#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GENERATED_PATH="${PLUGIN_DIR}/keyd/runtime/keyd.generated.conf"
STATE_PATH="${PLUGIN_DIR}/keyd/runtime/export_state.json"
TARGET_PATH="/etc/keyd/edmchotkeys.conf"
HELPER_TARGET="/usr/local/bin/edmchotkeys_send.py"

read_socket_path() {
  local path=""
  if [[ -f "${PLUGIN_DIR}/config.ini" ]]; then
    path="$(awk -F '=' '/^[[:space:]]*socket_path[[:space:]]*=/{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$2); print $2; exit}' "${PLUGIN_DIR}/config.ini")"
  fi
  if [[ -z "${path}" ]] && [[ -f "${PLUGIN_DIR}/config.defaults.ini" ]]; then
    path="$(awk -F '=' '/^[[:space:]]*socket_path[[:space:]]*=/{gsub(/^[[:space:]]+|[[:space:]]+$/,"",$2); print $2; exit}' "${PLUGIN_DIR}/config.defaults.ini")"
  fi
  if [[ -z "${path}" ]]; then
    path="/dev/shm/edmchotkeys/keyd.sock"
  fi
  echo "${path}"
}

diag_log_path_for_socket() {
  local socket_path="$1"
  local socket_dir
  socket_dir="$(dirname "${socket_path}")"
  echo "${socket_dir}/keyd_send.log"
}

fail() {
  echo "verify_keyd_integration: $1" >&2
  exit 1
}

[[ -f "${GENERATED_PATH}" ]] || fail "missing generated file: ${GENERATED_PATH}"
[[ -f "${STATE_PATH}" ]] || fail "missing export state file: ${STATE_PATH}"

if [[ -f "${TARGET_PATH}" ]]; then
  echo "found active keyd config: ${TARGET_PATH}"
else
  echo "active keyd config not found: ${TARGET_PATH}"
fi

[[ -f "${HELPER_TARGET}" ]] || fail "missing keyd helper: ${HELPER_TARGET}"
[[ -x "${HELPER_TARGET}" ]] || fail "keyd helper is not executable: ${HELPER_TARGET}"

if command -v keyd >/dev/null 2>&1 && [[ -f "${TARGET_PATH}" ]]; then
  KEYD_CHECK_OUTPUT="$(keyd check "${TARGET_PATH}" 2>&1)" || fail "keyd check failed for ${TARGET_PATH}"
  if printf "%s\n" "${KEYD_CHECK_OUTPUT}" | grep -q "WARNING:"; then
    fail "active keyd config has keyd check warnings (run: keyd check ${TARGET_PATH})"
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet keyd; then
    echo "keyd service is active"
    SOCKET_PATH="$(read_socket_path)"
    DIAG_LOG="$(diag_log_path_for_socket "${SOCKET_PATH}")"
    KEYD_PRIVATE_TMP="$(systemctl show keyd --property=PrivateTmp --value 2>/dev/null || true)"
    if [[ "${KEYD_PRIVATE_TMP}" =~ ^([Yy][Ee][Ss]|[Tt][Rr][Uu][Ee]|1)$ ]] && [[ "${SOCKET_PATH}" == /tmp/* ]]; then
      echo "warning: keyd.service uses PrivateTmp while socket_path is under /tmp (${SOCKET_PATH})."
      echo "warning: keyd command() helpers may not be able to reach EDMC socket; prefer /dev/shm/edmchotkeys/keyd.sock."
    fi
    if [[ -f "${DIAG_LOG}" ]]; then
      echo "recent keyd sender diagnostics:"
      tail -n 10 "${DIAG_LOG}"
    fi
    exit 0
  fi
  fail "keyd service is not active"
fi

if command -v pgrep >/dev/null 2>&1; then
  if pgrep -x keyd >/dev/null 2>&1; then
    echo "keyd process detected"
    SOCKET_PATH="$(read_socket_path)"
    DIAG_LOG="$(diag_log_path_for_socket "${SOCKET_PATH}")"
    if [[ -f "${DIAG_LOG}" ]]; then
      echo "recent keyd sender diagnostics:"
      tail -n 10 "${DIAG_LOG}"
    fi
    exit 0
  fi
fi

fail "unable to verify keyd is active (no systemctl/pgrep success)"
