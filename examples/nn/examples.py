from typing import List, Any
from datetime import datetime
import pandas as pd
from datamodel import BaseModel, Field
from datamodel.parsers.json import json_decoder
from datamodel.exceptions import ValidationError


client_payload = """
{
    "metadata": {
        "type": "client",
        "transactionType": "UPSERT",
        "source": "MainEvent",
        "client": "global"
    },
    "payload": {
        "client_id": 61,
        "client_name": "ASSEMBLY",
        "status": true,
        "orgid": 71,
        "org_name": "assembly"
    }
}
"""

formid_payload = """
{
    "metadata": {
        "type": "recapDefinition",
        "transactionType": "UPSERT",
        "source": "MainEvent",
        "client": "assembly"
    },
    "payload": {
        "formid": 7,
        "form_name": "Assembly Tech Form",
        "active": true,
        "created_on": "2024-09-24T07:13:20-05:00",
        "updated_on": "2024-09-25T12:51:53-05:00",
        "is_store_stamp": false,
        "client_id": 61,
        "client_name": "ASSEMBLY",
        "orgid": 71
    }
}
"""

metadata_payload = """
{
    "metadata": {
        "type": "form_metadata",
        "transactionType": "UPSERT",
        "source": "MainEvent",
        "client": "assembly"
    },
    "payload": {
        "column_name": "9080",
        "description": "Were all the Kitchen Suite appliances installed correctly before leaving the store?",
        "is_active": true,
        "data_type": "FIELD_MULTISELECT",
        "formid": 10,
        "form_name": "Lowe's Call Form",
        "client_id": 57,
        "client_name": "HISENSE",
        "orgid": 106
    }
}
"""

user_payload = """
{
    "metadata": {
        "type": "user",
        "transactionType": "UPSERT",
        "source": "MainEvent",
        "client": "global"
    },
    "payload": {
        "user_id": 2661,
        "first_name": "M",
        "last_name": "Rosado",
        "email": "mrosado@trocglobal.com",
        "mobile_number": "237-222-3576",
        "address": "800 S. Douglas Rd",
        "city": "Coral Gables",
        "state_name": "FL",
        "zipcode": "33134",
        "latitude": 25.763887,
        "longitude": -80.2567,
        "username": "mrosado",
        "role_id": 1,
        "employee_number": 158,
        "physical_country": "USA",
        "role_name": "Global Admin",
        "is_active": true,
        "org_name": "assembly",
        "client_id": [
            61,
            54,
            55,
            56,
            60,
            57,
            58,
            62,
            59,
            65,
            63
        ],
        "orgid": [
            71,
            138,
            74,
            69,
            60,
            106,
            137,
            62,
            77,
            3,
            63
        ],
        "client_names": [
            "ASSEMBLY",
            "AT&T",
            "BOSE",
            "EPSON",
            "FLEX-ROC",
            "HISENSE",
            "POKEMON",
            "TCT MOBILE",
            "TRENDMICRO",
            "TRO MSO",
            "WORP"
        ]
    }
}
"""

class Organization(BaseModel):
    orgid: int = Field(primary_key=True)
    org_name: str
    status: bool = Field(required=True, default=True)

    class Meta:
        name: str = 'organizations'
        strict: bool = True

def create_organization(
    name: str,
    value: Any,
    obj: Any,
    parent_data: BaseModel
) -> Organization:
    org_name = parent_data.get('org_name', None) if parent_data else None
    print('Creating organization')
    args = {
        name: value,
        "org_name": org_name,
        "status": True,
    }
    return obj(**args)

BaseModel.register_parser(Organization, create_organization, 'orgid')

class Client(BaseModel):
    client_id: int = Field(primary_key=True)
    client_name: str
    status: bool = Field(required=True, default=True)
    orgid: Organization = Field(required=False)
    org_name: str

    class Meta:
        name: str = 'clients'
        strict: bool = True
        as_objects: bool = True


class Form(BaseModel):
    formid: int = Field(primary_key=True)
    form_name: str = Field(required=True)
    active: bool = Field(required=False, default=True)
    created_on: datetime = Field(required=True)
    updated_on: datetime = Field(required=True)
    is_store_stamp: bool = Field(required=True)
    client_id: Client = Field(required=True)
    client_name: Client = Field(required=True)
    orgid: Organization = Field(required=True)

    class Meta:
        name: str = 'forms'
        strict: bool = True

class FormMetadata(BaseModel):
    column_name: str = Field(required=True)
    description: str = Field(required=True)
    is_active: bool = Field(required=False, default=True)
    data_type: str = Field(required=True)
    formid: Form = Field(required=True)
    form_name: Form = Field(required=True)
    client_id: Client = Field(required=True)
    client_name: Client = Field(required=True)
    orgid: Organization = Field(required=True)

    class Meta:
        name: str = 'form_metadata'
        strict: bool = True

class User(BaseModel):
    user_id: int = Field(primary_key=True)
    first_name: str = Field(required=True)
    last_name: str = Field(required=True)
    email: str = Field(required=True)
    mobile_number: str = Field(required=True)
    address: str = Field(required=True)
    city: str = Field(required=True)
    state_name: str = Field(required=True)
    zipcode: str = Field(required=True)
    latitude: float = Field(required=True)
    longitude: float = Field(required=True)
    username: str = Field(required=True)
    role_id: int = Field(required=True)
    employee_number: int = Field(required=True)
    physical_country: str = Field(required=True)
    role_name: str = Field(required=True)
    is_active: bool = Field(required=False, default=True)
    client_id: List[Client] = Field(required=True)
    orgid: List[Organization] = Field(required=True)
    org_name: str
    client_names: List[str] = Field(required=True)

    class Meta:
        name: str = 'users'
        strict: bool = True
        as_objects: bool = False


network_ninja_map = {
    "client": Client,
    "organization": Organization,
    "recapDefinition": Form,
    "form_metadata": FormMetadata,
    "user": User
}

def get_client():
    payload = json_decoder(client_payload)
    metadata = payload.get("metadata")
    payload = payload.get("payload")
    model = network_ninja_map.get(metadata.get("type"))
    try:
        client = model(**payload)
    except ValidationError as e:
        print(e)
        print(e.payload)
    print('CLIENT > ', client)
    return client

def get_formid():
    payload = json_decoder(formid_payload)
    metadata = payload.get("metadata")
    payload = payload.get("payload")
    model = network_ninja_map.get(metadata.get("type"))
    form = None
    try:
        form = model(**payload)
    except ValidationError as e:
        print(e)
        print(e.payload)
    if form:
        print('FORM ID > ', form)
        return form

def get_formmetadata():
    payload = json_decoder(metadata_payload)
    metadata = payload.get("metadata")
    payload = payload.get("payload")
    model = network_ninja_map.get(metadata.get("type"))
    form_metadata = None
    try:
        form_metadata = model(**payload)
    except ValidationError as e:
        print(e)
        print(e.payload)
    if form_metadata:
        print('FORM METADATA > ', form_metadata)
        return form_metadata

def get_user():
    payload = json_decoder(user_payload)
    metadata = payload.get("metadata")
    payload = payload.get("payload")
    model = network_ninja_map.get(metadata.get("type"))
    user = None
    try:
        user = model(**payload)
    except ValidationError as e:
        print(e)
        print(e.payload)
    if user:
        print('USER > ', user)
        return user

if __name__ == "__main__":
    # client = get_client()
    # formid = get_formid()
    # form_metadata = get_formmetadata()
    user = get_user()
    # df = pd.DataFrame([client.to_dict(as_values=True)])
    # print('DF = ', df)
