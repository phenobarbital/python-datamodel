.. python-datamodel documentation master file, created by
   sphinx-quickstart on Fri Sep 16 07:35:11 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to python-datamodel's documentation!
============================================


.. image:: https://img.shields.io/pypi/v/python-datamodel
   :target: https://pypi.org/project/pythoon-datamodel/
   :alt: PyPI
.. image:: https://github.com/phenobarbital/python-datamodel/workflows/CI/badge.svg
   :target: https://github.com/phenobarbital/python-datamodel/actions?query=workflow%3ACI
   :alt: GitHub Actions - CI
.. image:: https://github.com/phenobarbital/python-datamodel/workflows/pre-commit/badge.svg
   :target: https://github.com/phenobarbital/python-datamodel/actions?query=workflow%3Apre-commit
   :alt: GitHub Actions - pre-commit
.. image:: https://img.shields.io/codecov/c/gh/phenobarbital/python-datamodel
   :target: https://app.codecov.io/gh/phenobarbital/python-datamodel
   :alt: Codecov

DataModel
---------

DataModel is a simple library based on python +3.7 to use Dataclass-syntax for interacting with
Data, using the same syntax of Dataclass, users can write Python Objects
and work with Data in the same way, is a reimplementation of python Dataclasses supporting true inheritance (without decorators), true composition and other good features.

The key features are:
* **Easy to use**: No more using decorators, concerns abour re-ordering attributes or common problems with using dataclasses with inheritance.



Requirements
------------

Python 3.7+



Installation
------------

.. code-block:: bash

   pip install python-datamodel



Usage
-----
.. code-block:: python
   
   >>> from datamodel import Field, BaseModel
   >>> @dataclass
   >>> class Point:
   >>>     x: int = Field(default=0, min=0, max=10)
   >>>     y: int = Field(default=0, min=0, max=10)
   >>>     c: float = Field(default=10, init=False)
   >>> a = Point(x=10, y=10)





License
-------

This project is licensed under the terms of the BSD v3. license.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api 

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
