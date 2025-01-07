# Aliases Functions:
import re

_RE_FIRST_CAP = re.compile(r"(.)([A-Z][a-z]+)")
_RE_ALL_CAPS = re.compile(r"([a-z0-9])([A-Z])")


def to_snakecase(name: str) -> str:
    """
    Convert a CamelCase or PascalCase string into snake_case.
    Example: "EmailAddress" -> "email_address"
    """
    import re
    # Insert underscores before capital letters, then lower-case
    s1 = _RE_FIRST_CAP.sub(r"\1_\2", name)
    return _RE_ALL_CAPS.sub(r"\1_\2", s1).lower()
