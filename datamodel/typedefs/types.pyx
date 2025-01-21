# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#

cdef class SafeDict(dict):
    """
    SafeDict.

    Allow to using partial format strings

    """
    def __missing__(self, str key):
        """Missing method for SafeDict."""
        return "{" + key + "}"


cdef class AttrDict(dict):
    """
    AttrDict.
    Allow to using a dictionary like an object
    """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


cdef class NullDefault(dict):
    """NullDefault.

    When an attribute is missing, return default.
    """
    def __missing__(self, key):
        return ''
