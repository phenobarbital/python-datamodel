# test_example_model.py
from typing import Callable, Awaitable
import asyncio
import pytest
from datamodel import BaseModel, Field
from datamodel.exceptions import ValidationError

# Define the ExampleModel using your DataModel framework:
class ExampleModel(BaseModel):
    callback: Callable[[int], str] = Field(required=True)
    async_result: Awaitable[int] = Field(required=True)

# --- Valid Cases ---

# Define a simple synchronous callback function.
def my_callback(x: int) -> str:
    return f"Value: {x}"

# Define an asynchronous function.
async def my_async_func() -> int:
    await asyncio.sleep(0.01)
    return 42

def test_example_model_valid():
    # Create an instance with valid types.
    instance = ExampleModel(
        callback=my_callback,
        async_result=my_async_func()  # note: a coroutine object
    )

    # Check that callback is callable.
    assert callable(instance.callback), "callback field should be callable."

    # Check that async_result is awaitable.
    assert hasattr(instance.async_result, '__await__'), "async_result should be awaitable."

    # Await the async result and verify its value.
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(instance.async_result)
    loop.close()
    assert result == 42


# --- Invalid Cases ---

def test_example_model_invalid_callback():
    # async_result is valid (using a coroutine)
    coro = my_async_func()

    with pytest.raises(ValidationError) as excinfo:
        # Pass a non-callable (a string) instead of a callable for callback.
        ExampleModel(callback="not a callable", async_result=coro)

    error_str = str(excinfo.value)
    assert "callback" in error_str, "Validation error should mention the callback field."


def test_example_model_invalid_async_result():
    # callback is valid (a callable)
    cb = my_callback

    with pytest.raises(ValidationError) as excinfo:
        # Pass a non-awaitable (an integer) instead of an awaitable.
        ExampleModel(callback=cb, async_result=123)

    error_str = str(excinfo.value)
    assert "async_result" in error_str, "Validation error should mention the async_result field."
