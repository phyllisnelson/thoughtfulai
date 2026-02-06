.PHONY: help install install-dev test coverage lint format typecheck clean run

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install package
	pip install -e .

install-dev:  ## Install package with dev dependencies
	pip install -e ".[dev]"
	pre-commit install

test:  ## Run tests
	pytest

coverage:  ## Run tests with coverage report
	pytest --cov=my_solution --cov=routing_cycle_detector --cov-report=term-missing

lint:  ## Run all linters
	pre-commit run --all-files

format:  ## Format code with black and isort
	black .
	isort .

typecheck:  ## Run mypy type checker
	mypy my_solution.py

clean:  ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +

run:  ## Run with example: make run FILE=large_input_v1.txt
	python3 my_solution.py $(FILE)
