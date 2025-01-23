from typing import Optional
from datamodel import BaseModel, Field
from datamodel.converters import parse_type

class TestOptional(BaseModel):
    services_especialities: Optional[list] = Field(required=False)

opt = TestOptional(services_especialities=None)
columns = opt.get_columns()
print('Columns ', columns)
col = columns['services_especialities']

print(col, opt, columns)
data = ['Pilates', 'Yoga', 'Mindfulness', 'Running', 'Pilates']
newval = parse_type(col, col.type, data)
opt.set('services_especialities', newval)

assert opt.services_especialities == data
assert type(opt.services_especialities) == list
