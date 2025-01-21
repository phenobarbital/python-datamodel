# types.pxd
# Copyright (C) 2018-present Jesus Lara
#
cdef class SafeDict(dict):
    pass  # No need to declare methods here as they have Python-compatible signatures

cdef class AttrDict(dict):
    pass

cdef class NullDefault(dict):
    pass
