.PHONY: install dev doctor test lint swift-test clean

install:
	python3.13 -m venv .venv
	.venv/bin/python -m pip install -U pip
	.venv/bin/python -m pip install -e .

dev:
	python3.13 -m venv .venv
	.venv/bin/python -m pip install -U pip
	.venv/bin/python -m pip install -e '.[dev]'

doctor:
	.venv/bin/atot doctor

test:
	.venv/bin/python -m pytest

swift-test:
	cd app && swift test --scratch-path ../build/swiftpm

lint:
	.venv/bin/python -m ruff check .
	.venv/bin/python src/scripts/check_public_paths.py
	.venv/bin/python src/scripts/validate_model_inventory.py

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache app/.build
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
