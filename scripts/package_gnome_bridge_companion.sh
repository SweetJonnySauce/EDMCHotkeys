#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${REPO_ROOT}/dist"
PACKAGE_NAME="edmc-hotkeys-gnome-companion"
STAMP="$(date +%Y%m%d-%H%M%S)"
STAGE_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${STAGE_DIR}"
}
trap cleanup EXIT

mkdir -p "${OUT_DIR}"
mkdir -p "${STAGE_DIR}/${PACKAGE_NAME}"

cp -R "${REPO_ROOT}/companion" "${STAGE_DIR}/${PACKAGE_NAME}/companion"
mkdir -p "${STAGE_DIR}/${PACKAGE_NAME}/scripts"
cp "${REPO_ROOT}/scripts/install_gnome_bridge_companion.sh" "${STAGE_DIR}/${PACKAGE_NAME}/scripts/"
cp "${REPO_ROOT}/scripts/uninstall_gnome_bridge_companion.sh" "${STAGE_DIR}/${PACKAGE_NAME}/scripts/"
cp "${REPO_ROOT}/scripts/verify_gnome_bridge_companion.sh" "${STAGE_DIR}/${PACKAGE_NAME}/scripts/"
cp "${REPO_ROOT}/scripts/export_companion_bindings.py" "${STAGE_DIR}/${PACKAGE_NAME}/scripts/"
cp "${REPO_ROOT}/docs/gnome-wayland-bridge-prototype.md" "${STAGE_DIR}/${PACKAGE_NAME}/"
cp "${REPO_ROOT}/docs/linux-user-setup.md" "${STAGE_DIR}/${PACKAGE_NAME}/"
cp "${REPO_ROOT}/docs/gnome-companion-compatibility-matrix.md" "${STAGE_DIR}/${PACKAGE_NAME}/"

tar -C "${STAGE_DIR}" -czf "${OUT_DIR}/${PACKAGE_NAME}-${STAMP}.tar.gz" "${PACKAGE_NAME}"

echo "Companion package created:"
echo "  ${OUT_DIR}/${PACKAGE_NAME}-${STAMP}.tar.gz"
