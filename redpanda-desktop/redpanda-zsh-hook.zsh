# GPT-REDPANDA terminal metadata hook.
# Captures only: epoch, previous command exit status, current working directory.
# It intentionally does NOT record command text or keystrokes.

_redpanda_emit_event() {
  local code=$?
  local event_file="${REDPANDA_EVENT_FILE:-}"
  [[ -n "$event_file" ]] || return 0
  [[ -d "${event_file:h}" && -w "${event_file:h}" ]] || return 0
  printf '%s\t%s\t%s\n' "$(date +%s)" "$code" "$PWD" >> "$event_file" 2>/dev/null || true
  return $code
}

autoload -Uz add-zsh-hook 2>/dev/null || true
add-zsh-hook precmd _redpanda_emit_event 2>/dev/null || true
