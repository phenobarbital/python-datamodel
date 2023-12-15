from typing import Optional
from datetime import datetime
import pprint
from enum import Enum
from datamodel import BaseModel, Field

pp = pprint.PrettyPrinter(width=41, compact=True)


class Reward(BaseModel):
    reward_id: int = Field(
        primary_key=True, required=False, db_default="auto", repr=False
    )
    reward: str = Field(required=True, nullable=False)
    description: str = Field(required=False)
    points: int = Field(required=False, default=1)
    programs: str = Field(required=False)
    program_slug: str = Field(required=False, default="")
    region: str = Field(required=False, default="")
    department: list = Field(required=False, default_factory=list)
    icon: str = Field(
        required=False,
        default="",
        ui_widget="ImageUploader",
        ui_help="Badge Icon, Hint: please use a transparent PNG."
    )
    attributes: Optional[dict] = Field(
        required=False, default_factory=dict, db_type="jsonb"
    )
    resource_link: str = Field(required=False, default="")
    effective_date: datetime = Field(required=False, default=datetime.now())
    inserted_at: datetime = Field(required=False, default=datetime.now())

    class Meta:
        driver = "pg"
        name = "rewards"
        schema = "navigator"
        app_label = "navigator"
        strict = True

class Employee(BaseModel):
    associate_id: str = Field(required=True)
    position_id: str = Field(required=True)
    file_number: str = Field(required=True)
    operator_name: str = Field(required=True)
    first_name: str = Field(required=False)
    last_name: str = Field(required=False)
    display_name: str = Field(required=False)
    corporate_email: str = Field(required=True)
    job_code: str = Field(required=False)
    job_code_title: str = Field(required=False)
    region_code: str = Field(required=False)
    department: str = Field(required=False)
    department_code: str = Field(required=False)
    location_code: str = Field(required=False)
    work_location: str = Field(required=False)
    reports_to_associate_oid: str = Field(required=False)
    reports_to_associate_id: str = Field(required=False)
    reports_to_position_id: str = Field(required=False)

    def email(self):
        return self.corporate_email

    class Meta:
        name = 'vw_active_employees'
        schema = 'troc'
        strict = True


class BadgeAssign(BaseModel):
    reward_id: Reward = Field(
        required=True, fk='reward_id|reward', endpoint='rewards', label="Badge"
    )
    reward: str = Field(repr=False)
    receiver_email: Employee = Field(
        required=True,
        fk='corporate_email|display_name',
        api='adp_employees'
    )
    job_code: str = Field(
        endpoint={
            "url": "api/v1/adp_employees",
            "key": "job_code",
            "value": "job_code_title"
        }
    )
    # receiver_user: User = Field(
    #     required=True,
    #     fk='user_id|display_name',
    #     api='programs',
    #     repr=False
    # )
    giver_user: int = Field(required=True)
    giver_email: str = Field(required=True)
    giver_employee: str = Field(required=False)
    giver_message: str = Field(
        ui_widget='textarea',
        ui_help='Message to the receiver',
        label="Message"
    )

    class Meta:
        name = 'users_rewards'
        schema = 'navigator'
        endpoint: str = 'api/v1/assign_rewards'
        strict = True

schema = BadgeAssign.schema(as_dict=False)
print(schema)
# pp.pprint(schema)
