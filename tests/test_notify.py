from typing import Union, Optional, Any, Literal
import uuid
from datetime import datetime
from pathlib import Path
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

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


# ----------------------------------------------------------------------------------------
# Test Account
# ----------------------------------------------------------------------------------------
def test_account_valid():
    acc = Account(
        provider="dummy_provider",
        enabled=False,
        address=["123 Main St", "456 Secondary Ave"],
        number=["555-1234", "555-5678"],
        userid="someuser123",
        attributes={"foo": "bar"}
    )
    assert acc.provider == "dummy_provider"
    assert acc.enabled is False
    assert acc.address == ["123 Main St", "456 Secondary Ave"]
    assert acc.userid == "someuser123"
    assert acc.attributes["foo"] == "bar"

def test_account_invalid():
    # For example, pass a non-boolean to 'enabled'
    with pytest.raises(ValidationError):
        Account(provider="dummy", enabled="NotABool")


# ----------------------------------------------------------------------------------------
# Test Actor
# ----------------------------------------------------------------------------------------
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
    with pytest.raises(ValidationError):
        Actor(name={"user": 123})  # name must be str or any type can be converted.


# ----------------------------------------------------------------------------------------
# Test Message
# ----------------------------------------------------------------------------------------
def test_message_valid():
    m = Message(
        name="TestMessage",
        body={"key": "value"},
        content="Hello, world!",
        sent=datetime(2025, 3, 14, 12, 30),
        template=Path("/tmp/example_template.txt")
    )
    assert m.name == "TestMessage"
    assert m.body == {"key": "value"}
    assert m.content == "Hello, world!"
    assert m.sent == datetime(2025, 3, 14, 12, 30)
    assert m.template.name == "example_template.txt"

def test_message_invalid():
    # e.g. template must be a Path, pass an int
    with pytest.raises(ValidationError):
        Message(name="BadMessage", template=123)


# ----------------------------------------------------------------------------------------
# Test Attachment
# ----------------------------------------------------------------------------------------
def test_attachment_valid():
    attach = Attachment(
        name="file.txt",
        content="FileContentBytesHere",
        content_type="text/plain",
        type="inline"
    )
    assert attach.name == "file.txt"
    assert attach.content_type == "text/plain"

def test_attachment_invalid():
    # e.g. pass non-string for 'name'
    with pytest.raises(ValidationError):
        Attachment(name={"user": 123}, content=None, content_type="text/plain", type="inline")


# ----------------------------------------------------------------------------------------
# Test BlockMessage
# ----------------------------------------------------------------------------------------
def test_blockmessage_valid():
    # content_type must be one of
    # "text/plain", "text/html", "multipart/alternative", "application/json"
    bm = BlockMessage(
        name="BlockMsg01",
        body="Body content",
        content="Additional text",
        template=Path("/tmp/block_template.txt"),
        content_type="text/html",
        flags=["urgent", "read-receipt"]
    )
    assert bm.content_type == "text/html"
    assert bm.flags == ["urgent", "read-receipt"]

def test_blockmessage_invalid_content_type():
    # Provide an invalid content_type to ensure it raises
    with pytest.raises(ValueError):
        BlockMessage(
            name="BlockMsg02",
            body=None,
            template=Path("/tmp/block_template.txt"),
            content_type="INVALID/TYPE",
            flags=[]
        )

def test_blockmessage_invalid_sender():
    # e.g. pass a string for sender where we want an Actor or list[Actor]
    with pytest.raises(ValueError):
        BlockMessage(
            name="BlockMsg03",
            body="Hello",
            template=Path("template.txt"),
            sender="NotAnActorObject",
            flags=["someflag"]
        )
