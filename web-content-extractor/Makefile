# Makefile for Web Content Extraction Tool

# Variables
PYTHON := python3
VENV := venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PLAYWRIGHT := $(BIN)/playwright
PY := $(BIN)/python
OUTPUT_DIR := output
DEFAULT_URL := https://x.com/koylanai/status/2025286163641118915

.PHONY: help install run test clean lint

help:
	@echo "Available commands:"
	@echo "  make install         - Create virtual environment and install dependencies"
	@echo "  make run URL=...     - Run the tool (default URL provided)"
	@echo "  make test            - Run unit tests"
	@echo "  make clean           - Remove output directory and temporary files"
	@echo "  make lint            - Run code linting (optional)"

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PLAYWRIGHT) install chromium

run:
	@mkdir -p $(OUTPUT_DIR)
	$(PY) main.py $(if $(URL),$(URL),$(DEFAULT_URL)) --output $(OUTPUT_DIR) --debug

test:
	$(PY) -m unittest discover tests

clean:
	rm -rf $(OUTPUT_DIR)
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	# Check if pylint is installed, if not, install it temporarily or skip
	$(PIP) install pylint
	$(BIN)/pylint src main.py
