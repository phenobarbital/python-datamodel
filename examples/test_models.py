from datetime import datetime
from datamodel import BaseModel, Column

class Address(BaseModel):
    street_address: str
    postal_code: str

class User(BaseModel):
    """Basic User Model for authentication."""

    user_id: int = Column(required=False, primary_key=True, repr=False)
    first_name: str = Column(required=True, max=254, label="First Name", pattern="^\w*$")
    last_name: str = Column(required=True, max=254, label="Last Name")
    email: str = Column(required=False, max=254, label="User's Email")
    password: str = Column(required=False, max=16, secret=True)
    last_login: datetime = Column(required=False, format='YYYY-MM-DD', readonly=True)
    username: str = Column(required=False)
    title: str = Column(equired=False, max=90)
    address: Address = Column(required=False)

    class Meta:
        name = 'users'
        schema = 'public'
        strict = True

user = User(
    user_id=1,
    first_name='John',
    last_name='Doe',
    email='john@example.com',
    username='johndoe',
)
print(user)
# Change the user_id and saved into the __value__ attribute:
user.user_id = 2
print(user.user_id, user.old_value('user_id'))
