# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
cdef class Singleton(type):
    """Singleton.
    Metaclass for Singleton instances.
    Returns:
        cls: a singleton version of the class, there are only one
        version of the instance any time.
    """
    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs)
        cls._instances = {}
        cls.__initialized__ = False

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # First time creating an instance for this class
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            cls.__initialized__ = True
        elif not cls.__initialized__:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls.__initialized__ = True
        return cls._instances[cls]
