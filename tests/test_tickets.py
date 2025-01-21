from typing import List
from datetime import datetime
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class TicketAttachment(BaseModel):
    filename: str = Field(required=False)
    data: str = Field(required=False)
    mime_type: str = Field(required=False)
    size: str = Field(required=False)

class ZammadCatalog(BaseModel):
    catalog_id: int = Field(
        primary_key=True,
        required=False,
        db_default="auto"
    )
    catalog_name: str = Field(required=True)
    service_catalog: str = Field(required=True)
    service_name: str = Field(required=False)
    type: str = Field(required=False)
    created_at: str = Field(required=False, default=datetime.now)

    class Meta:
        driver = "pg"
        name = "zammad_catalog"
        schema = "navigator"
        app_label = "navigator"
        strict = True

class SimpleSupportTicket(BaseModel):
    """Create a Support Ticket in Zammad.
    """
    title: str = Field(
        required=True,
        ui_widget="input",
        label="Incidence"
    )
    subject: str = Field(
        required=False,
        ui_widget="input",
        label="Subject",
        repr=False
    )
    type: str = Field(
        required=False,
        default='incident',
        repr=False
    )
    ctoken: str = Field(
        required=False,
        repr=False
    )
    body: str = Field(
        required=True,
        ui_widget="textarea",
        label="Tell Us What Happened?"
    )
    group: str = Field(
        required=False,
        default='People Team',
        repr=False
    )
    firstname: str = Field(
        required=False,
        label="First Name"
    )
    lastname: str = Field(
        required=False,
        label="Last Name"
    )
    email: str = Field(
        required=True,
        label="User Email",
        min=4,
        max=36,
    )
    service_catalog: ZammadCatalog = Field(
        required=True,
        fk='service_catalog|catalog_name',
        api='zammad_catalogs',
        endpoint='support/api/v1/zammad_catalogs?service_name=Employee%20Support',
        label="Choose a category:"
    )
    attachments: List[TicketAttachment] = Field(
        required=False,
        multiple=True,
        default_factory=list,
        label="Add an attachment ...",
        ui_widget="dropzone"
    )

    class Meta:
        strict: bool = True
        extra: str = "forbid"
        title: str = "Support Ticket"
        as_objects: bool = True
        settings: dict = {
            "showSubmit": True,
            "SubmitLabel": "Create Ticket",
            "showCancel": True,
        }

@pytest.fixture
def sample_catalog():
    """
    Provide a sample ZammadCatalog object for testing.
    """
    return ZammadCatalog(
        catalog_id=123,
        catalog_name="Hardware Support",
        service_catalog="Employee Support",
        service_name="Laptop Issues",
        type="incident",
        created_at=str(datetime(2023, 1, 1, 12, 0, 0))
    )


def test_create_support_ticket_ok(sample_catalog):
    """
    Test creating a SimpleSupportTicket successfully (no attachments).
    """
    data = {
        "title": "My Keyboard is not working",
        "body": "It suddenly stopped responding this morning.",
        "email": "user@example.com",
        "service_catalog": sample_catalog,
    }
    ticket = SimpleSupportTicket(**data)
    assert ticket.title == data["title"]
    assert ticket.body == data["body"]
    assert ticket.email == data["email"]
    # verify service_catalog is indeed a ZammadCatalog
    assert isinstance(ticket.service_catalog, ZammadCatalog)
    assert ticket.service_catalog.catalog_name == "Hardware Support"
    # attachments should be an empty list by default
    assert isinstance(ticket.attachments, list)
    assert ticket.attachments == []


def test_create_support_ticket_with_attachments(sample_catalog):
    """
    Test creating a SimpleSupportTicket with attachments,
    verifying that each attachment is a TicketAttachment object.
    """
    data = {
        "title": "Need help with a software install",
        "body": "Installation keeps failing on step 3.",
        "email": "user2@example.com",
        "service_catalog": sample_catalog,
        "attachments": [
            {
                "filename": "error_log.txt",
                "data": "base64encodeddata==",
                "mime_type": "text/plain",
                "size": "12345"
            },
            {
                "filename": "screenshot.png",
                "data": "base64encodedPNG==",
                "mime_type": "image/png",
                "size": "204800"
            }
        ]
    }
    ticket = SimpleSupportTicket(**data)
    assert len(ticket.attachments) == 2

    # Check each attachment is a proper TicketAttachment object
    for att in ticket.attachments:
        assert isinstance(att, TicketAttachment), (
            f"Attachment {att} is not a TicketAttachment"
        )

    # Check the first attachment's details
    assert ticket.attachments[0].filename == "error_log.txt"
    assert ticket.attachments[0].mime_type == "text/plain"
    # Check the second one
    assert ticket.attachments[1].filename == "screenshot.png"
    assert ticket.attachments[1].mime_type == "image/png"


def test_support_ticket_missing_required_field(sample_catalog):
    """
    If a required field (e.g., 'title' or 'body' or 'email') is missing,
    a ValidationError should be raised, thanks to strict mode.
    """
    data = {
        # 'title' is missing here
        "body": "I have a problem but no title!",
        "email": "missingtitle@example.com",
        "service_catalog": sample_catalog
    }
    with pytest.raises(ValueError) as excinfo:
        SimpleSupportTicket(**data)

    # We can inspect the excinfo if needed,
    # but just verifying that ValueError was raised is enough.
    assert isinstance(excinfo.value, ValueError)
    assert "title" in str(excinfo.value)





def test_support_ticket_schema_generation():
    """
    Check the structure of the JSON-Schema produced by schema(as_dict=True).
    """
    # Generate the schema as a dictionary
    schema_dict = SimpleSupportTicket.schema(as_dict=True)

    assert schema_dict["title"] == "Support Ticket"
    assert schema_dict["type"] == "object"
    assert "properties" in schema_dict
    # Check for a required field:
    assert "title" in schema_dict["required"], "'title' must be a required field"

    # e.g. ensure attachments is recognized as a list
    attachments_prop = schema_dict["properties"]["attachments"]
    assert attachments_prop["type"] == "array"

    # as the class cached the schema, calling .schema(as_dict=True) again should
    # return the same dictionary reference:
    second_call = SimpleSupportTicket.schema(as_dict=True)
    assert second_call is schema_dict  # might be true if caching
