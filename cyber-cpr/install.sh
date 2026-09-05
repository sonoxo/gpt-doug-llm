#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/cyber-cpr"
TARGET="${BIN_DIR}/cyber-cpr"

mkdir -p "${BIN_DIR}" "${APP_DIR}"
install -m 0755 "${ROOT_DIR}/cyber_cpr.py" "${APP_DIR}/cyber_cpr.py"

cat > "${TARGET}" <<EOF
#!/usr/bin/env bash
exec python3 "${APP_DIR}/cyber_cpr.py" "\$@"
EOF

chmod +x "${TARGET}"

echo "🚑 Cyber CPR installed"
echo "   CLI: ${TARGET}"
echo "   Engine: ${APP_DIR}/cyber_cpr.py"

case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    echo "Add this to your shell profile if needed:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac

echo "Run: cyber-cpr check sonoxo/gpt-doug-llm"
