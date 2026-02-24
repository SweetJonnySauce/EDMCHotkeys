PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)

.PHONY: check test compile lint typecheck vendor-xlib

check: lint typecheck test compile

test:
	$(PYTHON) -m pytest

compile:
	$(PYTHON) -m compileall load.py edmc_hotkeys tests

lint:
	@echo "lint: no linter configured"

typecheck:
	@echo "typecheck: no type checker configured"

vendor-xlib:
	./scripts/vendor_xlib.sh
