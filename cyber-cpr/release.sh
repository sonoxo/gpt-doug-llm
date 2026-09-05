#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "${ROOT_DIR}/VERSION")"
DIST_DIR="${ROOT_DIR}/dist"
STAGE_DIR="${DIST_DIR}/cyber-cpr-${VERSION}"
ARCHIVE="${DIST_DIR}/cyber-cpr-${VERSION}.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"

rm -rf "${STAGE_DIR}"
mkdir -p "${STAGE_DIR}"

for file in README.md LICENSE SECURITY.md CHANGELOG.md VERSION cyber_cpr.py install.sh uninstall.sh install-service.sh uninstall-service.sh config.example.json; do
  cp "${ROOT_DIR}/${file}" "${STAGE_DIR}/${file}"
done

chmod +x "${STAGE_DIR}"/*.sh "${STAGE_DIR}/cyber_cpr.py"
tar -C "${DIST_DIR}" -czf "${ARCHIVE}" "cyber-cpr-${VERSION}"

if command -v shasum >/dev/null 2>&1; then
  (cd "${DIST_DIR}" && shasum -a 256 "$(basename "${ARCHIVE}")") > "${CHECKSUM}"
elif command -v sha256sum >/dev/null 2>&1; then
  (cd "${DIST_DIR}" && sha256sum "$(basename "${ARCHIVE}")") > "${CHECKSUM}"
else
  echo "No SHA-256 utility found" >&2
  exit 2
fi

rm -rf "${STAGE_DIR}"
echo "📦 Built ${ARCHIVE}"
echo "🔐 Checksum ${CHECKSUM}"
