# test_example_model.py
from typing import Callable, Awaitable
import asyncio
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

# --- Valid Cases ---

# Define a simple synchronous callback function.
def my_callback(x: int) -> str:
    return f"Value: {x}"

# Define an asynchronous function.
async def my_async_func() -> int:
    await asyncio.sleep(0.01)
    return 42

# Define the ExampleModel using your DataModel framework:
class ExampleModel(BaseModel):
    callback: Callable[[int], str] = Field(required=True)
    async_result: Awaitable[int] = Field(required=True)

try:
    instance = ExampleModel(
        callback=my_callback,
        async_result=my_async_func()  # note: a coroutine object
    )
except ValidationError as e:
    print(e.payload)
