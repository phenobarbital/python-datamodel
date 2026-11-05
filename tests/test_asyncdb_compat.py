"""
Dry-run tests for asyncdb.models.Model compatibility.

Verifies that python-datamodel's BaseModel provides the full interface
that asyncdb.models.Model depends on — without requiring a live database.

Layer 1: datamodel.models.Model — the base interface (Meta, fields, PKs,
         serialization, schema generation).
Layer 2: asyncdb.models.Model  — CRUD methods with mock connections.
"""
import pytest
import asyncio
from dataclasses import is_dataclass
from typing import Optional
from enum import Enum
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from datamodel import BaseModel, Field
from datamodel.abstract import Meta, ModelMeta
from datamodel.models import Model as DataModel, ModelMixin
from asyncdb.models import Model as AsyncModel


# ---------------------------------------------------------------------------
# Fixtures: datamodel.models.Model definitions (base layer)
# ---------------------------------------------------------------------------

class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(DataModel):
    """User accounts table."""
    user_id: int = Field(required=True, primary_key=True)
    username: str = Field(required=True)
    email: str = Field(required=False, default=None)
    age: int = Field(required=False, default=0)
    balance: Decimal = Field(required=False, default=Decimal("0.00"))
    status: UserStatus = Field(required=False, default=UserStatus.ACTIVE)
    is_admin: bool = False
    created_at: datetime = Field(required=False, default=None)

    class Meta:
        name = "users"
        schema = "public"
        strict = True


class Product(DataModel):
    """Product catalog."""
    sku: str = Field(required=True, primary_key=True)
    name: str = Field(required=True)
    price: float = Field(required=False, default=0.0, min=0, max=99999)
    description: str = Field(
        required=False, default="", comment="Product description"
    )
    active: bool = True

    class Meta:
        name = "products"
        schema = "inventory"
        strict = True


class Order(DataModel):
    """Customer orders."""
    order_id: int = Field(required=True, primary_key=True)
    customer_id: int = Field(required=True, primary_key=True)
    total: float = Field(required=False, default=0.0)
    notes: str = Field(required=False, default=None)

    class Meta:
        name = "orders"
        schema = "public"
        strict = True


class PEP604Model(DataModel):
    """Model using PEP 604 union syntax."""
    id: int = Field(required=True, primary_key=True)
    value: int | str = Field(required=False, default=None)
    tags: list | None = None
    score: float | None = Field(required=False, default=None)
    label: str | int | None = None

    class Meta:
        name = "pep604_test"
        schema = "public"
        strict = True


# ---------------------------------------------------------------------------
# Fixtures: asyncdb.models.Model definitions (CRUD layer)
# ---------------------------------------------------------------------------

class DbUser(AsyncModel):
    """User accounts table (asyncdb layer)."""
    user_id: int = Field(required=True, primary_key=True)
    username: str = Field(required=True)
    email: str = Field(required=False, default=None)
    age: int = Field(required=False, default=0)

    class Meta:
        name = "users"
        schema = "public"
        strict = True


class DbPEP604(AsyncModel):
    """PEP 604 model (asyncdb layer)."""
    id: int = Field(required=True, primary_key=True)
    value: int | str = Field(required=False, default=None)
    score: float | None = Field(required=False, default=None)

    class Meta:
        name = "pep604_db"
        schema = "public"
        strict = True


# ---------------------------------------------------------------------------
# 1. Metaclass and dataclass basics
# ---------------------------------------------------------------------------

class TestMetaclassIntegration:
    """Verify ModelMeta produces a proper dataclass with expected attributes."""

    def test_is_dataclass(self):
        assert is_dataclass(User)

    def test_asyncdb_model_is_dataclass(self):
        assert is_dataclass(DbUser)

    def test_metaclass_type(self):
        assert isinstance(User, ModelMeta)

    def test_inherits_model_mixin(self):
        assert issubclass(User, ModelMixin)

    def test_asyncdb_inherits_base_model(self):
        assert issubclass(DbUser, BaseModel)
        assert issubclass(DbUser, ModelMixin)

    def test_meta_class_attached(self):
        assert hasattr(User, 'Meta')
        assert User.Meta.name == "users"
        assert User.Meta.schema == "public"

    def test_meta_defaults_populated(self):
        for attr in ('frozen', 'driver', 'connection', 'dsn', 'strict'):
            assert hasattr(User.Meta, attr)


