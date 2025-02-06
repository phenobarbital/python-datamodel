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
    orgid: Organization = Field(required=False, alias='org_id')
    org_name: str

    class Meta:
        name: str = 'clients'
        strict: bool = True
        as_objects: bool = False

data = {"client_id": 1, "client_name": "Client A"}

data = {"client_id": 9, "client_name": 123, "status": "True", "orgid": 123, "org_name": None}
try:
    client = Client(**data)
    print(client)
except ValidationError as e:
    print(e.payload)

Client.Meta.as_objects = False
try:
    client = Client(
        client_id=1,
        client_name="Test Client",
        status=True,
        orgid=1,
        org_name="Test Org"
    )
    assert client.orgid == 1
    assert client.org_name == "Test Org"
except ValidationError as e:
    print(e.payload)

try:
    Client.Meta.as_objects = True
    client = Client(
        client_id=1,
        client_name="Test Client",
        status=True,
        org_id=10,
        org_name="Organization A"
    )
    print(client.orgid)
    assert client.orgid.org_id == 10
except ValidationError as e:
    print(e.payload)

try:
    org_data = {"org_id": 10, "name": "Org A"}
    client = Client(
        client_id=1,
        client_name="Test Client",
        status=True,
        org_id=org_data,
        org_name="Organization A"
    )
    print(client)
    assert client.orgid.org_id == 10
    assert client.orgid.name == "Org A"
except ValidationError as e:
    print(e.payload)
