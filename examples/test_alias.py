from datamodel import BaseModel, Field


class Store(BaseModel):
    email_address: str = Field(alias="emailAddress")  # The user sees "emailAddress"

store = Store(emailAddress="lara@test.com")
print('Store > ', store)
print(store.email_address)  # "lara@test.com"