# ---------------------------------------------------------------------------
# 2. Field introspection (columns, types, metadata)
# ---------------------------------------------------------------------------

class TestFieldIntrospection:

    def test_columns_available(self):
        u = User(user_id=1, username="test")
        cols = u.columns()
        assert "user_id" in cols
        assert "username" in cols
        assert "email" in cols

    def test_get_columns_classmethod(self):
        cols = User.get_columns()
        assert isinstance(cols, dict)
        assert "user_id" in cols

    def test_get_column(self):
        col = User.get_column("username")
        assert col.name == "username"

    def test_get_column_missing_raises(self):
        with pytest.raises(AttributeError):
            User.get_column("nonexistent")

    def test_fields_list(self):
        u = User(user_id=1, username="test")
        assert "user_id" in u.get_fields()
        assert "username" in u.get_fields()

    def test_list_columns(self):
        u = User(user_id=1, username="test")
        cols = u.list_columns()
        assert isinstance(cols, list)
        assert "user_id" in cols

    def test_has_column(self):
        u = User(user_id=1, username="test")
        assert u.has_column("user_id")
        assert not u.has_column("nonexistent")

    def test_contains(self):
        u = User(user_id=1, username="test")
        assert "user_id" in u
        assert "nonexistent" not in u

    def test_field_metadata_accessible(self):
        col = User.get_column("user_id")
        assert col.metadata.get("primary", False) is True
        assert col.metadata.get("required", False) is True


# ---------------------------------------------------------------------------
# 3. Primary key support
# ---------------------------------------------------------------------------

class TestPrimaryKeys:

    def test_primary_keys_detected(self):
        pks = User.get_primary_keys()
        assert "user_id" in pks

    def test_composite_primary_keys(self):
        pks = Order.get_primary_keys()
        assert "order_id" in pks
        assert "customer_id" in pks
        assert len(pks) == 2

    def test_get_primary_key_fields(self):
        pk_fields = User.get_primary_key_fields()
        assert "user_id" in pk_fields
        assert pk_fields["user_id"].name == "user_id"

    def test_get_primary_key_values(self):
        u = User(user_id=42, username="test")
        pk_vals = u.get_primary_key_values()
        assert pk_vals == {"user_id": 42}

    def test_composite_pk_values(self):
        o = Order(order_id=1, customer_id=100, total=50.0)
        pk_vals = o.get_primary_key_values()
        assert pk_vals == {"order_id": 1, "customer_id": 100}

    def test_asyncdb_model_primary_keys(self):
        pks = DbUser.get_primary_keys()
        assert "user_id" in pks

    def test_asyncdb_pep604_primary_keys(self):
        pks = DbPEP604.get_primary_keys()
        assert "id" in pks


# ---------------------------------------------------------------------------
# 4. Instantiation, defaults, and coercion
# ---------------------------------------------------------------------------

class TestInstantiation:

    def test_basic_creation(self):
        u = User(user_id=1, username="alice")
        assert u.user_id == 1
        assert u.username == "alice"

    def test_defaults_applied(self):
        u = User(user_id=1, username="alice")
        assert u.age == 0
        assert u.is_admin is False
        assert u.email is None

    def test_enum_default(self):
        u = User(user_id=1, username="alice")
        assert u.status == UserStatus.ACTIVE

    def test_all_fields_set(self):
        now = datetime.now()
        u = User(
            user_id=1,
            username="alice",
            email="alice@example.com",
            age=30,
            balance=Decimal("100.50"),
            status=UserStatus.INACTIVE,
            is_admin=True,
            created_at=now,
        )
        assert u.email == "alice@example.com"
        assert u.age == 30
        assert u.is_admin is True
        assert u.created_at == now

    def test_from_dict(self):
        data = {"user_id": 1, "username": "bob", "email": "bob@test.com"}
        u = User.from_dict(data)
        assert u.user_id == 1
        assert u.username == "bob"
        assert u.email == "bob@test.com"

    def test_asyncdb_model_creation(self):
        u = DbUser(user_id=1, username="alice", email="a@b.com")
        assert u.user_id == 1
        assert u.username == "alice"

    def test_asyncdb_pep604_creation(self):
        m = DbPEP604(id=1, value=42, score=3.14)
        assert m.id == 1
        assert m.value == 42
        assert m.score == 3.14


