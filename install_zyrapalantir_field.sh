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

cat > "$BIN/zyra-maven" <<EOF
#!/bin/sh
exec sh "$ROOT/scripts/zyra-maven" "\$@"
EOF

chmod +x "$BIN/zyra-field" "$BIN/zyra-field-mega" "$BIN/zyra-maven"

printf '✅ ZYRAPALANTIR field terminal installed.\n'
printf '🎖️ Mega boot:    zyra-field-mega\n'
printf '🖥️ Visual:       zyra-field visual\n'
printf '📟 Console:      zyra-field status\n'
printf '🧩 Assets:       zyra-field assets\n'
printf '📶 Comms:        zyra-field comms\n'
printf '🧠 Intel:        zyra-field intel\n'
printf '🛡️ Cyber:        zyra-field cyber\n'
printf '🚨 Incidents:    zyra-field incidents\n'
printf '📋 Readiness:    zyra-field readiness\n'
printf '🧪 Simulation:   zyra-field simulate\n'
printf '📦 Maven verify: zyra-maven verify\n'
printf '🩺 Maven doctor: zyra-maven doctor\n'
printf '🧾 Maven proof:  zyra-maven proof\n'
printf '🧠 Maven ontology: zyra-maven ontology\n'
printf '🖥️ Maven visual: zyra-maven visual\n'

case ":$PATH:" in
  *":$BIN:"*) : ;;
  *) printf '⚠️ Add ~/.local/bin to PATH for this shell: export PATH="$HOME/.local/bin:$PATH"\n' ;;
esac
