from typing import List
from datetime import datetime
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
    created_at: str = Field(required=False, default=datetime.now())

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
        default="Default Ticket",
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
        # default_factory=list
    )

    class Meta:
        strict: bool = True
        extra: str = "forbid"
        title: str = "Support Ticket"
        as_objects: bool = True


def create_ticket():
    payload = {
        "type": "Incident",
        "group": "Users",
        "subject": "test ticket",
        "attachments": [],
        "service_catalog": "We Protect U::Discrimination",
        "title": "test ticket",
        "body": "test ticket ",
        "ctoken": "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="
    }
    # Payload with Attachments:
    payload_attach = {
        "type": "Incident",
        "group": "Users",
        "subject": "test ticket",
        "attachments": [
            {"data": "XXXXX", "filename": "file.svg"}
        ],
        "service_catalog": "We Protect U::Discrimination",
        "title": "test ticket",
        "body": "test ticket ",
        "ctoken": "03AFcWeA7JtyzsmZEVY0QO84bCOJLiAlj9MyQxWXApyixNjj0c8x1Q=="
    }
    try:
        ticket = AbstractTicket(**payload)
        print(ticket)
        print('===')
        print(ticket.to_dict())
        print("====")
        # Ticket with attachment:
        ticket = AbstractTicket(**payload_attach)
        print(ticket)
    except ValidationError as e:
        print(f"Validation Error: {e.payload}")
        return


if __name__ == "__main__":
    create_ticket()
