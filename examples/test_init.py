from dataclasses import dataclass, InitVar, asdict
from datamodel import BaseModel, Field

@dataclass
class User:
    name: str
    age: int
    password: str = None
    user: str = None
    username: InitVar = ''

    def __post_init__(self, username):
        self.user = username


try:
    user = User(name="John Doe", age=30)
    print(user.name)  # Output: John Doe
    print(user.age)  # Output: 30
    print(user.password)  # Output: None
    print(user.user)  # Output: John Doe
    print('Init > ', user.username, type(user.username))
    print('--------------------')
    print(asdict(user))
except TypeError as e:
    print(f"TypeError: {e}")


class OtherUser(BaseModel):
    name: str
    age: int
    password: str = None
    user: str
    username: InitVar = ''

    def __post_init__(self, username):
        self.user = username
        super().__post_init__()


try:
    user = OtherUser(name="John Doe", age=30)
    print(user.name)  # Output: John Doe
    print(user.age)  # Output: 30
    print(user.password)  # Output: None
    print(user.user)  # Output: John Doe
    print('Init > ', user.username, type(user.username))  # Output: ''
    print('--------------------')
    print(user.to_dict())
except TypeError as e:
    print(f"TypeError: {e}")
