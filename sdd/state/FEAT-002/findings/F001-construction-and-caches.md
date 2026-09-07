---
id: F001
query_id: Q001
type: read
executed_at: 2026-09-08
depth: 0
---

# Construction and cache boundaries

## Summary

The metaclass already caches reflection, parsers, validators and type categories. Construction still remaps keyword arguments, enters a generated dataclass initializer, calls Python assignment bookkeeping for every field, materializes column items and runs the converter pipeline. Caching more annotation reflection alone cannot remove all this work.

## Citations

- `datamodel/abstract.py:66`, `_dc_method_setattr_`: list membership in `__fields__`, `__values__.setdefault`, optional assignment conversion and descriptor-respecting assignment.
- `datamodel/abstract.py:158`, `ModelMeta._base_class_cache`: bounded OrderedDict cache, maximum 512 entries.
- `datamodel/abstract.py:229`, `_initialize_fields`: caches origin, arguments, primitive/dataclass flags, parser and validator.
- `datamodel/abstract.py:358`, `ModelMeta.__new__`: key uses name, bases and sorted annotations; defaults, metadata and Meta settings are absent; cached dictionaries are shallow copies.
- `datamodel/abstract.py:460`, dataclass decoration and subsequent attributes: initializes `__columns__`, list-valued `__fields__`, class-level `__values__`, and overrides assignment.
- `datamodel/abstract.py:516`, `ModelMeta.__call__`: alias function and alias mapping before construction.
- `datamodel/base.py:35`, `BaseModel.__post_init__`: `columns = list(self.__columns__.items())`; calls `processing_fields`; strict and non-strict error handling.
- `datamodel/base.py:59`, `register_parser`, `add_field`, `create_field`, `set`: runtime extension surface.
- `datamodel/fields.pyx:81`, `Field`: Python class extending dataclasses.Field, despite residing in a Cython file.

## Implications

A proposed execution cache should belong to the actual class and account for field/configuration/parser changes and inheritance. Reusing this existing cache key for an execution plan risks conflating different model definitions. Direct metadata mutation and existing shared state need characterization; changing their semantics is a separate correctness decision, not an incidental optimization.
