#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

EXT_UUID="edmc-hotkeys@edcd"
XDG_DATA_HOME_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}"
XDG_CONFIG_HOME_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}"
DEFAULT_DATA_HOME_DIR="${HOME}/.local/share"
SOURCE_EXT_DIR="${REPO_ROOT}/companion/gnome-extension/${EXT_UUID}"
SOURCE_HELPER="${REPO_ROOT}/companion/helper/gnome_bridge_companion_send.py"
CONFIG_DIR="${XDG_CONFIG_HOME_DIR}/edmc-hotkeys"
CONFIG_FILE="${CONFIG_DIR}/companion-bindings.json"
SAMPLE_CONFIG="${SOURCE_EXT_DIR}/bindings.sample.json"
SOURCE_BINDINGS="${REPO_ROOT}/bindings.json"

ENABLE_EXTENSION=0

usage() {
  cat <<'EOF'
Install GNOME bridge companion extension and helper.

Usage:
  scripts/install_gnome_bridge_companion.sh [--enable]

Options:
  --enable   Enable extension after install (uses gnome-extensions if available).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable)
      ENABLE_EXTENSION=1
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

if [[ ! -d "${SOURCE_EXT_DIR}" ]]; then
  echo "Missing source extension directory: ${SOURCE_EXT_DIR}" >&2
  exit 1
fi
if [[ ! -f "${SOURCE_HELPER}" ]]; then
  echo "Missing helper sender: ${SOURCE_HELPER}" >&2
  exit 1
fi

declare -a data_homes
data_homes=("${DEFAULT_DATA_HOME_DIR}")
if [[ "${XDG_DATA_HOME_DIR}" != "${DEFAULT_DATA_HOME_DIR}" ]]; then
  data_homes+=("${XDG_DATA_HOME_DIR}")
fi

declare -a installed_dirs
for data_home in "${data_homes[@]}"; do
  target_ext_dir="${data_home}/gnome-shell/extensions/${EXT_UUID}"
  if ! mkdir -p "${target_ext_dir}" 2>/dev/null; then
    echo "Warning: unable to create extension directory, skipping: ${target_ext_dir}" >&2
    continue
  fi
  if ! cp "${SOURCE_EXT_DIR}/metadata.json" "${target_ext_dir}/metadata.json" 2>/dev/null; then
    echo "Warning: unable to copy extension files, skipping: ${target_ext_dir}" >&2
    continue
  fi
  cp "${SOURCE_EXT_DIR}/extension.js" "${target_ext_dir}/extension.js"
  cp "${SOURCE_EXT_DIR}/helper_bridge.js" "${target_ext_dir}/helper_bridge.js"
  cp "${SOURCE_EXT_DIR}/bindings.sample.json" "${target_ext_dir}/bindings.sample.json"
  mkdir -p "${target_ext_dir}/helper"
  cp "${SOURCE_HELPER}" "${target_ext_dir}/helper/gnome_bridge_companion_send.py"
  chmod +x "${target_ext_dir}/helper/gnome_bridge_companion_send.py"
  installed_dirs+=("${target_ext_dir}")
done

if [[ "${#installed_dirs[@]}" -eq 0 ]]; then
  echo "Failed to install extension to any target directory." >&2
  exit 1
fi

mkdir -p "${CONFIG_DIR}"
if [[ -f "${SOURCE_BINDINGS}" ]]; then
  if ! "${REPO_ROOT}/scripts/export_companion_bindings.py" \
    --bindings "${SOURCE_BINDINGS}" \
    --output "${CONFIG_FILE}"; then
    if [[ ! -f "${CONFIG_FILE}" ]]; then
      cp "${SAMPLE_CONFIG}" "${CONFIG_FILE}"
    fi
  fi
elif [[ ! -f "${CONFIG_FILE}" ]]; then
  cp "${SAMPLE_CONFIG}" "${CONFIG_FILE}"
fi

if [[ "${ENABLE_EXTENSION}" -eq 1 ]]; then
  if command -v gnome-extensions >/dev/null 2>&1; then
    gnome-extensions enable "${EXT_UUID}" || true
  else
    echo "gnome-extensions command not found; extension was installed but not enabled." >&2
  fi
fi

cat <<EOF
Installed GNOME companion extension:
$(printf '  %s\n' "${installed_dirs[@]}")

Runtime binding config:
  ${CONFIG_FILE}

Next:
  1) Ensure EDMC is running with:
     EDMC_HOTKEYS_BACKEND_MODE=wayland_gnome_bridge
     EDMC_HOTKEYS_GNOME_BRIDGE=1
  2) Update ${CONFIG_FILE} with desired accelerators/binding ids.
  3) Enable extension:
     gnome-extensions enable ${EXT_UUID}
EOF
