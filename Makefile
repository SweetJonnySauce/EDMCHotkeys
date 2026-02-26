PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)

.PHONY: check test compile lint typecheck vendor-xlib

check: lint typecheck test compile

test:
	$(PYTHON) -m pytest

compile:
	$(PYTHON) -m compileall load.py edmc_hotkeys tests

lint:
	$(PYTHON) scripts/check_no_print.py

typecheck:
	@echo "typecheck: no static type checker configured (skipped)"

vendor-xlib:
	./scripts/vendor_xlib.sh
