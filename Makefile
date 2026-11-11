.PHONY: install test lint run clean help

install:
	uv sync

test:
	uv run pytest -q

test-cov:
	uv run pytest --cov=summa --cov-report=term-missing

lint:
	uv run python -m compileall src

run:
	uv run summa --help

clean:
	rm -rf .venv .pytest_cache .coverage htmlcov
	rm -f ~/.summa/summa.db

help:
	@echo "Available targets:"
	@echo "  install   - install dependencies"
	@echo "  test      - run tests"
	@echo "  test-cov  - run tests with coverage"
	@echo "  lint      - compile check"
	@echo "  run       - show CLI help"
	@echo "  clean     - remove artifacts"
