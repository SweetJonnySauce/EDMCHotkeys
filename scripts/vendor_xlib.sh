#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Vendor python-xlib into the EDMCHotkeys plugin directory.

Usage:
  scripts/vendor_xlib.sh [--python /path/to/python] [--version X.Y.Z]

Environment:
  EDMC_PYTHON            Optional Python interpreter to use for pip/install.
  PYTHON_XLIB_VERSION    Optional version (default: 0.33).
EOF
}

PYTHON_BIN="${EDMC_PYTHON:-}"
PYTHON_XLIB_VERSION="${PYTHON_XLIB_VERSION:-0.33}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --version)
      PYTHON_XLIB_VERSION="$2"
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
echo "Vendoring python-xlib==${PYTHON_XLIB_VERSION}"

"${PYTHON_BIN}" -m pip install --target "${TMP_DIR}" "python-xlib==${PYTHON_XLIB_VERSION}"

if [[ ! -d "${TMP_DIR}/Xlib" ]]; then
  echo "Install succeeded but Xlib package directory was not found." >&2
  exit 1
fi

# python-xlib requires `six`; vendor both runtime import targets.
rm -rf "${REPO_ROOT}/Xlib"
rm -f "${REPO_ROOT}/six.py"
cp -R "${TMP_DIR}/Xlib" "${REPO_ROOT}/Xlib"
if [[ -f "${TMP_DIR}/six.py" ]]; then
  cp "${TMP_DIR}/six.py" "${REPO_ROOT}/six.py"
else
  echo "Install succeeded but six.py was not found in target directory." >&2
  exit 1
fi

DIST_INFO_DIR="$(find "${TMP_DIR}" -maxdepth 1 -type d -name 'python_xlib-*.dist-info' | head -n 1 || true)"
if [[ -n "${DIST_INFO_DIR}" && -f "${DIST_INFO_DIR}/LICENSE" ]]; then
  mkdir -p "${REPO_ROOT}/third_party_licenses"
  cp "${DIST_INFO_DIR}/LICENSE" "${REPO_ROOT}/third_party_licenses/python-xlib.LICENSE"
fi
SIX_DIST_INFO_DIR="$(find "${TMP_DIR}" -maxdepth 1 -type d -name 'six-*.dist-info' | head -n 1 || true)"
if [[ -n "${SIX_DIST_INFO_DIR}" && -f "${SIX_DIST_INFO_DIR}/LICENSE" ]]; then
  mkdir -p "${REPO_ROOT}/third_party_licenses"
  cp "${SIX_DIST_INFO_DIR}/LICENSE" "${REPO_ROOT}/third_party_licenses/six.LICENSE"
fi

"${PYTHON_BIN}" - <<PY
import logging
import os
import sys
from pathlib import Path

repo = Path(r"${REPO_ROOT}")
sys.path.insert(0, str(repo))
import six
import Xlib
import Xlib.display
from edmc_hotkeys.backends.selector import select_backend

print(f"Vendored six import OK: {six.__file__}")
print(f"Vendored Xlib import OK: {Xlib.__file__}")

env = dict(os.environ)
platform_name = sys.platform
backend = select_backend(
    logger=logging.getLogger("edmc_hotkeys.vendor_xlib"),
    platform_name=platform_name,
    environ=env,
)
availability = backend.availability()
print(f"Backend availability check: name={backend.name} available={availability.available} reason={availability.reason}")

session = env.get("XDG_SESSION_TYPE", "").strip().lower()
is_linux_x11 = platform_name.startswith("linux") and (session == "x11" or bool(env.get("DISPLAY")))
if is_linux_x11 and (backend.name != "linux-x11" or not availability.available):
    raise SystemExit("Expected available linux-x11 backend in X11 session after vendoring")
PY

echo "Vendored runtime modules into ${REPO_ROOT}: Xlib/, six.py"