# ---------------------------------------------------------------------------
# 5. Serialization (to_dict, json, schema)
# ---------------------------------------------------------------------------

class TestSerialization:

    def test_to_dict(self):
        u = User(user_id=1, username="alice", email="a@b.com")
        d = u.to_dict()
        assert isinstance(d, dict)
        assert d["user_id"] == 1
        assert d["username"] == "alice"
        assert d["email"] == "a@b.com"

    def test_to_dict_remove_nulls(self):
        u = User(user_id=1, username="alice")
        d = u.to_dict(remove_nulls=True)
        assert "email" not in d or d.get("email") is not None

    def test_to_dict_convert_enums(self):
        u = User(user_id=1, username="alice", status=UserStatus.SUSPENDED)
        d = u.to_dict(convert_enums=True)
        assert d["status"] == "suspended"

    def test_json_serialization(self):
        u = User(user_id=1, username="alice")
        j = u.json()
        assert isinstance(j, (str, bytes))
        assert b"alice" in (j if isinstance(j, bytes) else j.encode())

    def test_to_json_alias(self):
        u = User(user_id=1, username="alice")
        assert u.to_json() == u.json()

    def test_from_json(self):
        u = User(user_id=1, username="alice")
        j = u.json()
        u2 = User.from_json(j)
        assert u2.user_id == u.user_id
        assert u2.username == u.username

    def test_round_trip_dict(self):
        u = User(user_id=1, username="alice", age=30, email="a@b.com")
        d = u.to_dict()
        u2 = User(**d)
        assert u2.user_id == u.user_id
        assert u2.username == u.username
        assert u2.age == u.age

    def test_schema_generation(self):
        s = User.schema(as_dict=True)
        assert isinstance(s, dict)
        assert "properties" in s
        assert "user_id" in s["properties"]
        assert "username" in s["properties"]
        assert s["table"] == "users"
        assert s["schema"] == "public"

    def test_schema_required_fields(self):
        s = User.schema(as_dict=True)
        assert "user_id" in s["required"]
        assert "username" in s["required"]

    def test_schema_json_string(self):
        s = User.schema(as_dict=False)
        assert isinstance(s, (str, bytes))

    def test_json_schema_model(self):
        j = Product.model(dialect="json")
        assert isinstance(j, (str, bytes))

    def test_asyncdb_to_dict(self):
        u = DbUser(user_id=1, username="alice", email="a@b.com")
        d = u.to_dict()
        assert d["user_id"] == 1
        assert d["username"] == "alice"

    def test_asyncdb_json(self):
        u = DbUser(user_id=1, username="alice")
        j = u.json()
        assert isinstance(j, (str, bytes))

    def test_asyncdb_schema(self):
        s = DbUser.schema(as_dict=True)
        assert "properties" in s
        assert "user_id" in s["properties"]

    def test_asyncdb_sql_model(self):
        sql = DbUser.model(dialect="sql")
        assert "CREATE TABLE" in sql
        assert "public.users" in sql
        assert "user_id" in sql


# ---------------------------------------------------------------------------
# 6. getitem/get/repr/pop
# ---------------------------------------------------------------------------

class TestModelBehavior:

    def test_is_valid_when_valid(self):
        u = User(user_id=1, username="alice")
        assert isinstance(u.is_valid(), bool)

    def test_getitem(self):
        u = User(user_id=1, username="alice")
        assert u["user_id"] == 1
        assert u["username"] == "alice"

    def test_get_method(self):
        u = User(user_id=1, username="alice")
        assert u.get("user_id") == 1
        assert u.get("nonexistent", "fallback") == "fallback"

    def test_repr(self):
        u = User(user_id=1, username="alice")
        r = repr(u)
        assert "User" in r
        assert "alice" in r

    def test_pop(self):
        u = User(user_id=1, username="alice", email="a@b.com")
        val = u.pop("email")
        assert val == "a@b.com"
        assert u.email is None

    def test_pop_missing_with_default(self):
        u = User(user_id=1, username="alice")
        val = u.pop("nonexistent", "default_val")
        assert val == "default_val"


# ---------------------------------------------------------------------------
# 7. PEP 604 union types in Model context
# ---------------------------------------------------------------------------

