# tests/test_query_model.py
from datetime import datetime
from typing import List, Optional
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


def rigth_now(obj) -> datetime:
    return datetime.now()

class QueryModel(BaseModel):
    query_slug: str = Field(required=True, primary_key=True)
    description: str = Field(required=False, default=None)
    # Source and primary attributes:
    source: Optional[str] = Field(required=False)
    params: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    attributes: Optional[dict] = Field(
        required=False,
        db_type='jsonb',
        default_factory=dict,
        comment="Optional Attributes for Query"
    )
    #  main conditions
    conditions: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    cond_definition: Optional[dict] = Field(
        required=False,
        db_type='jsonb',
        default_factory=dict
    )
    ## filter and grouping options
    fields: Optional[List[str]] = Field(
        required=False,
        db_type='array',
        default_factory=list
    )
    filtering: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ordering: Optional[List[str]] = Field(required=False, db_type='array')
    grouping: Optional[List[str]] = Field(required=False, db_type='array')
    qry_options: Optional[dict] = Field(required=False, db_type='jsonb')
    h_filtering: bool = Field(required=False, default=False, comment="filtering based on Hierarchical rules.")
    ### Query Information:
    query_raw: str = Field(required=False)
    is_raw: bool = Field(required=False, default=False)
    is_cached: bool = Field(required=False, default=True)
    provider: str = Field(required=False, default='db')
    parser: str = Field(required=False, default='SQLParser', comment="Parser to be used for parsing Query.")
    cache_timeout: int = Field(required=True, default=3600)
    cache_refresh: int = Field(required=True, default=0)
    cache_options: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ## Program Information:
    program_id: int = Field(required=True, default=1)
    program_slug: str = Field(required=True, default='default')
    # DWH information
    dwh: bool = Field(required=True, default=False)
    dwh_driver: str = Field(required=False, default=None)
    dwh_info: Optional[dict] = Field(required=False, db_type='jsonb')
    dwh_scheduler: Optional[dict] = Field(
        required=False,
        db_type='jsonb',
        default_factory=dict
    )
    # Creation Information:
    created_at: datetime = Field(
        required=False,
        default=datetime.now,
        db_default='now()'
    )
    created_by: int = Field(required=False)  # TODO: validation for valid user
    updated_at: datetime = Field(
        required=False,
        default=datetime.now,
        # encoder=rigth_now
    )
    updated_by: int = Field(required=False)  # TODO: validation for valid user

    class Meta:
        driver = 'pg'
        name = 'queries'
        schema = 'public'
        strict = True
        frozen = False
        remove_nulls = True  # Auto-remove nullable (with null value) fields


# Sample payload as provided
@pytest.fixture
def sample_data():
    return {
        'query_slug': 'walmart_mtd_postpaid_to_goal',
        'description': 'walmart_mtd_postpaid_to_goal',
        'conditions': {'filterdate': 'POSTPAID_DATE', 'store_tier': 'null', 'launch_group': 'null'},
        'cond_definition': {'filterdate': 'date', 'store_tier': 'string', 'launch_group': 'string'},
        'fields': ["client_id", "client_name"],
        'ordering': [],
        'h_filtering': False,
        'query_raw': 'SELECT {fields}\nFROM walmart.postpaid_metrics({filterdate}, {launch_group}, {store_tier})\n{where_cond}',
        'is_raw': False,
        'is_cached': True,
        'provider': 'db',
        'parser': 'pgSQLParser',
        'cache_timeout': 900,
        'cache_refresh': None,
        'cache_options': {},
        'program_id': 3,
        'program_slug': 'walmart',
        'dwh': False,
        'dwh_scheduler': {},
        'created_at': datetime(2022, 11, 18, 1, 10, 8, 872163),
        'updated_at': datetime(2023, 4, 18, 1, 38, 44, 466221)
    }


