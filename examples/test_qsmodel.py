from typing import List, Optional, Mapping, Sequence, Callable, Tuple, Union
from datetime import datetime
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


data = {
    'query_slug': 'walmart_mtd_postpaid_to_goal',
    'description': 'walmart_mtd_postpaid_to_goal',
    'conditions': {'filterdate': 'POSTPAID_DATE', 'store_tier': 'null', 'launch_group': 'null'},
    'cond_definition': {'filterdate': 'date', 'store_tier': 'string', 'launch_group': 'string'},
    'attributes': {"example": "value"},
    'fields': ["client_id", "client_name"], 'ordering': [],
    'h_filtering': False,
    'directives': ('23.1', 12.8),
    'supported': ('1.0', 2.0, '3.0'),
    'query_raw': 'SELECT {fields}\nFROM walmart.postpaid_metrics({filterdate}, {launch_group}, {store_tier})\n{where_cond}',
    'is_raw': False,
    'is_cached': True,
    'provider': 'db',
    'parser': 'pgSQLParser',
    'cache_timeout': 900,
    'cache_refresh': None,
    'cache_options': {},
    'program_id': 3,
    'program_slug': 'walmart', 'dwh': False, 'dwh_scheduler': {},
    'created_at': datetime(2022, 11, 18, 1, 10, 8, 872163),
    'updated_at': datetime(2023, 4, 18, 1, 38, 44, 466221),
    'host_info': ('host', 4568.1),
    'created_by': (1, 33),
    "example": {"a": "hello", "b": 123},
    "more_nested": {"a": "hello", "b": 123}
}

def rigth_now(obj) -> datetime:
    return datetime.now()

class QueryModel(BaseModel):
    query_slug: str = Field(required=True, primary_key=True)
    description: str = Field(required=False, default=None)
    # Source and primary attributes:
    source: Optional[str] = Field(required=False)
    params: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    attributes: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict, comment="Optional Attributes for Query")
    #  main conditions
    conditions: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    cond_definition: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ## filter and grouping options
    fields: Optional[List[str]] = Field(required=False, db_type='array', default_factory=list)
    filtering: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ordering: Optional[List[str]] = Field(required=False, db_type='array')
    grouping: Optional[List[str]] = Field(required=False, db_type='array')
    qry_options: Optional[dict] = Field(required=False, db_type='jsonb')
    h_filtering: bool = Field(required=False, default=False, comment="filtering based on Hierarchical rules.")
    ### Query Information:
    query_raw: str = Field(required=False)
    is_raw: bool = Field(required=False, default=False)
    is_cached: bool = Field(required=False, default=True)
    provider: str = Field(required=False, default='db')
    parser: str = Field(required=False, default='SQLParser', comment="Parser to be used for parsing Query.")
    cache_timeout: int = Field(required=True, default=3600)
    cache_refresh: int = Field(required=True, default=0)
    cache_options: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ## Program Information:
    program_id: int = Field(required=True, default=1)
    program_slug: str = Field(required=True, default='default')
    directives: Tuple[float, float] = Field(required=False)
    supported: Tuple[float, ...] = Field(required=False)
    # DWH information
    dwh: bool = Field(required=True, default=False)
    dwh_driver: str = Field(required=False, default=None)
    dwh_info: Optional[dict] = Field(required=False, db_type='jsonb')
    dwh_scheduler: Optional[dict] = Field(required=False, db_type='jsonb')
    host_info: Tuple[str, int] = Field(required=False)
    # Creation Information:
    created_at: datetime = Field(
        required=False,
        default=datetime.now,
        db_default='now()'
    )
    created_by: tuple[int, str] = Field(required=False)  # TODO: validation for valid user
    updated_at: datetime = Field(
        required=False,
        default=datetime.now,
        encoder=rigth_now
    )
    updated_by: int = Field(required=False)  # TODO: validation for valid user
    example: Mapping[str, str | int] = Field(required=False)
    more_nested: Mapping[str, Union[str, str]] = Field(required=False)

    class Meta:
        driver = 'pg'
        name = 'queries'
        schema = 'public'
        strict = True
        frozen = False
        remove_nulls = True  # Auto-remove nullable (with null value) fields


try:
    slug = QueryModel(**data)
    print(slug)
    print('MAPPING > ', slug.more_nested, type(slug.more_nested))
except ValidationError as e:
    print(e.payload)


data_new = {
    "query_slug": "vision_form_data",
    "description": None,
    "source": None,
    "params": None,
    "attributes": None,
    "conditions": {
        "orgid": "106",
        "formid": "2681",
        "lastdate": "CURRENT_DATE",
        "firstdate": "CURRENT_DATE"
    },
    "cond_definition": {
        "orgid": "integer",
        "formid": "integer",
        "lastdate": "date",
        "firstdate": "date"
    },
    "fields": [],
    "filtering": None,
    "ordering": [],
    "grouping": [],
    "qry_options": None,
    "h_filtering": False,
    "query_raw": "-- Insert New query_slug:vision_form_date\nSELECT  fd.*, fv.FormId, f.OrgId, fv.FormVisitId, VV.VisitDateLocal AS VisitDateLocal --in store TZ\nFROM dbo._FormView_{formid}({orgid},16558) fd\nINNER JOIN dbo.FormVisit fv on fv.FormVisitId = fd.FormVisitId\nINNER JOIN vwVisitView VV ON FV.FormVisitId = VV.FormVisitId\nINNER JOIN forms f on fv.FormId = f.FormId\nWHERE ISNULL([000_055],[000_003]) BETWEEN {firstdate} and {lastdate}\n--- end form data",
    "is_raw": False,
    "is_cached": False,
    "cache_timeout": 3600,
    "cache_refresh": None,
    "cache_options": None,
    "program_id": 1,
    "program_slug": "troc",
    "provider": "sqlserver",
    "parser": "SQLParser",
    "dwh": False,
    "dwh_driver": None,
    "dwh_info": None,
    "dwh_scheduler": None,
    "created_at": "2021-08-28 15:09:00",
    "created_by": None,
    "updated_at": "2023-01-05 11:26:00",
    "updated_by": None
}

if __name__ == '__main__':
    slug = QueryModel(**data_new)
    print(slug)