class TestPEP604Compatibility:

    def test_creation_with_int(self):
        m = PEP604Model(id=1, value=42)
        assert m.value == 42

    def test_creation_with_str(self):
        m = PEP604Model(id=1, value="hello")
        assert m.value == "hello"

    def test_optional_none(self):
        m = PEP604Model(id=1)
        assert m.score is None
        assert m.tags is None
        assert m.label is None

    def test_optional_with_value(self):
        m = PEP604Model(id=1, score=3.14, label="test")
        assert m.score == 3.14
        assert m.label == "test"

    def test_to_dict_with_unions(self):
        m = PEP604Model(id=1, value="hello", score=9.5)
        d = m.to_dict()
        assert d["id"] == 1
        assert d["value"] == "hello"
        assert d["score"] == 9.5

    def test_json_with_unions(self):
        m = PEP604Model(id=1, value=42, label="x")
        j = m.json()
        assert isinstance(j, (str, bytes))

    def test_primary_keys_with_pep604(self):
        pks = PEP604Model.get_primary_keys()
        assert "id" in pks

    def test_schema_with_pep604(self):
        s = PEP604Model.schema(as_dict=True)
        assert "properties" in s
        assert "value" in s["properties"]
        assert "score" in s["properties"]

    def test_asyncdb_pep604_to_dict(self):
        m = DbPEP604(id=1, value="hello", score=9.5)
        d = m.to_dict()
        assert d["value"] == "hello"
        assert d["score"] == 9.5

    def test_asyncdb_pep604_schema(self):
        s = DbPEP604.schema(as_dict=True)
        assert "properties" in s
        assert "value" in s["properties"]


# ---------------------------------------------------------------------------
# 8. CRUD interface dry-run (asyncdb.models.Model, mock connections)
# ---------------------------------------------------------------------------

