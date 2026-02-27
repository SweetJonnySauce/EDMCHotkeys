#!/usr/bin/env bash
set -euo pipefail

EXT_UUID="edmc-hotkeys@edcd"
XDG_DATA_HOME_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}"
XDG_CONFIG_HOME_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}"
DEFAULT_DATA_HOME_DIR="${HOME}/.local/share"
CONFIG_FILE="${XDG_CONFIG_HOME_DIR}/edmc-hotkeys/companion-bindings.json"

DISABLE_EXTENSION=1
REMOVE_CONFIG=0

usage() {
  cat <<'EOF'
Uninstall GNOME bridge companion extension and helper.

Usage:
  scripts/uninstall_gnome_bridge_companion.sh [--keep-enabled] [--remove-config]

Options:
  --keep-enabled   Skip gnome-extensions disable call.
  --remove-config  Delete companion bindings config file.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-enabled)
      DISABLE_EXTENSION=0
      shift
      ;;
    --remove-config)
      REMOVE_CONFIG=1
      shift
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

if [[ "${DISABLE_EXTENSION}" -eq 1 ]] \
  && command -v gnome-extensions >/dev/null 2>&1 \
  && [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
  gnome-extensions disable "${EXT_UUID}" || true
fi

declare -a data_homes
data_homes=("${DEFAULT_DATA_HOME_DIR}")
if [[ "${XDG_DATA_HOME_DIR}" != "${DEFAULT_DATA_HOME_DIR}" ]]; then
  data_homes+=("${XDG_DATA_HOME_DIR}")
fi

for data_home in "${data_homes[@]}"; do
  target_ext_dir="${data_home}/gnome-shell/extensions/${EXT_UUID}"
  if [[ -d "${target_ext_dir}" ]]; then
    if ! rm -rf "${target_ext_dir}" 2>/dev/null; then
      echo "Warning: unable to remove extension directory: ${target_ext_dir}" >&2
    fi
  fi
done

if [[ "${REMOVE_CONFIG}" -eq 1 ]] && [[ -f "${CONFIG_FILE}" ]]; then
  rm -f "${CONFIG_FILE}"
fi

cat <<EOF
Removed GNOME companion extension:
  ${DEFAULT_DATA_HOME_DIR}/gnome-shell/extensions/${EXT_UUID}
  ${XDG_DATA_HOME_DIR}/gnome-shell/extensions/${EXT_UUID}

Config retained:
  ${CONFIG_FILE}
EOF
