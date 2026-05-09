PYTHON ?= python
NPX ?= npx

.PHONY: all format lint test coverage run

all: format lint test

format:
	$(PYTHON) -m ruff format .
	$(NPX) prettier . --write

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m unittest discover -s tests -t .

coverage:
	$(PYTHON) -m coverage erase
	$(PYTHON) -m coverage run -m unittest discover -s tests -t .
	$(PYTHON) -m coverage report --include='main.py,game/*.py'
	$(PYTHON) tests/check_coverage_threshold.py --threshold 80 main.py game/*.py

run:
	$(PYTHON) main.py