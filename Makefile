.DEFAULT_GOAL := all

.PHONY: install
install:
	@which uv > /dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	uv sync --all-extras --python 3.12
	uv run pre-commit install -t pre-push

.PHONY: format
format:
	uv run ruff check --fix neatpush/ tests/
	uv run ruff format neatpush/ tests/

.PHONY: lint
lint:
	uv run ruff check neatpush/ tests/
	uv run ruff format --check neatpush/ tests/

.PHONY: mypy
mypy:
	uv run mypy neatpush --enable-incomplete-feature=NewGenericSyntax

.PHONY: test
test:
	uv pytest

.PHONY: all
all: lint mypy test

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '.*DS_Store'`
	rm -rf .cache
	rm -rf .*_cache
	rm -rf .ropeproject
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -rf .eggs
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf public
	rm -rf .hypothesis
	rm -rf .profiling
