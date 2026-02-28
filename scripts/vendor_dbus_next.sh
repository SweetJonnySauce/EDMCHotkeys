#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Vendor dbus-next into the EDMCHotkeys plugin directory.

Usage:
  scripts/vendor_dbus_next.sh [--python /path/to/python] [--version X.Y.Z]

Environment:
  EDMC_PYTHON         Optional Python interpreter to use for pip/install.
  DBUS_NEXT_VERSION   Optional version (default: 0.2.3).
EOF
}

PYTHON_BIN="${EDMC_PYTHON:-}"
DBUS_NEXT_VERSION="${DBUS_NEXT_VERSION:-0.2.3}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --version)
      DBUS_NEXT_VERSION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "${HOME}/apps/EDMarketConnector/venv/bin/python3" ]]; then
    PYTHON_BIN="${HOME}/apps/EDMarketConnector/venv/bin/python3"
  elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "No Python interpreter found. Set EDMC_PYTHON or pass --python." >&2
    exit 1
  fi
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python interpreter is not executable: ${PYTHON_BIN}" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

echo "Using Python: ${PYTHON_BIN}"
echo "Vendoring dbus-next==${DBUS_NEXT_VERSION}"

"${PYTHON_BIN}" -m pip install --target "${TMP_DIR}" "dbus-next==${DBUS_NEXT_VERSION}"

if [[ ! -d "${TMP_DIR}/dbus_next" ]]; then
  echo "Install succeeded but dbus_next package directory was not found." >&2
  exit 1
fi

rm -rf "${REPO_ROOT}/dbus_next"
cp -R "${TMP_DIR}/dbus_next" "${REPO_ROOT}/dbus_next"

DIST_INFO_DIR="$(find "${TMP_DIR}" -maxdepth 1 -type d -name 'dbus_next-*.dist-info' | head -n 1 || true)"
if [[ -n "${DIST_INFO_DIR}" ]]; then
  LICENSE_SRC=""
  for candidate in LICENSE LICENSE.txt COPYING COPYING.txt; do
    if [[ -f "${DIST_INFO_DIR}/${candidate}" ]]; then
      LICENSE_SRC="${DIST_INFO_DIR}/${candidate}"
      break
    fi
  done
  if [[ -n "${LICENSE_SRC}" ]]; then
    mkdir -p "${REPO_ROOT}/third_party_licenses"
    cp "${LICENSE_SRC}" "${REPO_ROOT}/third_party_licenses/dbus-next.LICENSE"
  fi
fi

"${PYTHON_BIN}" - <<PY
import logging
import os
import sys
from pathlib import Path

repo = Path(r"${REPO_ROOT}")
sys.path.insert(0, str(repo))
import dbus_next
from edmc_hotkeys.backends.selector import select_backend

print(f"Vendored dbus_next import OK: {dbus_next.__file__}")

env = dict(os.environ)
platform_name = sys.platform
backend = select_backend(
    logger=logging.getLogger("edmc_hotkeys.vendor_dbus_next"),
    platform_name=platform_name,
    environ=env,
)
availability = backend.availability()
print(f"Backend availability check: name={backend.name} available={availability.available} reason={availability.reason}")

session = env.get("XDG_SESSION_TYPE", "").strip().lower()
is_linux_wayland = platform_name.startswith("linux") and (session == "wayland" or bool(env.get("WAYLAND_DISPLAY")))
if is_linux_wayland:
    if backend.name != "linux-wayland-portal":
        raise SystemExit("Expected linux-wayland-portal backend in Wayland session")
    reason = availability.reason or ""
    if "dbus-next is unavailable" in reason:
        raise SystemExit("dbus-next still reported unavailable after vendoring")
PY

echo "Vendored runtime module into ${REPO_ROOT}: dbus_next/"
