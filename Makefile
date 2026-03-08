PYTHON := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; elif command -v python >/dev/null 2>&1; then echo python; else echo python3; fi)
VERSION ?= v0.0.0-rc.1

.PHONY: check test compile lint typecheck docs-check companion-release-check vendor-xlib vendor-dbus-next install-gnome-companion uninstall-gnome-companion verify-gnome-companion package-gnome-companion release-build release-build-all release-build-linux-x11 release-build-linux-wayland release-build-linux-wayland-portal release-build-linux-wayland-gnome-bridge release-build-windows

check: lint typecheck docs-check test companion-release-check compile

test:
	$(PYTHON) -m pytest

compile:
	$(PYTHON) -m compileall load.py edmc_hotkeys tests

lint:
	$(PYTHON) scripts/check_no_print.py

typecheck:
	@echo "typecheck: no static type checker configured (skipped)"

docs-check:
	$(PYTHON) scripts/check_docs_links.py
	$(PYTHON) scripts/check_plugin_api_docs.py
	$(PYTHON) scripts/check_doc_snippets.py

companion-release-check:
	$(PYTHON) scripts/check_companion_release.py

vendor-xlib:
	./scripts/vendor_xlib.sh

vendor-dbus-next:
	./scripts/vendor_dbus_next.sh

install-gnome-companion:
	./scripts/install_gnome_bridge_companion.sh

uninstall-gnome-companion:
	./scripts/uninstall_gnome_bridge_companion.sh

verify-gnome-companion:
	./scripts/verify_gnome_bridge_companion.sh

package-gnome-companion:
	./scripts/package_gnome_bridge_companion.sh

release-build: release-build-all

release-build-all: release-build-linux-x11 release-build-linux-wayland release-build-linux-wayland-portal release-build-linux-wayland-gnome-bridge release-build-windows

release-build-linux-x11:
	$(PYTHON) scripts/build_release_artifact.py --variant linux-x11 --version $(VERSION)

release-build-linux-wayland:
	$(PYTHON) scripts/build_release_artifact.py --variant linux-wayland --version $(VERSION)

release-build-linux-wayland-portal:
	$(PYTHON) scripts/build_release_artifact.py --variant linux-wayland-portal --version $(VERSION)

release-build-linux-wayland-gnome-bridge:
	$(PYTHON) scripts/build_release_artifact.py --variant linux-wayland-gnome-bridge --version $(VERSION)

release-build-windows:
	$(PYTHON) scripts/build_release_artifact.py --variant windows --version $(VERSION)
