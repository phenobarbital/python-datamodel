#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""
import ast
from os import path

from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup, find_namespace_packages
from setuptools_rust import RustExtension


def get_path(filename):
    return path.join(path.dirname(path.abspath(__file__)), filename)


def readme():
    with open(get_path('README.md'), encoding='utf-8') as rd:
        return rd.read()


version = get_path('datamodel/version.py')
with open(version, 'r', encoding='utf-8') as meta:
    t = compile(meta.read(), version, 'exec', ast.PyCF_ONLY_AST)
    for node in (n for n in t.body if isinstance(n, ast.Assign)):
        if len(node.targets) == 1:
            name = node.targets[0]
            if isinstance(name, ast.Name) and \
                    name.id in (
                        '__version__',
                        '__title__',
                        '__description__',
                        '__author__',
                        '__license__', '__author_email__'):
                v = node.value
                if name.id == '__version__':
                    __version__ = v.s
                if name.id == '__title__':
                    __title__ = v.s
                if name.id == '__description__':
                    __description__ = v.s
                if name.id == '__license__':
                    __license__ = v.s
                if name.id == '__author__':
                    __author__ = v.s
                if name.id == '__author_email__':
                    __author_email__ = v.s


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
        name='datamodel.functions',
        sources=['datamodel/functions.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.validation',
        sources=['datamodel/validation.pyx'],
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
    name="python-datamodel",
    version=__version__,
    python_requires=">=3.10.0",
    url="https://github.com/phenobarbital/python-datamodel",
    description=__description__,
    keywords=['asyncio', 'dataclass', 'dataclasses', 'data models'],
    platforms=['any'],
    long_description=readme(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Environment :: Web Environment",
    ],
    author=__author__,
    author_email=__author_email__,
    packages=find_namespace_packages(exclude=["contrib", "docs", "tests", "examples"]),
    include_package_data=True,
    package_data={
        "datamodel.fields": ["*.pyx"],
        "datamodel.converters": ["*.pyx"],
        "datamodel.validation": ["*.pyx"],
        "datamodel.exceptions": ["*.pxd", "*.pyx"],
        "datamodel.functions": ["*.pxd", "*.pyx"],
        "datamodel.libs.mapping": ["*.pxd", "*.pyx"],
        "datamodel.typedefs.singleton": ["*.pxd", "*.pyx"],
        "datamodel.typedefs.types": ["*.pxd", "*.pyx"],
        "datamodel.parsers.json": ["*.pyx"],
    },
    license=__license__,
    setup_requires=[
        'setuptools==74.0.0',
        'Cython==3.0.11',
        'wheel==0.44.0',
        'pip>=24.3.1,<26.0',
        'setuptools-rust==1.10.2',
    ],
    install_requires=[
        "numpy>=1.26.4",
        "uvloop>=0.21.0",
        "asyncio==3.4.3",
        "faust-cchardet==2.1.19",
        "ciso8601==2.3.2",
        "objectpath==0.6.1",
        "orjson>=3.10.11",
        'typing_extensions>=4.9.0',
        "asyncpg>=0.29.0",
        "python-dateutil>=2.8.2",
        "python-slugify==8.0.1",
        "psycopg2-binary==2.9.10",
        "msgspec==0.19.0"
    ],
    ext_modules=cythonize(
        extensions,
        annotate=True
    ),
    zip_safe=False,
    rust_extensions=rust_extensions,
    project_urls={  # Optional
        "Source": "https://github.com/phenobarbital/datamodel",
        "Funding": "https://paypal.me/phenobarbital",
        "Tracker": "https://github.com/phenobarbital/datamodel/issues",
        "Documentation": "https://datamodel.readthedocs.io/en/latest/",
        "Buy Me A Coffee!": "https://www.buymeacoffee.com/phenobarbital",
        "Say Thanks!": "https://saythanks.io/to/phenobarbital",
    },
)
