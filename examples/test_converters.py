import timeit
from datetime import datetime
from datamodel.converters import to_boolean, to_date
from datamodel import Model, BaseModel, Field
import rst_converters
import random


def test_datamodel():
    class User(BaseModel):
        id: int
        name: str = 'John Doe'
        signup_ts: datetime
    # Using the DataModel defined above

    def test_model():
        user = User(id=1, name="Alice", signup_ts=datetime.now())
        results = rst_converters.parse_datamodel(user)

    print('Test with Rust: ')
    time = timeit.timeit(test_model, number=1)
    print(f"Execution time: {time:.6f} seconds")

    # user = User(id="1", name="Alice", signup_ts=datetime.now())
    # results = rst_converters.validate_datamodel(user)
    # print(results)

def test_dates():
    def test_date():
        for _ in range(10):
            dt = to_date('2024-01-31 00:00:00')
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 31
            dt = to_date('31-12-2022')
            assert dt.year == 2022
            assert dt.month == 12
            assert dt.day == 31
            dt = to_date('12/31/2023')
            assert dt.year == 2023
            assert dt.month == 12
            assert dt.day == 31

    print('Test with Cython: ')
    time = timeit.timeit(test_date, number=100000)
    print(f"Execution time: {time:.6f} seconds")

    def test_rst_date():
        for _ in range(10):
            dt = rst_converters.to_date('2024-01-31 00:00:00')
            assert dt.year == 2024
            assert dt.month == 1
            assert dt.day == 31
            dt = rst_converters.to_date('31-12-2022')
            assert dt.year == 2022
            assert dt.month == 12
            assert dt.day == 31
            dt = rst_converters.to_date('12/31/2023')
            assert dt.year == 2023
            assert dt.month == 12
            assert dt.day == 31

    print('Test with Rust: ')
    time = timeit.timeit(test_rst_date, number=100000)
    print(f"Execution time: {time:.6f} seconds")

def test_booleans():
    inputs = [
        random.choice(
            ["true", "false", "yes", "no", "on", "off", "1", "0"]
        ) for _ in range(10000)]

    def test_boolean():
        for _ in range(10):
            user = {
                "is_active": to_boolean('true'),
                "is_admin": to_boolean('false'),
                "is_staff": to_boolean('yes'),
                "is_superuser": to_boolean('No')
            }
            assert user["is_active"] is True

    print('Test with Cython: ')
    time = timeit.timeit(test_boolean, number=100000)
    print(f"Execution time: {time:.6f} seconds")

    def test_rstboolean():
        for _ in range(10):
            user = {
                "is_active": rst_converters.to_boolean('true'),
                "is_admin": rst_converters.to_boolean('false'),
                "is_staff": rst_converters.to_boolean('yes'),
                "is_superuser": rst_converters.to_boolean('No')
            }
            assert user["is_active"] is True

    print('Test with Rust: ')
    time = timeit.timeit(test_rstboolean, number=100000)
    print(f"Execution time: {time:.6f} seconds")

    def test_cython_boolean():
        for val in inputs:
            to_boolean(val)

    print('Test with Cython: ')
    time = timeit.timeit(test_cython_boolean, number=1000)
    print(f"Execution time: {time:.6f} seconds")

    def test_rust_boolean():
        for val in inputs:
            rst_converters.to_boolean(val)

    print('Test with Rust: ')
    time = timeit.timeit(test_rust_boolean, number=1000)
    print(f"Execution time: {time:.6f} seconds")


if __name__ == '__main__':
    # test_booleans()
    test_dates()
    # test_datamodel()