class TestCRUDInterfaceDryRun:
    """Verify CRUD methods exist on asyncdb Model and work with mocks."""

    def test_instance_crud_methods_exist(self):
        for method in ("insert", "update", "delete", "save", "fetch"):
            assert hasattr(DbUser, method), f"Missing instance method: {method}"
            assert asyncio.iscoroutinefunction(getattr(DbUser, method))

    def test_class_crud_methods_exist(self):
        for method in ("create", "remove", "select", "filter", "get", "all",
                       "updating", "deleting"):
            assert hasattr(DbUser, method), f"Missing class method: {method}"

    def test_set_connection(self):
        u = DbUser(user_id=1, username="test")
        mock_conn = MagicMock()
        u.set_connection(mock_conn)
        assert u.Meta.connection is mock_conn

    def test_meta_set_connection_classmethod(self):
        mock_conn = MagicMock()
        DbUser.Meta.set_connection(mock_conn)
        assert DbUser.Meta.connection is mock_conn
        DbUser.Meta.connection = None

    @pytest.mark.asyncio
    async def test_insert_without_connection_raises(self):
        u = DbUser(user_id=1, username="test")
        u.Meta.connection = None
        u.Meta.driver = None
        u.Meta.datasource = None
        with pytest.raises(Exception):
            await u.insert()

    @pytest.mark.asyncio
    async def test_class_select_without_connection(self):
        from asyncdb.exceptions import ConnectionMissing
        DbUser.Meta.connection = None
        DbUser.Meta.driver = None
        with pytest.raises(ConnectionMissing):
            await DbUser.select()

    @pytest.mark.asyncio
    async def test_class_get_without_connection(self):
        from asyncdb.exceptions import ConnectionMissing
        DbUser.Meta.connection = None
        DbUser.Meta.driver = None
        with pytest.raises(ConnectionMissing):
            await DbUser.get()

    @pytest.mark.asyncio
    async def test_insert_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._insert_ = AsyncMock(return_value={"user_id": 1})

        u = DbUser(user_id=1, username="alice")
        u.Meta.connection = mock_conn

        result = await u.insert()
        mock_conn._insert_.assert_called_once()
        assert result == {"user_id": 1}

    @pytest.mark.asyncio
    async def test_update_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._update_ = AsyncMock(return_value=True)

        u = DbUser(user_id=1, username="alice")
        u.Meta.connection = mock_conn

        result = await u.update()
        mock_conn._update_.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._delete_ = AsyncMock(return_value=True)

        u = DbUser(user_id=1, username="alice")
        u.Meta.connection = mock_conn

        result = await u.delete()
        mock_conn._delete_.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._save_ = AsyncMock(return_value={"user_id": 1})

        u = DbUser(user_id=1, username="alice")
        u.Meta.connection = mock_conn

        result = await u.save()
        mock_conn._save_.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._fetch_ = AsyncMock(
            return_value={"user_id": 1, "username": "alice", "email": "a@b.com"}
        )

        u = DbUser(user_id=1, username="placeholder")
        u.Meta.connection = mock_conn

        result = await u.fetch()
        assert result.username == "alice"
        assert result.email == "a@b.com"

    @pytest.mark.asyncio
    async def test_class_all_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn._all_ = AsyncMock(return_value=[
            {"user_id": 1, "username": "alice"},
            {"user_id": 2, "username": "bob"},
        ])

        DbUser.Meta.connection = mock_conn
        results = await DbUser.all()
        assert len(results) == 2
        assert all(isinstance(r, DbUser) for r in results)
        assert results[0].username == "alice"
        assert results[1].username == "bob"

    @pytest.mark.asyncio
    async def test_class_select_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn._select_ = AsyncMock(return_value=[
            {"user_id": 1, "username": "alice"},
        ])

        DbUser.Meta.connection = mock_conn
        results = await DbUser.select()
        assert len(results) == 1
        assert results[0].user_id == 1

    @pytest.mark.asyncio
    async def test_class_filter_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn._filter_ = AsyncMock(return_value=[
            {"user_id": 1, "username": "alice"},
        ])

        DbUser.Meta.connection = mock_conn
        results = await DbUser.filter(username="alice")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_class_get_with_mock(self):
        mock_conn = AsyncMock()
        mock_conn._get_ = AsyncMock(
            return_value={"user_id": 1, "username": "alice"}
        )

        DbUser.Meta.connection = mock_conn
        result = await DbUser.get(user_id=1)
        assert isinstance(result, DbUser)
        assert result.username == "alice"

    @pytest.mark.asyncio
    async def test_crud_with_pep604_model(self):
        """CRUD round-trip with PEP 604 union fields."""
        mock_conn = AsyncMock()
        mock_conn.is_connected.return_value = True
        mock_conn._insert_ = AsyncMock(return_value={"id": 1})
        mock_conn._fetch_ = AsyncMock(
            return_value={"id": 1, "value": "hello", "score": 9.5}
        )

        m = DbPEP604(id=1, value="hello", score=9.5)
        m.Meta.connection = mock_conn

        await m.insert()
        mock_conn._insert_.assert_called_once()

        result = await m.fetch()
        assert result.value == "hello"
        assert result.score == 9.5


# ---------------------------------------------------------------------------
# 9. make_model dynamic model creation
# ---------------------------------------------------------------------------

class TestMakeModel:

    def test_make_model_from_datamodel(self):
        DynModel = DataModel.make_model(
            "dynamic_table",
            schema="staging",
            fields=[("col_a", str, Field(required=True)), ("col_b", int)]
        )
        assert is_dataclass(DynModel)
        assert DynModel.Meta.name == "dynamic_table"
        assert DynModel.Meta.schema == "staging"

        instance = DynModel(col_a="hello", col_b=42)
        assert instance.col_a == "hello"
        assert instance.col_b == 42


# ---------------------------------------------------------------------------
# 10. JSON-LD, adaptive card, and sample (schema extensions)
# ---------------------------------------------------------------------------

class TestSchemaExtensions:

    def test_as_schema_jsonld(self):
        u = User(user_id=1, username="alice")
        schema = u.as_schema()
        assert "@context" in schema
        assert schema["@context"] == "https://schema.org/"
        assert "@type" in schema
        assert schema["user_id"] == 1

    def test_as_schema_nested(self):
        u = User(user_id=1, username="alice")
        schema = u.as_schema(top_level=False)
        assert "@context" not in schema
        assert "@type" in schema

    def test_adaptive_card(self):
        card = Product.to_adaptive(as_dict=True)
        assert card["type"] == "AdaptiveCard"
        assert "body" in card
        assert "actions" in card
        assert any(
            item.get("id") == "sku" for item in card["body"]
            if isinstance(item, dict) and "id" in item
        )

    def test_sample(self):
        s = Product.sample()
        assert "properties" in s
        assert "required" in s
        assert "sku" in s["required"]
