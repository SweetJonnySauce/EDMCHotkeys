#!/usr/bin/env bash
set -euo pipefail

EXT_UUID="edmc-hotkeys@edcd"
XDG_DATA_HOME_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}"
XDG_CONFIG_HOME_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}"
DEFAULT_DATA_HOME_DIR="${HOME}/.local/share"
CONFIG_FILE="${XDG_CONFIG_HOME_DIR}/edmc-hotkeys/companion-bindings.json"

fail() {
  echo "verify: FAIL - $*" >&2
  exit 1
}

declare -a ext_dirs
ext_dirs=("${DEFAULT_DATA_HOME_DIR}/gnome-shell/extensions/${EXT_UUID}")
if [[ "${XDG_DATA_HOME_DIR}" != "${DEFAULT_DATA_HOME_DIR}" ]]; then
  ext_dirs+=("${XDG_DATA_HOME_DIR}/gnome-shell/extensions/${EXT_UUID}")
fi

found_ext_dir=""
for ext_dir in "${ext_dirs[@]}"; do
  if [[ -d "${ext_dir}" ]]; then
    found_ext_dir="${ext_dir}"
    break
  fi
done
[[ -n "${found_ext_dir}" ]] || fail "extension directory missing in expected locations: ${ext_dirs[*]}"
[[ -f "${found_ext_dir}/metadata.json" ]] || fail "metadata.json missing"
[[ -f "${found_ext_dir}/extension.js" ]] || fail "extension.js missing"
[[ -f "${found_ext_dir}/helper_bridge.js" ]] || fail "helper_bridge.js missing"
[[ -x "${found_ext_dir}/helper/gnome_bridge_companion_send.py" ]] || fail "helper sender missing or not executable"
[[ -f "${CONFIG_FILE}" ]] || fail "companion bindings config missing: ${CONFIG_FILE}"

python3 - "${found_ext_dir}/metadata.json" "${CONFIG_FILE}" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
config_path = Path(sys.argv[2])
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
if metadata.get("uuid") != "edmc-hotkeys@edcd":
    raise SystemExit("invalid metadata uuid")
shell_versions = metadata.get("shell-version")
if not isinstance(shell_versions, list) or not shell_versions:
    raise SystemExit("metadata shell-version list missing")

config = json.loads(config_path.read_text(encoding="utf-8"))
bindings = config.get("bindings")
if not isinstance(bindings, list):
    raise SystemExit("companion bindings config missing bindings array")
PY

if command -v gnome-extensions >/dev/null 2>&1; then
  if gnome-extensions info "${EXT_UUID}" >/dev/null 2>&1; then
    state="$(
      gnome-extensions info "${EXT_UUID}" \
        | sed -n 's/^[[:space:]]*State:[[:space:]]*//p' \
        | head -n 1
    )"
    if [[ -n "${state}" ]]; then
      echo "verify: extension state=${state}"
    else
      echo "verify: extension registered (state not parsed)"
    fi
  else
    echo "verify: extension not registered in gnome-extensions yet"
  fi
else
  echo "verify: gnome-extensions command unavailable; skipped state check"
fi

echo "verify: OK"
