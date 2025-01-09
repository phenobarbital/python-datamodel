from typing import List, Optional
from datamodel import BaseModel, Field
from datamodel.aliases import to_snakecase, to_pascalcase


class Store(BaseModel):
    email_address: str
    status: str
    store_id: int = Field(primary_key=True)

    class Meta:
        strict = True
        as_objects = True
        alias_function = to_snakecase


class ExampleModel(BaseModel):
    # Here, our Python fields are declared in PascalCase.
    StoreId: int = Field(primary_key=True)
    EmailAddress: str
    Status: str

    class Meta:
        strict = True
        as_objects = True
        # Our alias_function now transforms from the incoming snake_case to PascalCase.
        # So if user passes `store_id`, we transform it to `StoreId`.
        alias_function = to_pascalcase

def demo():
    store = Store(EmailAddress="test@example.com", Status="ACTIVE", StoreId=1)
    print("StoreId =>", store.store_id)
    print("EmailAddress =>", store.email_address)
    # The user input is using snake_case:
    model = ExampleModel(
        store_id=123,
        email_address="somebody@example.com",
        status="ACTIVE"
    )
    # Internally, we have PascalCase attributes:
    print("StoreId =>", model.StoreId)
    print("EmailAddress =>", model.EmailAddress)
    print("Status =>", model.Status)
    # Check the actual model
    print(model)

if __name__ == "__main__":
    demo()
