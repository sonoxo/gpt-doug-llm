#!/bin/sh
set -eu
BASE="${GPTDOUG_HOME:-$HOME/.config/gptdoug/src/gpt-doug-llm}"
SRC="$BASE/scripts/doug-gpt-maven.py"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
if [ ! -f "$SRC" ]; then
  echo "Missing $SRC"
  echo "Pull the latest sonoxo/gpt-doug-llm main branch first."
  exit 1
fi
cat > "$BIN/doug-gpt-maven" <<EOF
#!/bin/sh
exec python3 "$SRC" "\$@"
EOF
chmod +x "$BIN/doug-gpt-maven"
ln -sf "$BIN/doug-gpt-maven" "$BIN/gpt-dougmaven"
ln -sf "$BIN/doug-gpt-maven" "$BIN/gpt-maven"
echo "✅ DOUG-GPT-MAVEN installed"
echo "   doug-gpt-maven"
echo "   gpt-dougmaven"
echo "   gpt-maven"
echo "Try: doug-gpt-maven --drone"
