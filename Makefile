venv:
	python3.9 -m venv .venv
	echo 'run `source .venv/bin/activate` to start develop DataModel'

venv10:
	python3.10 -m venv .venv10
	echo 'run `source .venv/bin/activate` to start develop DataModel'

setup:
	pip install wheel==0.38.4
	pip install -e .

develop:
	pip install wheel==0.38.4
	pip install -e .
	flit install --symlink

release:
	lint test clean
	flit publish

format:
	python -m black asyncdb

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
