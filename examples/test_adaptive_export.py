from pprint import pprint
from datamodel import BaseModel, Field

class UserInfo(BaseModel):
    """User information."""
    myComment: str = Field(style='text')
    myEmail: str = Field(style='email')
    myTel: str = Field(style='url')
    myPassword: str = Field(style='password')
    myNumber: str = Field(style='number')
    isSuper: bool = Field(label='Super User')

    class Meta:
        submit: str = 'OK'


if __name__ == '__main__':
    schema = UserInfo().to_adaptive()
    print(schema)
