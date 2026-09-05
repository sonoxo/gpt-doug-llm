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

cat > "$HOME/.local/bin/doug-market" <<EOF
#!/bin/sh
exec "$ROOT/doug-market" "\$@"
EOF
chmod +x "$HOME/.local/bin/doug-market" "$ROOT/doug-market"

ZSHRC="$HOME/.zshrc"
BACKUP=""
if [ -f "$ZSHRC" ]; then
  BACKUP="$ZSHRC.gpt-doug-backup-$(date +%Y%m%d-%H%M%S)"
  cp "$ZSHRC" "$BACKUP"
fi

python3 - "$ZSHRC" <<'PY'
from pathlib import Path
import re, sys
path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ''

# Remove only our previous managed block.
start = '# >>> GPT-DOUG ZYRA TERMINAL >>>'
end = '# <<< GPT-DOUG ZYRA TERMINAL <<<'
if start in text and end in text:
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    text = before.rstrip() + '\n' + after.lstrip()

# Repair the known zsh alias/function collision without deleting user commands.
known = {'doug', 'doug-voice', 'doug-max', 'doug-status', 'doug-market', 'zyra'}
aliases = set()
out = []
for line in text.splitlines():
    m = re.match(r'^\s*alias\s+([A-Za-z0-9_-]+)=', line)
    if m and m.group(1) in known:
        aliases.add(m.group(1))
    fm = re.match(r'^\s*(?:function\s+)?([A-Za-z0-9_-]+)\s*\(\s*\)\s*\{?', line)
    if fm and fm.group(1) in aliases:
        name = fm.group(1)
        if not out or f'unalias {name}' not in out[-1]:
            out.append(f'unalias {name} 2>/dev/null || true')
        aliases.discard(name)
    out.append(line)
text = '\n'.join(out).rstrip() + '\n'

boot_start = '# >>> GPT-DOUG ENV >>>'
boot_end = '# <<< GPT-DOUG ENV <<<'
text = re.sub(r'(?ms)^# >>> GPT-DOUG ENV >>>.*?^# <<< GPT-DOUG ENV <<<\n?', '', text)
boot = f'''{boot_start}
export PATH="$HOME/.local/bin:$PATH"
{boot_end}
'''

managed = f'''{start}
if [[ -o interactive && -t 0 && -f "$HOME/.config/gpt-doug/zyra-autostart" && -z "${{ZYRA_ACTIVE:-}}" ]]; then
  "$HOME/.local/bin/zyra"
fi
{end}
'''

path.write_text(boot + '\n' + text + '\n' + managed)
PY

if command -v zsh >/dev/null 2>&1; then
  if ! zsh -n "$ZSHRC"; then
    echo "ZYRA install stopped: ~/.zshrc still has a syntax error."
    if [ -n "$BACKUP" ] && [ -f "$BACKUP" ]; then
      cp "$BACKUP" "$ZSHRC"
      echo "Restored backup: $BACKUP"
    fi
    exit 1
  fi
fi

echo 'ZYRA terminal launcher repaired and upgraded.'
echo 'Launcher: ~/.local/bin/zyra'
echo 'Market terminal: ~/.local/bin/doug-market'
echo 'Start now: ~/.local/bin/zyra'
