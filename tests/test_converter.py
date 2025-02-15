import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class Organization(BaseModel):
    org_id: int = Field(primary_key=True)
    name: str

    class Meta:
        strict = True


class Client(BaseModel):
    client_id: int = Field(primary_key=True)
    client_name: str
    status: bool = Field(required=True)
    orgid: Organization = Field(required=False, alias="org_id")
    org_name: str = Field(required=False)

    class Meta:
        name: str = 'clients'
        strict: bool = True
        as_objects: bool = True

@pytest.mark.parametrize(
    "client_id, client_name, status, orgid, org_name, expected_exception",
    [
        # Happy path
        (1, "Client A", True, Organization(org_id=1, name="Org A"), "Org A Name", None),
        # Edge cases
        (4, "", True, None, "", None),  # Empty client_name and org_name
        (5, "Client D", True, Organization(org_id=0, name=""), "", None),  # Empty org_name
        (6, None, True, None, None, None),  # Missing client_name
        # Error cases
        ("Chance", 123, True, None, None, ValidationError),  # Invalid client_id type
        (8, "Client E", "Apollo", None, None, ValidationError),  # Invalid status type
        (9, "Client F", True, "Arenas", None, ValueError),  # Invalid orgid type
    ],
)
def test_client_creation(client_id, client_name, status, orgid, org_name, expected_exception):
    if expected_exception:
        with pytest.raises(expected_exception):
            Client(client_id=client_id, client_name=client_name, status=status, orgid=orgid, org_name=org_name)
    else:
        client = Client(client_id=client_id, client_name=client_name, status=status, orgid=orgid, org_name=org_name)
        assert client.client_id == client_id
        assert client.client_name == client_name
        assert client.status == status
        if isinstance(client.orgid, Organization):
            assert client.orgid.org_id == orgid.org_id
        else:
            assert client.orgid == orgid
        assert client.org_name == org_name


@pytest.mark.parametrize(
    "client_id, client_name, status, orgid, org_name",
    [
        # Happy path tests
        (1, "Client A", True, Organization(org_id=1, name="Org A"), "Org A Name"),  # ID: happy_path_1
        (2, "Client B", False, None, None),  # ID: happy_path_2
        (3, "Client C", True, Organization(org_id=2, name="Org B"), "Org B Name"),  # ID: happy_path_3

        # Edge cases
        (4, "", True, None, ""),  # ID: edge_case_empty_strings
        (5, "Client D", True, Organization(org_id=0, name=""), ""),  # ID: edge_case_zero_org_id
        (6, None, True, None, None), # ID: edge_case_none_client_name
        (7, "Client F", True, 123, None),  # ID: edge_case_invalid_orgid_type

        # Error cases - expecting exceptions due to strict mode
        (8, 123, True, {"orgid": "Bother", "name": "Org B"}, None),  # ID: error_case_invalid_orgid_type
        (9, "Client E", "Family", None, None),  # ID: error_case_invalid_status_type

    ],
)
def test_more_client_creation(client_id, client_name, status, orgid, org_name):

    # Act
    if client_id in [8, 9]:  # Error cases
        with pytest.raises((ValueError, ValidationError)):
            client = Client(client_id=client_id, client_name=client_name, status=status, orgid=orgid, org_name=org_name)
    else:  # Happy path and edge cases
        client = Client(client_id=client_id, client_name=client_name, status=status, orgid=orgid, org_name=org_name)

        # Assert
        assert client.client_id == client_id
        assert client.client_name == client_name
        assert client.status == status
        if isinstance(client.orgid, BaseModel):
            if isinstance(orgid, dict):
                org = Organization(**orgid)
            elif isinstance(orgid, BaseModel):
                org = orgid
            else:
                org = Organization(org_id=orgid)
            assert client.orgid.org_id == org.org_id
            assert client.orgid == org
        else:
            assert client.orgid == orgid
        assert client.org_name == org_name


@pytest.mark.parametrize(
    "input_dict, expected_exception",
    [
        # Missing required field 'status'
        ({"client_id": 1, "client_name": "Client A"}, ValueError),  # ID: missing_status
        # Extra unknown field
        ({"client_id": 1, "client_name": "Client A", "status": True, "unknown_field": "value"}, TypeError),  # ID: extra_unknown_field
    ],
)
def test_client_creation_missing_fields(input_dict, expected_exception):

    # Act
    with pytest.raises(expected_exception):
        client = Client(**input_dict)


def test_client_missing_status():

    # Act
    with pytest.raises(ValueError):
        client = Client(client_id=1, client_name="Client A")


def test_client_meta_attributes():

    # Assert
    assert Client.Meta.name == 'clients'
    assert Client.Meta.strict is True
    assert Client.Meta.as_objects is True


def test_handle_dataclass_with_alias_on_error():
    # This will work without alias
    org_data = {"org_id": 10, "name": "Org A"}
    client = Client(
        client_id=1,
        client_name="Test Client",
        status=True,
        orgid=org_data,
        org_name="Organization A"
    )
    assert client.orgid.org_id == 10
    assert client.orgid.name == "Org A"

    # This will trigger alias logic
    org_data_alias = {"orgid": 20, "name": "Org B"}
    client_with_alias = Client(
        client_id=2,
        client_name="Test Client B",
        status=True,
        orgid=org_data_alias,
        org_name="Organization B"
    )
    assert client_with_alias.orgid.org_id == 20
    assert client_with_alias.orgid.name == "Org B"

def test_client_creation_as_objects_false():
    Client.Meta.as_objects = False
    client = Client(
        client_id=1,
        client_name="Test Client",
        status=True,
        orgid=1,
        org_name="Test Org"
    )
    assert client.orgid == 1
    assert client.org_name == "Test Org"
