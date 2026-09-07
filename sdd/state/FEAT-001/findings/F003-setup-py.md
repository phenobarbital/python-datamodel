---
id: F003
query_id: Q003
type: read
intent: Inspect Cython extension build flags for Windows/MSVC portability
executed_at: 2026-09-07T21:30:00Z
duration_ms: 250
parent_id: null
depth: 0
---

# F003 — setup.py hardcodes GCC-only flags (-O3, -lstdc++)

## Summary

Ten Cython extensions are declared. All use `COMPILE_ARGS = ["-O3"]`; the
three C++ extensions (`fields`, `functions`, `parsers.json`) additionally use
`EXTRA_LINK_ARGS = ["-lstdc++"]`. Both are GCC/Clang flags; MSVC will emit
warnings for `-O3` and fail on `-lstdc++`. This is the primary blocker for
Windows wheels of the Cython layer. No platform conditional exists.

## Citations

- path: `setup.py`
  lines: 12-13
  symbol: `COMPILE_ARGS`, `EXTRA_LINK_ARGS`
  excerpt: |
    COMPILE_ARGS = ["-O3"]
    EXTRA_LINK_ARGS = ["-lstdc++"]

- path: `setup.py`
  lines: 15-22
  symbol: `Extension('datamodel.fields')`
  excerpt: |
    Extension(
        name='datamodel.fields',
        sources=['datamodel/fields.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),

- path: `setup.py`
  lines: 36-42
  symbol: `Extension('datamodel.functions')`
  excerpt: |
    extra_link_args=EXTRA_LINK_ARGS,
    language="c++"

- path: `setup.py`
  lines: 60-66
  symbol: `Extension('datamodel.parsers.json')`
  excerpt: |
    extra_link_args=EXTRA_LINK_ARGS,
    language="c++"

- path: `setup.py`
  lines: 96-102
  symbol: `setup()`
  excerpt: |
    setup(
        ext_modules=cythonize(extensions, annotate=True),
        package_data={
            "datamodel.rs_parsers": ["*.so", "*.pyd"],
        },
        zip_safe=False,
    )
