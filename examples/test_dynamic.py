from typing import Optional, Any
from dataclasses import InitVar
from datamodel import BaseModel, Column
from datamodel.exceptions import ValidationError

class Identity(BaseModel):
    """Identity.

    Describe an Authenticated Entity on Navigator.
    """

    id: Any = Column(required=True)
    auth_method: str = None
    access_token: Optional[str] = None
    enabled: bool = Column(required=True, default=True)
    data: InitVar = {}
    is_authenticated: bool = Column(equired=False, default=False)
    userdata: dict = Column(required=False, default_factory=dict)

    def __post_init__(self, data):  # pylint: disable=W0221
        self.userdata = data
        for key, value in data.items():
            self.create_field(key, value)

    def set(self, name: str, value: Any) -> None:
        # alias for "create_field"
        self.create_field(name, value)

    class Meta:
        strict = False
        frozen = False


class BaseUser(Identity):
    name: str = Column(required=True)
    email: str = Column(required=True)

# Test the creation of dynamic fields on Datamodel:
if __name__ == '__main__':
    data = {
        'id': 12345,
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'age': 30,
        'is_active': True,
        'magic': 'Navigator',
        'address': {
            'street': '123 Main St',
            'city': 'Anytown',
            'state': 'NY',
            'zip': '10001'
        }
    }
    try:
        user = BaseUser(data)
        print(user)
    except ValidationError as e:
        print(e.payload)
    except Exception as e:
        print(e)
