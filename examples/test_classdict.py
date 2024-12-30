from typing import Optional
from datamodel import Field
from datamodel.libs.mapping import ClassDict
from datetime import datetime


data = {
    "fields": ["store_id", "postpaid_sales", "postpaid_trended", "apd", "postpaid_to_goal", "hours_worked", "hps", "hps_to_goal"],
    "filterdate": "2023-01-30",
    "filter": {
        "store_id": "!null"
    }
}

def to_field_list(obj) -> list:
    if obj is None:
        return []
    if isinstance(obj, str):
        return [x.strip() for x in obj.split(',')]
    return obj

def empty_dict(obj) -> dict:
    if obj is None:
        return {}
    return obj

class QueryObject(ClassDict):
    """Base Class for all options passed to Parsers.
    """
    source: Optional[str]
    driver: Optional[str]
    conditions: Optional[dict] = Field(default=empty_dict)
    coldef: Optional[dict]
    fields: list = Field(default=to_field_list)
    ordering: Optional[list]
    group_by: Optional[list]
    qry_options: Optional[dict]
    ## filter
    filter: Optional[dict]
    where_cond: Optional[dict]
    and_cond: Optional[dict]
    hierarchy: Optional[list]
    # Limiting Query:
    querylimit: Optional[int]
    query_raw: str
    created_at: datetime


qry = QueryObject(**data, created_at='2022-01-01 00:00:00')
print(qry)
print('Created > ', qry.created_at, type(qry.created_at))
# del qry.fields
# fields = qry.pop('fields')
# print('FIELDS > ', fields)
print('CHECK > ', qry.fields, qry.get('fields'))
print('EXISTS > ', 'fields' in qry)

# qry1 = QueryObject(**data)
# print(qry1)
# del qry1.fields
