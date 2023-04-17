from typing import Optional
import timeit
import pyperf
from datamodel import Field
from datamodel.models import Model
# from datamodel.libs.mapping import ClassDict
from datamodel.libs.mutables import ClassDict

class QueryObject(ClassDict):
    """Base Class for all options passed to Parsers.
    """
    name: str
    source: Optional[str] = Field(required=False, default='db')
    driver: Optional[str] = Field(required=False, default='pg')
    conditions: Optional[dict] = Field(required=False, default={})
    where_cond: Optional[dict] = Field(default={})
    and_cond: Optional[dict] = Field(default={})
    query_raw: str

class QObject(Model):
    """Base Class for all options passed to Parsers.
    """
    name: str
    source: Optional[str] = Field(required=False, default='db')
    driver: Optional[str] = Field(required=False, default='pg')
    conditions: Optional[dict] = Field(required=False, default_factory=dict)
    where_cond: Optional[dict] = Field(default_factory=dict)
    and_cond: Optional[dict] = Field(default_factory=dict)
    query_raw: str

def create_dicts():
    for i in range(100):
        QueryObject(name='Test', source='source', driver='driver', conditions={"filterdate": "CURRENT_DATE"}, where_cond={"is_open", True})


def create_models():
    for i in range(100):
        QObject(name='Test', source='source', driver='driver', conditions={"filterdate": "CURRENT_DATE"}, where_cond={"is_open", True})


print('=== TESTING CREATION OF DICT === ')
time = timeit.timeit(create_dicts, number=10000)
print(f"Execution time: {time:.6f} seconds")
print('===')
runner = pyperf.Runner()
runner.bench_func('create_objects', create_dicts)


# print('=== TESTING CREATION OF MODEL === ')
# time = timeit.timeit(create_models, number=10000)
# print(f"Execution time: {time:.6f} seconds")
# print('===')
# runner = pyperf.Runner()
# runner.bench_func('create_models', create_models)
