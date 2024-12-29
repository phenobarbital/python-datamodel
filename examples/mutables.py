from typing import Optional
import timeit
import pyperf
from datamodel import Field
from datamodel.libs.mapping import ClassDict, ClassDictConfig


class QueryObject(ClassDict):
    """Base Class for all options passed to Parsers.
    """
    config = ClassDictConfig(parse_values=True)
    source: Optional[str]
    driver: Optional[str]
    conditions: Optional[dict] = Field(default={})
    coldef: Optional[dict]
    ordering: Optional[list]
    group_by: Optional[list]
    qry_options: Optional[dict]
    ## filter
    filter: Optional[dict] = Field(default={})
    where_cond: Optional[dict]
    and_cond: Optional[dict]
    hierarchy: Optional[list]
    # Limiting Query:
    querylimit: Optional[int]
    query_raw: str

def create_objects():
    for i in range(20):
        QueryObject(source='source', driver='driver')

time = timeit.timeit(create_objects, number=10000)
print(f"Execution time: {time:.6f} seconds")
print('===')
runner = pyperf.Runner()
runner.bench_func('create_objects', create_objects)
