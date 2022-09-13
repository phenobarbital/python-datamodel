#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""
from os import path
from setuptools import find_packages, setup


def get_path(filename):
    return path.join(path.dirname(path.abspath(__file__)), filename)


def readme():
    with open(get_path('README.md')) as readme:
        return readme.read()


with open(get_path('datamodel/version.py')) as meta:
    exec(meta.read())

setup(
    name="python-datamodel",
    version=__version__,
    python_requires=">=3.7.1",
    url="https://github.com/phenobarbital/python-datamodel",
    description=__description__,
    keywords=['asyncio', 'dataclass', 'dataclasses', 'data models'],
    platforms=['POSIX'],
    long_description=readme(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
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
    license=__license__,
    setup_requires=[
        "wheel==0.37.1",
        "Cython==0.29.32",
        "numpy==1.22.2",
        "asyncio==3.4.3",
        "cchardet==2.1.7",
        "cpython==0.0.6"
    ],
    install_requires=[
        "wheel==0.37.1",
        "cpython==0.0.6",
        "Cython==0.29.32",
        "numpy==1.23.3",
        "uvloop==0.16.0",
        "asyncio==3.4.3",
        "cchardet==2.1.7",
        "objectpath==0.6.1",
        "rapidjson==1.0.0",
        "python-rapidjson>=1.5",
        'typing_extensions==4.3.0',
        "asyncpg==0.26.0"
    ],
    tests_require=[
        'pytest>=6.0.0',
        'pytest-asyncio==0.19.0',
        'pytest-xdist==2.1.0',
        'pytest-assume==2.4.3'
    ],
    test_suite='tests',
    project_urls={  # Optional
        "Source": "https://github.com/phenobarbital/datamodels",
        "Funding": "https://paypal.me/phenobarbital",
        "Say Thanks!": "https://saythanks.io/to/phenobarbital",
    },
)
