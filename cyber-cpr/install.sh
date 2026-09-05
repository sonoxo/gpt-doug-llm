#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET="${TARGET_DIR}/cyber-cpr"

mkdir -p "${TARGET_DIR}"

cat > "${TARGET}" <<EOF
#!/usr/bin/env bash
exec python3 "${ROOT_DIR}/cyber_cpr.py" "\$@"
EOF

chmod +x "${TARGET}"

echo "🚑 Cyber CPR installed to ${TARGET}"

case ":${PATH}:" in
  *":${TARGET_DIR}:"*) ;;
  *)
    echo "Add this to your shell profile if needed:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac

echo "Run: cyber-cpr check sonoxo/gpt-doug-llm"
