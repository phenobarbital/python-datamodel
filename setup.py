#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""

import sys

from Cython.Build import cythonize
from setuptools import Extension, setup


def _compiler_flags() -> tuple[list[str], list[str]]:
    """Select platform-appropriate compile/link flags.

    MSVC (Windows) rejects the GCC-style `-O3` / `-lstdc++` flags used on
    POSIX platforms, so this returns `/O2` with no extra link args on
    `win32`, and the existing `-O3` / `-lstdc++` pair everywhere else.
    """
    if sys.platform == "win32":
        return ["/O2"], []
    return ["-O3"], ["-lstdc++"]


COMPILE_ARGS, EXTRA_LINK_ARGS = _compiler_flags()

extensions = [
    Extension(
        name='datamodel.fields',
        sources=['datamodel/fields.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.converters',
        sources=['datamodel/converters.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c",
    ),
    Extension(
        name='datamodel.validation',
        sources=['datamodel/validation.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.functions',
        sources=['datamodel/functions.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.exceptions',
        sources=['datamodel/exceptions.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.types',
        sources=['datamodel/types.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.parsers.json',
        sources=['datamodel/parsers/json.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.libs.mapping',
        sources=['datamodel/libs/mapping.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.typedefs.singleton',
        sources=['datamodel/typedefs/singleton.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.typedefs.types',
        sources=['datamodel/typedefs/types.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
]

if __name__ == "__main__":
    # Guarded so `import setup` (used by tests/test_setup_flags.py to exercise
    # `_compiler_flags()` for both platforms) does not trigger a build.
    setup(
        ext_modules=cythonize(extensions, annotate=True),
        package_data={
            "datamodel.rs_parsers": ["*.so", "*.pyd"],
        },
        zip_safe=False,
    )
