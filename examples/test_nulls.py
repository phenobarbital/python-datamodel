from typing import Optional
from datetime import datetime
from datamodel import Field, BaseModel

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
    fields: Optional[list] = Field(required=False, db_type='array')
    filtering: Optional[dict] = Field(required=False, db_type='jsonb', default_factory=dict)
    ordering: Optional[list] = Field(required=False, db_type='array')
    grouping: Optional[list] = Field(required=False, db_type='array')
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
        default=datetime.now(),
        db_default='now()'
    )

    class Meta:
        driver = 'pg'
        name = 'queries'
        schema = 'troc'
        app_label = 'troc'
        strict = False
        frozen = False
        remove_nulls = True  # Auto-remove nullable (with null value) fields

query = QueryModel(query_slug='walmart_stores')
query.create_field("tester", 'Prueba')
print('TEST >> ', query.tester)
print('EXPORT')
print(query.to_dict())
