"""
JSON Encoders.
"""
from .json import JSONContent, json_encoder

DefaultEncoder = JSONContent

class BaseEncoder:
    """
    Encoder replacement for json.dumps using orjson
    """

    def __init__(self, *args, **kwargs):
        encoder = DefaultEncoder(*args, **kwargs)
        self.encode = encoder.__call__
