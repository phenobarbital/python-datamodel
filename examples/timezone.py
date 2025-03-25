from datetime import datetime
from datamodel import BaseModel, Field


class DateTest(BaseModel):
    date_field: datetime = Field(required=True)


if __name__ == '__main__':
    data = {'date_field': "2025-03-24T11:10:22-05:00"}
    date_test = DateTest(**data)
    print(date_test.date_field)
    print(date_test.to_dict())
    print(date_test.to_json())
