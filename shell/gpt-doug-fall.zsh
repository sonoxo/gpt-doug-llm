# GPT-DOUG // SYSTEM-SYNCED FALL TERMINAL THEME
# Terminal-native ANSI/zsh theme. Safe to source repeatedly.
# Follows macOS Appearance automatically: Dark -> Dark Fall, Light -> Light Fall.

if [[ -z "${ZSH_VERSION:-}" ]]; then
  print -u2 "🍂 GPT-Doug fall theme requires zsh."
  return 1 2>/dev/null || exit 1
fi

autoload -Uz colors add-zsh-hook
colors
setopt PROMPT_SUBST

export GPTDOUG_THEME="fall"
export GPTDOUG_FALL_MODE="${GPTDOUG_FALL_MODE:-auto}"
export CLICOLOR=1

typeset -g GPTDOUG_FALL_ACTIVE_MODE=""
typeset -g GPTDOUG_FALL_LABEL="DARK FALL"
typeset -g GPTDOUG_FALL_RUST=166
typeset -g GPTDOUG_FALL_PUMPKIN=172
typeset -g GPTDOUG_FALL_ORANGE=208
typeset -g GPTDOUG_FALL_AMBER=214
typeset -g GPTDOUG_FALL_GOLD=220
typeset -g GPTDOUG_FALL_BROWN=130
typeset -g GPTDOUG_FALL_SAGE=142
typeset -g GPTDOUG_FALL_CREAM=230
typeset -g GPTDOUG_FALL_DIM=244
typeset -g GPTDOUG_FALL_BG="#120b07"
typeset -g GPTDOUG_FALL_FG="#f4dfc1"
typeset -g GPTDOUG_FALL_CURSOR="#ff9f43"

_gptdoug_system_appearance() {
  case "${GPTDOUG_FALL_MODE:-auto}" in
    dark|light)
      print -r -- "$GPTDOUG_FALL_MODE"
      return 0
      ;;
  esac

  if [[ "$OSTYPE" == darwin* ]] && (( $+commands[defaults] )); then
    if command defaults read -g AppleInterfaceStyle 2>/dev/null | command grep -qi '^Dark$'; then
      print -r -- "dark"
    else
      print -r -- "light"
    fi
    return 0
  fi

  # Non-macOS fallback: stay dark unless explicitly overridden.
  print -r -- "dark"
}

_gptdoug_apply_fall_palette() {
  local mode="$1"

  if [[ "$mode" == "light" ]]; then
    GPTDOUG_FALL_LABEL="LIGHT FALL"
    GPTDOUG_FALL_RUST=130
    GPTDOUG_FALL_PUMPKIN=166
    GPTDOUG_FALL_ORANGE=172
    GPTDOUG_FALL_AMBER=136
    GPTDOUG_FALL_GOLD=100
    GPTDOUG_FALL_BROWN=94
    GPTDOUG_FALL_SAGE=65
    GPTDOUG_FALL_CREAM=52
    GPTDOUG_FALL_DIM=240
    GPTDOUG_FALL_BG="#f5ead8"
    GPTDOUG_FALL_FG="#3b2518"
    GPTDOUG_FALL_CURSOR="#b45309"
  else
    GPTDOUG_FALL_LABEL="DARK FALL"
    GPTDOUG_FALL_RUST=166
    GPTDOUG_FALL_PUMPKIN=172
    GPTDOUG_FALL_ORANGE=208
    GPTDOUG_FALL_AMBER=214
    GPTDOUG_FALL_GOLD=220
    GPTDOUG_FALL_BROWN=130
    GPTDOUG_FALL_SAGE=142
    GPTDOUG_FALL_CREAM=230
    GPTDOUG_FALL_DIM=244
    GPTDOUG_FALL_BG="#120b07"
    GPTDOUG_FALL_FG="#f4dfc1"
    GPTDOUG_FALL_CURSOR="#ff9f43"
  fi
}

_gptdoug_set_terminal_colors() {
  # OSC 10/11/12: foreground/background/cursor. Unsupported terminals safely ignore it.
  printf '\033]10;%s\007' "$GPTDOUG_FALL_FG"
  printf '\033]11;%s\007' "$GPTDOUG_FALL_BG"
  printf '\033]12;%s\007' "$GPTDOUG_FALL_CURSOR"
}

