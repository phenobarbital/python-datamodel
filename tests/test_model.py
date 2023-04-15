from typing import Union, List
from datamodel import Model, Field, Column
import uuid


class User(Model):
    id: int
    name: str
    first_name: str = Field(required=True)
    last_name: str = Field(required=True)
    age: int = 18

def auto_uuid(*args, **kwargs):
    return uuid.uuid4()

def test_user_model():
    # Create a new User instance
    user = User(id=1, name="Alice", first_name="Alice", last_name="Smith")

    # Check that the id attribute was set correctly
    assert user.id == 1

    # Check that the name attribute was set correctly
    assert user.name == "Alice"

    # Check that the first_name attribute was set correctly
    assert user.first_name == "Alice"

    # Check that the last_name attribute was set correctly
    assert user.last_name == "Smith"

    # Check that the age attribute has the default value of 18
    assert user.age == 18

    # Check that calling to_dict() returns a dictionary with the correct values
    assert user.to_dict() == {
        "id": 1,
        "name": "Alice",
        "first_name": "Alice",
        "last_name": "Smith",
        "age": 18,
    }


class Account(Model):
    """
    Attributes for using a Provider by an User (Actor)
    """
    provider: str = Column(required=True, default='dummy')
    enabled: bool = Column(required=True, default=True)
    address: Union[str, list] = Column(required=False, default='')
    phone: Union[str, list] = Column(required=False, default='')
    userid: str = Column(required=False, default='')

    def set_address(self, address: str):
        self.address = address

class Actor(Model):
    """
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """
    userid: uuid.UUID = Field(required=False, primary_key=True, factory=auto_uuid)
    name: str
    account: Union[Account, List[Account]]

    def __str__(self) -> str:
        return f'<{self.name}: {self.userid}>'


def test_actor_defaults():
    actor = Actor(name="John Doe")
    assert isinstance(actor.userid, uuid.UUID)
    assert isinstance(actor.name, str)
    assert actor.account is None

    # test that account is a list when set to a list
    actor.account = [Account(provider="google")]
    assert isinstance(actor.account, list)
    assert isinstance(actor.account[0], Account)

    # test that account is an object when set to an object
    actor.account = Account(provider="google")
    assert isinstance(actor.account, Account)

    # test that default values are correctly set
    assert actor.account.enabled is True
    assert actor.account.provider == "google"

def test_define_actor():
    info = {
    "name": "Jesus Lara",
        "account": {
            "address": "jesuslarag@gmail.com",
            "phone": "+34692817379"
        }
    }
    actor = Actor(**info)
    assert isinstance(actor.userid, uuid.UUID)
    actor.userid = 'TEST' ## changing to 'TEST' to avoid checking a uuid
    assert actor.to_json() == '{"userid":"TEST","name":"Jesus Lara","account":{"address":"jesuslarag@gmail.com","phone":"+34692817379"}}'
