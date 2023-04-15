from datetime import datetime

_started = datetime.now()
from pydantic import AnyUrl
from pydantic.dataclasses import dataclass
_end = datetime.now()

print(f'Pydantic Loaded at: {_end - _started}')

_started = datetime.now()
from datamodel import Field
from dataclasses import dataclass

_end = datetime.now()
print(f'BaseModel Loaded at: {_end - _started}')
