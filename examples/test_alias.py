from typing import List, Optional
from datamodel import BaseModel, Field

data = {
    'store_name': "0002 Conn's HomePlus - Winston NC",
    'store_address': '3925 Oxford Station Way',
    'city': 'Winston-Salem', 'zipcode': '27103', 'phone_number': None,
    'emailAddress': "lara@test.com",
    'store_number': None, 'store_status': 't',
    'latitude': '36.068799', 'longitude': '-80.328457',
    'timezone': 'America/New_York', 'account_id': 24, 'country_id': 'USA',
    'store_type': 'FreeStanding', 'account_name': "Conn's",
    'store_id': 24252, 'visit_rule': [],
    'visit_category': [],
    'client_name': ['HISENSE', 'FLEX-ROC', 'ASSEMBLY'],
    'market_name': '10', 'region_name': 'Assembly - Region',
    'district_name': 'Assembly - District',
    'org_name': 'assembly'
}

# class Store(BaseModel):
#     email_address: str = Field(alias="emailAddress")  # The user sees "emailAddress"

class Store(BaseModel):
    org_name: str = Field(required=True)
    store_id: int = Field(primary_key=True, required=True)
    store_name: str = Field(required=True)
    store_address: str
    city: str
    zipcode: str
    phone_number: Optional[str]
    email_address: str = Field(alias="emailAddress")
    store_number: Optional[str]
    store_status: str
    latitude: float
    longitude: float
    timezone: str
    account_id: int
    country_id: str
    store_type: str
    account_name: str
    visit_rule: List[str]
    visit_category: List[str]
    client_name: List[str]
    market_name: str
    region_name: str
    district_name: str

    class Meta:
        strict = True
        as_objects = True

store = Store(**data)
print('Store > ', store)
print(store.email_address)  # "lara@test.com"
