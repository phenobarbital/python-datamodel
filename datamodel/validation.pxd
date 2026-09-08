# cython: language_level=3, embedsignature=True
# Copyright (C) 2018-present Jesus Lara
#
cdef dict _validate_constraints(object field, str name, object value, object annotated_type, object val_type)

# FEAT-2 / TASK-13. Additions only: the pre-existing declaration above is
# unchanged, so the cimport surface stays backward compatible.
cdef int fastpath_kind(object f, object value, object annotated_type) except -1
cdef void count_generic_dispatch() noexcept
cpdef bint profiling_compiled_in()
cpdef long generic_dispatch_count()
cpdef void reset_generic_dispatch_count()
