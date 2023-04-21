from dataclasses import is_dataclass
from datetime import datetime, date
from datamodel import Model, Field


def now():
    return datetime.now()

class Environment(Model):
    time: datetime = Field(factory=now)
    dow: int
    hour: int
    date: date

    def __post_init__(self):
        self.hour = self.time.hour
        self.dow = self.time.weekday()
        self.date = self.time.date
        super(Environment, self).__post_init__()


env = Environment()
print(env)
print(is_dataclass(env))
