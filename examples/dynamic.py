from typing import Any, Optional
from dataclasses import InitVar
from datamodel import BaseModel, Column


class Identity(BaseModel):
    """Identity.

    Describe an Authenticated Entity on Navigator.
    """
    id: Any = Column(required=True)
    auth_method: str = None
    access_token: Optional[str] = None
    enabled: bool = Column(required=True, default=True)
    data: InitVar[dict]
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

u = Identity(data={"user_id": 123, "username": "test"})
print(u)


class AuthUser(Identity):
    """AuthUser

    Model for any Authenticated User.
    """
    first_name: str
    last_name: str
    name: str
    email: str
    username: str
    superuser: bool = Column(required=True, default=False)


userdata = {
    'user_id': 13144,
    'username': 'Gcanelon@mobileinsight.com',
    'first_name': 'Guillermo Daniel',
    'last_name': 'Canelón Lovera',
    'display_name': 'Guillermo Daniel Canelón Lovera',
    'email': 'Gcanelon@mobileinsight.com',
    'enabled': True,
    'superuser': True,
    'title': None,
    'associate_id': None,
    'associate_oid': None,
    'group_id': [1],
    'groups': ['superuser'],
    'programs': ['loreal', 'apple', 'retail', 'next', 'wm', 'partner_portal', 'navigator'],
    'department_code': None
}

try:
    usr = AuthUser(data=userdata)
    print('User >', usr)
except Exception as ex:
    print(ex)
