#!/bin/sh
set -eu

REPO_URL="https://github.com/sonoxo/gpt-doug-llm.git"
INSTALL_DIR="$HOME/.local/share/gpt-doug-llm"
BIN_DIR="$HOME/.local/bin"

command -v git >/dev/null 2>&1 || { echo "❌ Git is required."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required."; exit 1; }

mkdir -p "$BIN_DIR" "$(dirname "$INSTALL_DIR")"
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "🔄 Updating the dedicated GPT-DOUG installation…"
  git -C "$INSTALL_DIR" fetch origin main
  git -C "$INSTALL_DIR" merge --ff-only origin/main
else
  echo "📦 Installing GPT-DOUG Market Terminal…"
  git clone --depth 1 --branch main "$REPO_URL" "$INSTALL_DIR"
fi

chmod +x "$INSTALL_DIR/doug-market"
cat > "$BIN_DIR/doug-market" <<EOF
#!/bin/sh
exec "$INSTALL_DIR/doug-market" "\$@"
EOF
chmod +x "$BIN_DIR/doug-market"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    ZSHRC="$HOME/.zshrc"
    touch "$ZSHRC"
    grep -F 'export PATH="$HOME/.local/bin:$PATH"' "$ZSHRC" >/dev/null 2>&1 || printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$ZSHRC"
    ;;
esac

echo "✅ Installed without changing your current repository or working files."
exec "$BIN_DIR/doug-market"
