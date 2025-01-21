from datetime import datetime
from typing import List
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


class ZammadCatalog(BaseModel):
    catalog_id: int = Field(
        primary_key=True,
        required=False,
        db_default="auto"
    )
    catalog_name: str = Field(required=False)
    service_catalog: str = Field(required=True)
    service_name: str = Field(required=False)
    type: str = Field(required=False)
    created_at: datetime = Field(required=False, default=datetime.now())

    class Meta:
        driver = "pg"
        name = "zammad_catalog"
        schema = "navigator"
        app_label = "navigator"
        strict = True


class TicketAttachment(BaseModel):
    filename: str = Field(required=False)
    data: str = Field(required=False)
    mime_type: str = Field(required=False)
    size: str = Field(required=False)


class AbstractTicket(BaseModel):
    title: str = Field(required=True, ui_widget="input", label="Incidence")
    subject: str = Field(required=False, ui_widget="input", label="Subject", repr=False)
    type: str = Field(required=False, default="Default Ticket", repr=False)
    ctoken: str = Field(required=False, repr=False)
    body: str = Field(required=True, ui_widget="textarea", label="Tell Us What Happened?")
    group: str = Field(required=False, default='People Team', repr=False)
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
        label="Add an attachment ...",
        ui_widget="dropzone",
        default_factory=list
    )

    class Meta:
        strict: bool = True
        extra: str = "forbid"
        title: str = "Support Ticket"
        as_objects: bool = True


@pytest.mark.parametrize("as_objects", [True, False])
def test_abstract_ticket_without_attachments(as_objects):
    AbstractTicket.Meta.as_objects = as_objects

    payload = {
        "type": "Incident",
        "group": "Users",
        "subject": "test ticket",
        "attachments": [],
        "service_catalog": "We Protect U::Discrimination",
        "title": "test ticket",
        "body": "test ticket",
        "ctoken": "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="
    }

    ticket = AbstractTicket(**payload)
    assert ticket.type == "Incident"
    assert ticket.group == "Users"
    assert ticket.subject == "test ticket"
    assert ticket.attachments == []
    if as_objects:
        assert ticket.service_catalog.service_catalog == "We Protect U::Discrimination"
    else:
        assert ticket.service_catalog == "We Protect U::Discrimination"
    assert ticket.title == "test ticket"
    assert ticket.body == "test ticket"
    assert ticket.ctoken == "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="

    ticket_dict = ticket.to_dict()
    assert isinstance(ticket_dict, dict)
    assert ticket_dict["title"] == "test ticket"
    assert ticket_dict["attachments"] == []


@pytest.mark.parametrize("as_objects", [True, False])
def test_abstract_ticket_with_attachments(as_objects):
    AbstractTicket.Meta.as_objects = as_objects

    payload_attach = {
        "type": "Incident",
        "group": "Users",
        "subject": "test ticket",
        "attachments": [
            {"data": "XXXXX", "filename": "file.svg"}
        ],
        "service_catalog": "We Protect U::Discrimination",
        "title": "test ticket",
        "body": "test ticket",
        "ctoken": "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="
    }

    ticket = AbstractTicket(**payload_attach)
    assert ticket.type == "Incident"
    assert ticket.group == "Users"
    assert ticket.subject == "test ticket"
    assert len(ticket.attachments) == 1
    assert ticket.attachments[0].filename == "file.svg"
    assert ticket.attachments[0].data == "XXXXX"
    if as_objects:
        assert ticket.service_catalog.service_catalog == "We Protect U::Discrimination"
    else:
        assert ticket.service_catalog == "We Protect U::Discrimination"
    assert ticket.title == "test ticket"
    assert ticket.body == "test ticket"
    assert ticket.ctoken == "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="


def test_abstract_ticket_validation_error():
    payload_invalid = {
        "type": "Incident",
        "group": "Users",
        "body": "test ticket",
        "ctoken": "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="
    }

    with pytest.raises(ValueError) as exc_info:
        AbstractTicket(**payload_invalid)

    error = exc_info.value
    assert "title" in str(error)


@pytest.mark.parametrize("as_objects", [True, False])
def test_zammad_catalog_defaults(as_objects):
    ZammadCatalog.Meta.as_objects = as_objects

    catalog = ZammadCatalog(catalog_name="Test Catalog", service_catalog="Test Service")
    assert catalog.catalog_name == "Test Catalog"
    assert catalog.service_catalog == "Test Service"
    assert catalog.created_at is not None
    assert isinstance(catalog.created_at, datetime)
    if as_objects:
        assert catalog.service_name is None
        assert catalog.type is None