def test_query_model_success(sample_data):
    """Test that a QueryModel is created successfully and that every field has the expected value and type."""
    qm = QueryModel(**sample_data)

    # Required primary key field
    assert qm.query_slug == sample_data['query_slug']
    # Description is optional
    assert qm.description == sample_data['description']
    # When not provided, source is None.
    assert qm.source is None

    # Defaulted dict fields (via default_factory):
    assert isinstance(qm.params, dict)
    assert qm.params == {}
    assert isinstance(qm.attributes, dict)
    assert qm.attributes == {}
    assert isinstance(qm.conditions, dict)
    assert qm.conditions == sample_data['conditions']
    assert isinstance(qm.cond_definition, dict)
    assert qm.cond_definition == sample_data['cond_definition']

    # List field "fields" must be a list of strings as provided.
    assert isinstance(qm.fields, list)
    assert qm.fields == sample_data['fields']

    # Filtering and ordering
    assert isinstance(qm.filtering, dict)
    assert qm.filtering == {}
    assert isinstance(qm.ordering, list)
    assert qm.ordering == sample_data['ordering']
    # grouping is optional and not provided so likely None.
    assert qm.grouping is None

    # Boolean and string fields
    assert isinstance(qm.h_filtering, bool)
    assert qm.h_filtering == sample_data['h_filtering']
    assert qm.query_raw == sample_data['query_raw']
    assert qm.is_raw == sample_data['is_raw']
    assert qm.is_cached == sample_data['is_cached']
    assert qm.provider == sample_data['provider']
    assert qm.parser == sample_data['parser']

    # Numeric and dict defaults
    assert qm.cache_timeout == sample_data['cache_timeout']
    # Here cache_refresh is provided as None in sample but default_factory may have set it to 0.
    # (Your model code sets default=0 for cache_refresh.)
    assert qm.cache_refresh == 0
    assert qm.cache_options == sample_data['cache_options']

    # Program info
    assert qm.program_id == sample_data['program_id']
    assert qm.program_slug == sample_data['program_slug']

    # DWH info fields
    assert qm.dwh == sample_data['dwh']
    # dwh_driver and dwh_info are not provided, so should be None.
    assert qm.dwh_driver is None
    assert qm.dwh_info is None
    assert qm.dwh_scheduler == sample_data['dwh_scheduler']

    # Creation information: check that created_at and updated_at are datetime objects and match
    assert isinstance(qm.created_at, datetime)
    assert qm.created_at == sample_data['created_at']
    assert isinstance(qm.updated_at, datetime)
    assert qm.updated_at == sample_data['updated_at']

    # created_by and updated_by are not provided, so should be None.
    assert qm.created_by is None
    assert qm.updated_by is None


def test_query_model_missing_required_field(sample_data):
    """Test that missing a required field (e.g. 'query_slug') raises a ValueError."""
    payload = sample_data.copy()
    payload.pop('query_slug')
    with pytest.raises(ValueError) as excinfo:
        QueryModel(**payload)
    # Optionally, check that the error payload mentions the missing 'query_slug'
    assert 'query_slug' in str(excinfo.value)


def test_query_model_remove_nulls(sample_data):
    """Test that when remove_nulls is enabled, to_dict does not include keys with None values."""
    payload = sample_data.copy()
    # Intentionally set a couple of optional fields to None
    payload['attributes'] = None
    payload['params'] = None
    qm = QueryModel(**payload)
    d = qm.to_dict(remove_nulls=True)
    assert 'attributes' not in d
    assert 'params' not in d


def test_query_model_schema_generation():
    """Test that the JSON-Schema generated by QueryModel contains expected keys."""
    schema_dict = QueryModel.schema(as_dict=True)
    assert schema_dict["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    # Title may either be the class name or a transformation of it (based on slugify_camelcase)
    assert "Query Model" in schema_dict["title"]
    # Check that required fields (like 'query_slug') are in the "required" list.
    required = schema_dict.get("required", [])
    assert "query_slug" in required
    # Check that properties are defined and include 'query_slug'
    properties = schema_dict.get("properties", {})
    assert isinstance(properties, dict)
    assert "query_slug" in properties
