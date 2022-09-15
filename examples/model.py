import uuid
from datamodel import BaseModel, Column
from datetime import datetime


def auto_now_add(*args, **kwargs):
    return uuid.uuid4()

class Contact(BaseModel):
    account: str = ''
    value: str = ''

class User(BaseModel):
    """
    User Basic Structure
    """
    id: uuid.UUID = Column(primary_key=True, required=True, default=auto_now_add(), db_default='uuid_generate_v4()')
    firstname: str
    lastname: str
    name: str = Column(required=True, default='John Doe')
    age: int = Column(default=18, required=True)
    signup_ts: datetime = Column(default=datetime.now(), db_default='now()')
    contacts: Contact = Column(required=False)

    class Meta:
        name = 'users'
        schema = 'public'
        driver = 'pg'
        strict = False
        michiko = 'mamon'

u = User()
print(u.model(dialect='json'))
