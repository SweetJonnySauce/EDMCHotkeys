#!/usr/bin/env bash
set -euo pipefail

TARGET_PATH="/etc/keyd/edmchotkeys.conf"
HELPER_TARGET="/usr/local/bin/edmchotkeys_send.py"
LEGACY_HELPER_TARGET="/etc/keyd/edmchotkeys_send.py"

usage() {
  cat <<'EOF'
Usage:
  scripts/uninstall_keyd_integration.sh [--apply]

Behavior:
  Prints the command to remove /etc/keyd/edmchotkeys.conf and keyd helper script(s), then restart keyd.
  If --apply is set, executes the command.
EOF
}

APPLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
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

REMOVE_CMD="sudo rm -f ${TARGET_PATH} ${HELPER_TARGET} ${LEGACY_HELPER_TARGET} && sudo systemctl restart keyd"
echo "Remove command:"
echo "${REMOVE_CMD}"

if [[ "${APPLY}" -eq 1 ]]; then
  eval "${REMOVE_CMD}"
  echo "keyd integration removed"
fi
