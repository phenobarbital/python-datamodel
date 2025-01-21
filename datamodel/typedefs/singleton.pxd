# singleton.pxd

cdef class Singleton(type):
    """
    Singleton.
    Metaclass for Singleton instances.
    """
    cdef dict _instances
    cdef bint __initialized__
