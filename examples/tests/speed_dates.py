import timeit
from datetime import datetime
import pendulum
import ciso8601

def ciso():
    obj = '1978-10-23'
    return ciso8601.parse_datetime(obj).date()

def pend():
    obj = '23-10-1978'
    return pendulum.parse(obj, strict=False).date()

def strf():
    obj = '1978-10-23'
    return datetime.strptime(obj, "%Y-%m-%d").date()


time = timeit.timeit(ciso, number=10000)
print(f"CISO Execution time: {time:.6f} seconds")

time = timeit.timeit(pend, number=10000)
print(f"Pendulum Execution time: {time:.6f} seconds")

time = timeit.timeit(strf, number=10000)
print(f"Strptime Execution time: {time:.6f} seconds")
