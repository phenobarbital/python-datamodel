from asyncdb.models import Model, Field
from datamodel import BaseModel
from datamodel.exceptions import ValidationError


class User(BaseModel):
    user_id: int = Field(required=True, primary_key=True)
    username: str = Field(required=True)


class Employee(BaseModel):
    associate_oid: str = Field(required=True, primary_key=True)
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
    username: str = Field(required=False)
    user_id: User = Field(
        required=False,
        nullable=True,
        fk='user_id|display_name',
        api='users',
        endpoint='api/v1/users',
        label="User ID"
    )

    def email(self):
        return self.corporate_email

    class Meta:
        name = 'vw_active_employees'
        schema = 'troc'
        strict = True


user = User(user_id=35, username='johndoe')
print(user)
try:
    employee = Employee(
        associate_oid='123456789',
        associate_id='123456789',
        position_id='123456789',
        file_number='123456789',
        operator_name='John Doe',
        first_name='John',
        last_name='Doe',
        display_name='John Doe',
        user_id=35
    )
    print(employee)
except ValidationError as ex:
    print(ex.payload)
