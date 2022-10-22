.DEFAULT_GOAL := all
isort = isort --gitignore neatpush tests
black = black neatpush tests

.PHONY: install
install:
	pip install -U pip
	pip install -e .[qa,test]
	pre-commit install -t pre-push

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	flake8 neatpush/ tests/
	$(isort) --check-only --df
	$(black) --check

.PHONY: mypy
mypy:
	mypy neatpush

.PHONY: codegen
codegen:
	edgedb-py --file
	mv generated_async_edgeql.py neatpush/queries.py

.PHONY: watch-codegen
watch-codegen:
	watchfiles "make codegen" neatpush/queries/

.PHONY: test
test:
	pytest

.PHONY: all
all: lint mypy test

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
