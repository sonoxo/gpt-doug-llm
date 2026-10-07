#!/bin/sh
set -eu
BASE="${GPTDOUG_HOME:-$HOME/.config/gptdoug/src/gpt-doug-llm}"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
SRC="$BASE/cloud-swarm/terminal.py"
if [ ! -f "$SRC" ]; then
  echo "Missing $SRC"
  echo "Clone or pull https://github.com/sonoxo/gpt-doug-llm into $BASE first."
  exit 1
fi
cat > "$BIN/gpt-doug-cloud" <<EOF
#!/bin/sh
exec python3 "$SRC" "\$@"
EOF
chmod +x "$BIN/gpt-doug-cloud"
echo "✅ installed: $BIN/gpt-doug-cloud"
echo "Run: gpt-doug-cloud --demo"
