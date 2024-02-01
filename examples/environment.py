from datetime import datetime, date
import time
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

def now():
    return datetime.today()

def curtime():
    return time.time()

class Environment(BaseModel):
    time: float = Field(default_factory=curtime)
    timestamp: datetime = Field(default_factory=now)
    dow: int
    day_of_week: int
    hour: int
    curdate: date = Field(required=False, default=datetime.today().date())
    month: int

    def __post_init__(self):
        self.hour = self.timestamp.hour
        self.dow = self.timestamp.weekday()
        self.day_of_week = self.dow
        self.curdate = self.timestamp.date()
        self.month = self.timestamp.month
        super(Environment, self).__post_init__()


if __name__ == '__main__':
    try:
        env = Environment()
        print(env)
    except ValidationError as e:
        print(e.payload)
