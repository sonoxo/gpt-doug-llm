#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p "$HOME/.local/bin" "$HOME/.config/gpt-doug"
cat > "$HOME/.local/bin/zyra" <<EOF
#!/bin/sh
cd "$ROOT"
exec env ZYRA_ACTIVE=1 python3 "$ROOT/zyra_chat.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/zyra"
python3 - "$HOME/.zshrc" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); text=path.read_text() if path.exists() else ''
start='# >>> GPT-DOUG ZYRA TERMINAL >>>'; end='# <<< GPT-DOUG ZYRA TERMINAL <<<'
if start in text and end in text:
    before,rest=text.split(start,1); _,after=rest.split(end,1); text=before.rstrip()+'\n'+after.lstrip()
block=f'''{start}
export PATH="$HOME/.local/bin:$PATH"
zyra() {{ "$HOME/.local/bin/zyra" "$@"; }}
if [[ -o interactive && -t 0 && -f "$HOME/.config/gpt-doug/zyra-autostart" && -z "${{ZYRA_ACTIVE:-}}" ]]; then
  "$HOME/.local/bin/zyra"
fi
{end}
'''
path.write_text(text.rstrip()+'\n\n'+block)
PY
echo 'ZYRA terminal launcher upgraded.'
echo 'Run: source ~/.zshrc && zyra'
