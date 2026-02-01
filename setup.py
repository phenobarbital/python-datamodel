#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""


from Cython.Build import cythonize
from setuptools import Extension, setup
from setuptools_rust import RustExtension


COMPILE_ARGS = ["-O3"]
EXTRA_LINK_ARGS = ["-lstdc++"]

rust_extensions = [
    RustExtension(
        "datamodel.rs_parsers",
        path="datamodel/rs_parsers/Cargo.toml"
    ),
]

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

setup(
    ext_modules=cythonize(
        extensions,
        annotate=True
    ),
    zip_safe=False,
    rust_extensions=rust_extensions,
)
