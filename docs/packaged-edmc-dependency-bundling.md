# Packaged EDMC Dependency Bundling Plan

## Scope
- This document covers plugin runtime dependencies that must be available when EDMC is run from a packaged build.
- Development-only dependencies (for tests/linting) are out of scope here.

## Runtime Dependency Matrix
- Windows (`windows-registerhotkey` backend):
  - No third-party runtime dependency required (stdlib `ctypes` only).
- Linux X11 (`linux-x11` backend):
  - Requires `python-xlib` (`Xlib` package).
  - Imported dynamically via `Xlib.X`, `Xlib.XK`, and `Xlib.display`.
- Linux Wayland (`linux-wayland-portal` backend):
  - Requires `dbus-next` (`dbus_next` package) for portal runtime integration.
  - Uses XDG Desktop Portal `GlobalShortcuts`; backend remains non-fatal if prerequisites are missing.

## Bundling Strategy For Packaged EDMC
1. Create/update a plugin-local virtual environment and install runtime dependencies there.
2. Copy required runtime packages from `.venv` site-packages into the plugin directory.
3. Keep vendored content minimal: only copy packages used by runtime backend imports.

For Linux X11, use the vendoring script from the plugin root:

```bash
./scripts/vendor_xlib.sh
```

To force the exact EDMC interpreter:

```bash
EDMC_PYTHON="$HOME/apps/EDMarketConnector/venv/bin/python3" ./scripts/vendor_xlib.sh
```

The script:
- installs pinned `python-xlib` into a temp target directory.
- copies runtime modules into plugin root (`Xlib/`, `six.py`).
- writes `third_party_licenses/python-xlib.LICENSE` and `third_party_licenses/six.LICENSE` when available.
- verifies `import Xlib` and `import six` from plugin root.

For Linux Wayland (`dbus-next`), use:

```bash
./scripts/vendor_dbus_next.sh
```

To force the exact EDMC interpreter:

```bash
EDMC_PYTHON="$HOME/apps/EDMarketConnector/venv/bin/python3" ./scripts/vendor_dbus_next.sh
```

The script:
- installs pinned `dbus-next` into a temp target directory.
- copies runtime module into plugin root (`dbus_next/`).
- writes `third_party_licenses/dbus-next.LICENSE` when available.
- verifies `import dbus_next` from plugin root.

## Verification Checklist (Release)
- Launch packaged EDMC with plugin installed.
- Confirm plugin loads without import errors.
- Validate backend availability in debug logs:
  - X11 session: backend `linux-x11` should start when `Xlib` is present.
  - Wayland session: backend `linux-wayland-portal` should start when `WAYLAND_DISPLAY`, `xdg-desktop-portal`, and `dbus-next` are available; otherwise explicit unavailability reason should be logged.
- Open plugin settings and ensure no plugin prefs frame/type errors are logged.

## Maintenance Notes
- Re-run dependency copy whenever runtime dependency versions change.
- Keep this file updated when Wayland portal/runtime dependencies change.
