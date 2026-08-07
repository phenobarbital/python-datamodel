"""Rust-accelerated parsers for python-datamodel.

Provides type conversion functions (to_date, to_datetime, to_integer, etc.)
implemented in Rust via PyO3 for performance. Falls back gracefully if the
Rust extension is not compiled.
"""

HAS_RUST = False

try:
    from ._rs_parsers import (  # type: ignore[import-not-found]
        to_string,
        strtobool,
        to_boolean,
        to_date,
        to_datetime,
        to_timestamp,
        slugify_camelcase,
        to_uuid_str,
        to_uuid_obj,
        to_uuid,
        to_integer,
        to_float,
        to_decimal,
        to_list,
    )

    HAS_RUST = True
except ImportError:
    pass
