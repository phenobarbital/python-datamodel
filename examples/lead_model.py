from datetime import datetime
from uuid import uuid4, UUID
from pprint import pprint
from datamodel import BaseModel, Column


class Contact(BaseModel):
    contact_id: UUID = Column(primary_key=True, required=False, default=uuid4())
    contact_name: str = Column(required=True, max=254, label="Name")
    phone_number: str = Column(required=True, label="Phone Number")
    email: str = Column(required=True, label="Email")
    role_title: str = Column(required=False, label="Role/Title")
    department: str = Column(required=False, label="Department")
    created_at: datetime = Column(required=False, repr=False)
    updated_at: datetime = Column(required=False, repr=False)
    created_by: int = Column(required=False, repr=False)

    class Meta:
        name = 'contacts'
        description = 'Contact Details'
        schema = 'ambassador'
        strict = True
        display_name = 'contact_name'
        endpoint = '/api/v2/contacts'


class Lead(BaseModel):
    lead_id: UUID = Column(primary_key=True, required=False, default=uuid4())
    hs_lead_id: str = Column(required=False, repr=False)
    contact_id: Contact = Column(required=False, repr=False)
    contact_name: str = Column(required=True, max=254, label="Name")    # Contacts
    phone_number: str = Column(required=True, label="Phone Number")     # Contacts
    email: str = Column(required=True, label="Email")                   # Contacts
    role_title: str = Column(required=False, label="Role/Title")        # Contacts
    department: str = Column(required=False, label="Department")        # Contacts
    company_name: str = Column(required=True, label="Company Name")    # Company
    solutions_of_interest: str = Column(
        required=False,
        label="Solutions of Interest",
        fk='service_catalog|catalog_name',
        api='zammad_catalogs',
        endpoint='api/v2/services/queries/ambassador_offers'
    )
    status: str = Column(required=False, default="Open", repr=False)
    created_at: datetime = Column(required=False, repr=False)
    updated_at: datetime = Column(required=False, repr=False)
    created_by: int = Column(required=False, repr=False)

    class Meta:
        name = 'leads'
        description = 'Lead Details'
        schema = 'ambassador'
        strict = True


pprint(Lead.schema(as_dict=True))
