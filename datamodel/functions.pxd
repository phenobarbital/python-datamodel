# function.pxd
from libcpp cimport bool as bool_t

cpdef bool_t is_iterable(object value)
cpdef bool_t is_primitive(object value)
cpdef bool_t is_dataclass(object obj)
cpdef bool_t is_function(object value)
cpdef bool_t is_callable(object value)
cpdef bool_t is_empty(object value)