_gptdoug_sync_system_theme() {
  local force="${1:-0}"
  local mode
  mode="$(_gptdoug_system_appearance)"

  if [[ "$force" == "1" || "$mode" != "$GPTDOUG_FALL_ACTIVE_MODE" ]]; then
    _gptdoug_apply_fall_palette "$mode"
    GPTDOUG_FALL_ACTIVE_MODE="$mode"
    _gptdoug_set_terminal_colors
    if [[ "$force" == "1" ]]; then
      print -P "%F{${GPTDOUG_FALL_ORANGE}}🍂 SYSTEM SYNC%f  %F{${GPTDOUG_FALL_GOLD}}${GPTDOUG_FALL_LABEL}%f"
    fi
  fi
}

_gptdoug_fall_git_branch() {
  local branch
  branch="$(command git symbolic-ref --quiet --short HEAD 2>/dev/null)" ||
    branch="$(command git rev-parse --short HEAD 2>/dev/null)" ||
    return 0
  print -n -- "%F{${GPTDOUG_FALL_SAGE}}🌾 ${branch}%f"
}

_gptdoug_fall_title() {
  print -Pn "\e]0;🍁 GPT-DOUG // ${GPTDOUG_FALL_LABEL} // %~\a"
}

_gptdoug_fall_hud() {
  print -P "%F{${GPTDOUG_FALL_ORANGE}}🍁 GPT-DOUG%f  %F{${GPTDOUG_FALL_GOLD}}⚡ GPT-CHAOS%f  %F{${GPTDOUG_FALL_SAGE}}🐝 HIVE%f  %F{${GPTDOUG_FALL_DIM}}// ${GPTDOUG_FALL_LABEL}%f"
}

_gptdoug_fall_precmd() {
  _gptdoug_sync_system_theme
  _gptdoug_fall_title
}

add-zsh-hook -D precmd _gptdoug_fall_precmd 2>/dev/null
add-zsh-hook precmd _gptdoug_fall_precmd

# Variables remain inside the prompt string so PROMPT_SUBST can recolor on the
# next prompt when macOS Appearance changes.
PROMPT='%F{${GPTDOUG_FALL_ORANGE}}🍂 GPT-DOUG%f %F{${GPTDOUG_FALL_DIM}}//%f %F{${GPTDOUG_FALL_GOLD}}${GPTDOUG_FALL_LABEL}%f  %F{${GPTDOUG_FALL_DIM}}%(?.🍁.🔥)%f  $(_gptdoug_fall_git_branch)
%F{${GPTDOUG_FALL_PUMPKIN}}🎃 %~%f %F{${GPTDOUG_FALL_AMBER}}❯%f '
RPROMPT='%F{${GPTDOUG_FALL_DIM}}🧠 DOUG %F{${GPTDOUG_FALL_BROWN}}│%f %F{${GPTDOUG_FALL_AMBER}}⚡ CHAOS %F{${GPTDOUG_FALL_BROWN}}│%f %F{${GPTDOUG_FALL_SAGE}}🐝 HIVE %F{${GPTDOUG_FALL_DIM}}│ %D{%H:%M}%f'

# Fall-colored completion hints. These are refreshed when the theme is sourced;
# prompt colors and terminal background continue to follow system Appearance.
zstyle ':completion:*' list-colors \
  'di=38;5;214' \
  'ln=38;5;208' \
  'ex=38;5;142' \
  'fi=38;5;230'

# Manual controls when you want to override system Appearance.
darkfall() {
  export GPTDOUG_FALL_MODE="dark"
  _gptdoug_sync_system_theme 1
}

lightfall() {
  export GPTDOUG_FALL_MODE="light"
  _gptdoug_sync_system_theme 1
}

autofall() {
  export GPTDOUG_FALL_MODE="auto"
  GPTDOUG_FALL_ACTIVE_MODE=""
  _gptdoug_sync_system_theme 1
}

alias fallhud='_gptdoug_fall_hud'
alias leaves='print -P "%F{${GPTDOUG_FALL_RUST}}🍁%f  %F{${GPTDOUG_FALL_ORANGE}}🍂%f  %F{${GPTDOUG_FALL_GOLD}}🌾%f  %F{${GPTDOUG_FALL_PUMPKIN}}🎃%f  %F{${GPTDOUG_FALL_SAGE}}🍃%f  %F{${GPTDOUG_FALL_AMBER}}✨%f"'

_gptdoug_sync_system_theme
print -P "%F{${GPTDOUG_FALL_RUST}}╭──────────────────────────────────────────────╮%f"
print -P "%F{${GPTDOUG_FALL_ORANGE}}│ 🍂 GPT-DOUG // ${GPTDOUG_FALL_LABEL} ONLINE 🍁%f"
print -P "%F{${GPTDOUG_FALL_GOLD}}│ 🧠 DOUG   ⚡ CHAOS   🐝 HIVE   🎃 XUNIA     │%f"
print -P "%F{${GPTDOUG_FALL_RUST}}╰──────────────────────────────────────────────╯%f"
