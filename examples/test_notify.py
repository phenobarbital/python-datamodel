from typing import Union, Optional, Any, Literal
import uuid
from datetime import datetime
from pathlib import Path
from datamodel import BaseModel, Field


CONTENT_TYPES = [
    "text/plain",
    "text/html",
    "multipart/alternative",
    "application/json"
]

def auto_uuid(*args, **kwargs):  # pylint: disable=W0613
    return uuid.uuid4()


def now():
    return datetime.now()

class Account(BaseModel):
    """
    Attributes for using a Provider by an User (Actor)
    """

    provider: str = Field(required=True, default="dummy")
    enabled: bool = Field(required=True, default=True)
    address: Union[str, list[str]] = Field(required=False, default_factory=list)
    number: Union[str, list[str]] = Field(required=False, default_factory=list)
    userid: str = Field(required=False, default="")
    attributes: dict = Field(required=False, default_factory=dict)

    def set_address(self, address: Union[str, list[str]]):
        self.address = [address] if isinstance(address, str) else address


class Actor(BaseModel):
    """
    Basic Actor (meta-definition), can be an Sender or a Recipient
    """

    userid: uuid.UUID = Field(required=False, primary_key=True, default=auto_uuid)
    name: str
    account: Optional[Account]
    accounts: Optional[list[Account]]

    def __str__(self) -> str:
        return f"<{self.name}: {self.userid}>"

class Message(BaseModel):
    """
    Message.
    Base-class for Message blocks for Notify
    TODO:
     * template needs a factory function to find a jinja processor
     *
    """

    name: str = Field(required=True, default=auto_uuid)
    body: Union[str, dict] = Field(default=None)
    content: str = Field(required=False, default="")
    sent: datetime = Field(required=False, default=now)
    template: Path

class Attachment(BaseModel):
    """Attachement.

    an Attachment is any document attached to a message.
    """

    name: str = Field(required=True)
    content: Any = None
    content_type: str
    type: str

class BlockMessage(Message):
    """
    BlockMessage.
    Class for Message Notifications
    TODO:
     * template needs a factory function to find a jinja processor
     *
    """

    sender: Union[Actor, list[Actor]] = Field(required=False)
    recipient: Union[Actor, list[Actor]] = Field(required=False)
    content_type: Literal[
        "text/plain",
        "text/html",
        "multipart/alternative",
        "application/json"
    ] = Field(default="text/plain")
    attachments: list[Attachment] = Field(default_factory=list)
    flags: list[str]

def test_actor_valid():
    a = Actor(
        name="Alice",
        account=Account(provider="prov", enabled=True)
    )
    assert a.name == "Alice"
    assert a.account.provider == "prov"
    # accounts can be None or list[Account]
    a2 = Actor(
        name="Bob",
        accounts=[Account(provider="prov2")]
    )
    assert a2.accounts[0].provider == "prov2"

def test_actor_invalid():
    # Provide a wrong type for 'name'
    actor = Actor(name={"user": 123})
    print(actor.name, type(actor.name))

if __name__ == "__main__":
    test_actor_invalid()
    print("test_notify.py: all tests passed")
