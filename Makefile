VENV := .venv
BIN  := $(VENV)/bin

.PHONY: start install lint test

start:
	$(BIN)/ds4-mapper

install:
	python3 -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"

lint:
	$(BIN)/ruff format . && $(BIN)/ruff check .

test:
	$(BIN)/pytest tests/ -v
