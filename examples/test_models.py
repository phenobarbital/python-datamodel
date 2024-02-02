from typing import Optional, List
from datetime import datetime
from datamodel import BaseModel, Column, Field
from datamodel.exceptions import ValidationError

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

class Program(BaseModel):
    program_id: int
    program_slug: str
class Reward(BaseModel):
    """
    Rewards and Badges Management.
    """
    reward_id: int = Field(
        primary_key=True, required=False, db_default="auto", repr=False
    )
    reward: str = Field(required=True, nullable=False)
    description: str = Field(required=False)
    points: int = Field(required=False, default=10)
    programs: Optional[List[Program]] = Field(
        required=False,
        fk="program_slug|program_name",
        api="programs",
        label="Programs",
        nullable=True,
        multiple=True,
        default_factory=list
    )
    icon: str = Field(
        required=False,
        default="",
        ui_widget="ImageUploader",
        ui_help="Badge Icon, Hint: please use a transparent PNG."
    )
    attributes: Optional[dict] = Field(
        required=False, default_factory=dict, db_type="jsonb", repr=False
    )
    availability_rule: Optional[dict] = Field(
        required=False, default_factory=dict, db_type="jsonb", repr=False
    )
    effective_date: datetime = Field(required=False, default=datetime.now())
    inserted_at: datetime = Field(
        required=False,
        default=datetime.now(),
        readonly=True
    )
    deleted_at: datetime = Field(
        required=False,
        readonly=True
    )

    class Meta:
        driver = "pg"
        name = "rewards"
        schema = "rewards"
        endpoint: str = 'rewards/api/v1/rewards'
        strict = True

reward = {
    "reward_id": 1001,
    "reward": "Test Reward",
    "description": "Test Reward Description",
    "points": 100,
    "icon": "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
    "availability_rule": {
        "dow": [1, 2, 3, 4, 5]
    }
}

try:
    r = Reward(**reward)
    print(r)
except ValidationError as exc:
    print(exc.payload)
