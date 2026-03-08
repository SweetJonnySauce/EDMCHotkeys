#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="${REPO_ROOT}"
BINDINGS_FILE="${PLUGIN_DIR}/bindings.json"
INSTALL=0
APPLY=0

usage() {
  cat <<'EOF'
Usage:
  scripts/install_keyd_integration.sh [--plugin-dir PATH] [--bindings PATH] [--install] [--apply]

Behavior:
  1) Exports keyd bindings into keyd/runtime/keyd.generated.conf
  2) Prints install/apply commands
  3) If --install is set, installs /usr/local/bin/edmchotkeys_send.py
  4) If --apply is set, installs /etc/keyd/edmchotkeys.conf and restarts keyd
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-dir)
      PLUGIN_DIR="$2"
      shift 2
      ;;
    --bindings)
      BINDINGS_FILE="$2"
      shift 2
      ;;
    --install)
      INSTALL=1
      shift
      ;;
    --apply)
      APPLY=1
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

python3 "${PLUGIN_DIR}/scripts/export_keyd_bindings.py" \
  --plugin-dir "${PLUGIN_DIR}" \
  --bindings "${BINDINGS_FILE}"

GENERATED_PATH="${PLUGIN_DIR}/keyd/runtime/keyd.generated.conf"
TARGET_PATH="/etc/keyd/edmchotkeys.conf"
HELPER_SOURCE="${PLUGIN_DIR}/scripts/keyd_send.py"
HELPER_TARGET="/usr/local/bin/edmchotkeys_send.py"
INSTALL_CMD="sudo install -m 0755 ${HELPER_SOURCE} ${HELPER_TARGET}"
APPLY_CMD="sudo install -m 0644 ${GENERATED_PATH} ${TARGET_PATH} && sudo systemctl restart keyd"

echo "Install command:"
echo "${INSTALL_CMD}"
echo "Apply command:"
echo "${APPLY_CMD}"

if [[ "${INSTALL}" -eq 1 ]]; then
  eval "${INSTALL_CMD}"
  echo "keyd helper installed"
fi

if [[ "${APPLY}" -eq 1 ]]; then
  eval "${APPLY_CMD}"
  echo "keyd config applied"
fi
