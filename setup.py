#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""
from os import path
from setuptools import find_packages, setup, Extension
from Cython.Build import cythonize


def get_path(filename):
    return path.join(path.dirname(path.abspath(__file__)), filename)


def readme():
    with open(get_path('README.md'), encoding='utf-8') as rd:
        return rd.read()


with open(get_path('datamodel/version.py'), encoding='utf-8') as meta:
    exec(meta.read())

COMPILE_ARGS = ["-O2"]

extensions = [
    Extension(
        name='datamodel.fields',
        sources=['datamodel/fields.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.converters',
        sources=['datamodel/converters.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.validation',
        sources=['datamodel/validation.pyx'],
        extra_compile_args=COMPILE_ARGS,
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
    )
]

setup(
    name="python-datamodel",
    version=__version__,
    python_requires=">=3.8.1",
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Environment :: Web Environment",
    ],
    author=__author__,
    author_email=__author_email__,
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    include_package_data=True,
    license=__license__,
    setup_requires=[
        "setuptools==65.3.0",
        "wheel==0.37.1",
        "Cython==0.29.32",
        "asyncio==3.4.3",
        "cchardet==2.1.7"
    ],
    install_requires=[
        "wheel==0.37.1",
        "Cython==0.29.32",
        "numpy==1.23.3",
        "uvloop==0.17.0",
        "asyncio==3.4.3",
        "cchardet==2.1.7",
        "objectpath==0.6.1",
        "orjson==3.8.0",
        'typing_extensions==4.3.0',
        "asyncpg==0.26.0",
        "python-dateutil==2.8.2"
    ],
    tests_require=[
        'pytest>=6.0.0',
        'pytest-asyncio==0.19.0',
        'pytest-xdist==2.1.0',
        'pytest-assume==2.4.3'
    ],
    test_suite='tests',
    ext_modules=cythonize(extensions),
    project_urls={  # Optional
        "Source": "https://github.com/phenobarbital/datamodels",
        "Funding": "https://paypal.me/phenobarbital",
        "Say Thanks!": "https://saythanks.io/to/phenobarbital",
    },
)
