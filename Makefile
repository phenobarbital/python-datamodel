venv:
	python3.11 -m venv .venv
	echo 'run `source .venv/bin/activate` to start develop DataModel'

venv12:
	python3.12 -m venv .venv11
	echo 'run `source .venv/bin/activate` to start develop DataModel'

install:
	pip install -e .

develop:
	pip install -e .
	pip install -Ur docs/requirements-dev.txt

compile:
	python setup.py build_ext --inplace

release:
	lint test clean
	flit publish

format:
	python -m black datamodel

lint:
	python -m pylint --rcfile .pylintrc datamodels/*.py
	python -m pylint --rcfile .pylintrc datamodels/models/*.py
	python -m black --check datamodels

test:
	python -m coverage run -m datamodels.tests
	python -m coverage report
	python -m mypy datamodels/*.py

distclean:
	rm -rf .venv
