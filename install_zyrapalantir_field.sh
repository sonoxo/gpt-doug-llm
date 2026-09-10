#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN="$HOME/.local/bin"
mkdir -p "$BIN"

cat > "$BIN/zyra-field" <<EOF
#!/bin/sh
exec sh "$ROOT/scripts/zyra-field" "\$@"
EOF

cat > "$BIN/zyra-field-mega" <<EOF
#!/bin/sh
exec sh "$ROOT/scripts/zyra-field-mega" "\$@"
EOF

chmod +x "$BIN/zyra-field" "$BIN/zyra-field-mega"

printf '✅ ZYRAPALANTIR field terminal installed.\n'
printf '🎖️ Mega boot:  zyra-field-mega\n'
printf '📟 Console:    zyra-field status\n'
printf '🧩 Assets:     zyra-field assets\n'
printf '📶 Comms:      zyra-field comms\n'
printf '🧠 Intel:      zyra-field intel\n'
printf '🛡️ Cyber:      zyra-field cyber\n'
printf '🚨 Incidents:  zyra-field incidents\n'
printf '📋 Readiness:  zyra-field readiness\n'
printf '🧪 Simulation: zyra-field simulate\n'

case ":$PATH:" in
  *":$BIN:"*) : ;;
  *) printf '⚠️ Add ~/.local/bin to PATH for this shell: export PATH="$HOME/.local/bin:$PATH"\n' ;;
esac
