from typing import List, Optional
from datetime import datetime
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError


data = {
    'query_slug': 'walmart_mtd_postpaid_to_goal',
    'description': 'walmart_mtd_postpaid_to_goal',
    'conditions': {'filterdate': 'POSTPAID_DATE', 'store_tier': 'null', 'launch_group': 'null'},
    'cond_definition': {'filterdate': 'date', 'store_tier': 'string', 'launch_group': 'string'},
    'fields': ["client_id", "client_name"], 'ordering': [],
    'h_filtering': False,
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
    'updated_at': datetime(2023, 4, 18, 1, 38, 44, 466221)
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
    # DWH information
    dwh: bool = Field(required=True, default=False)
    dwh_driver: str = Field(required=False, default=None)
    dwh_info: Optional[dict] = Field(required=False, db_type='jsonb')
    dwh_scheduler: Optional[dict] = Field(required=False, db_type='jsonb')
    # Creation Information:
    created_at: datetime = Field(
        required=False,
        default=datetime.now,
        db_default='now()'
    )
    created_by: int = Field(required=False)  # TODO: validation for valid user
    updated_at: datetime = Field(
        required=False,
        default=datetime.now,
        encoder=rigth_now
    )
    updated_by: int = Field(required=False)  # TODO: validation for valid user

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
except ValidationError as e:
    print(e.payload)
