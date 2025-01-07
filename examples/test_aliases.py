from typing import List, Optional
from datamodel import BaseModel, Field
from datamodel.aliases import to_snakecase


class Store(BaseModel):
    email_address: str
    status: str
    store_id: int = Field(primary_key=True)

    class Meta:
        strict = True
        as_objects = True
        alias_function = to_snakecase

# Example Usage:
store = Store(EmailAddress="test@example.com", Status="ACTIVE", StoreId=1)
print(store)
