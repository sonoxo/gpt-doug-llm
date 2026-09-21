# GPT-DOUG // FALL TERMINAL THEME
# Terminal-native ANSI/zsh theme. Safe to source repeatedly.

if [[ -z "${ZSH_VERSION:-}" ]]; then
  print -u2 "🍂 GPT-Doug fall theme requires zsh."
  return 1 2>/dev/null || exit 1
fi

autoload -Uz colors add-zsh-hook
colors
setopt PROMPT_SUBST

export GPTDOUG_THEME="fall"
export CLICOLOR=1

# Autumn 256-color palette:
# 166 rust, 172 pumpkin, 208 orange, 214 amber, 220 gold,
# 130 brown, 142 sage, 230 cream, 240 charcoal.
typeset -g GPTDOUG_FALL_RUST=166
typeset -g GPTDOUG_FALL_PUMPKIN=172
typeset -g GPTDOUG_FALL_ORANGE=208
typeset -g GPTDOUG_FALL_AMBER=214
typeset -g GPTDOUG_FALL_GOLD=220
typeset -g GPTDOUG_FALL_BROWN=130
typeset -g GPTDOUG_FALL_SAGE=142
typeset -g GPTDOUG_FALL_CREAM=230
typeset -g GPTDOUG_FALL_DIM=240

_gptdoug_fall_git_branch() {
  local branch
  branch="$(command git symbolic-ref --quiet --short HEAD 2>/dev/null)" ||     branch="$(command git rev-parse --short HEAD 2>/dev/null)" || return 0
  print -n -- "%F{${GPTDOUG_FALL_SAGE}}🌾 ${branch}%f"
}

_gptdoug_fall_title() {
  print -Pn "\e]0;🍁 GPT-DOUG // %~\a"
}

_gptdoug_fall_hud() {
  print -P "%F{${GPTDOUG_FALL_ORANGE}}🍁 GPT-DOUG%f  %F{${GPTDOUG_FALL_GOLD}}⚡ GPT-CHAOS%f  %F{${GPTDOUG_FALL_SAGE}}🐝 HIVE%f  %F{${GPTDOUG_FALL_DIM}}// FALL CORE%f"
}

_gptdoug_fall_precmd() {
  _gptdoug_fall_title
}

add-zsh-hook -D precmd _gptdoug_fall_precmd 2>/dev/null
add-zsh-hook precmd _gptdoug_fall_precmd

PROMPT=$'\n%F{208}🍂 GPT-DOUG%f %F{240}//%f %F{220}XUNIA AUTUMN CORE%f  %F{240}%(?.🍁.🔥)%f  $(_gptdoug_fall_git_branch)\n%F{172}🎃 %~%f %F{214}❯%f '
RPROMPT='%F{240}🧠 DOUG %F{130}│%f %F{214}⚡ CHAOS %F{130}│%f %F{142}🐝 HIVE %F{240}│ %D{%H:%M}%f'

# Fall-colored completion hints.
zstyle ':completion:*' list-colors \
  'di=38;5;214' \
  'ln=38;5;208' \
  'ex=38;5;142' \
  'fi=38;5;230'

# Helpful fall HUD commands.
alias fallhud='_gptdoug_fall_hud'
alias leaves='print -P "%F{166}🍁%f  %F{208}🍂%f  %F{220}🌾%f  %F{172}🎃%f  %F{142}🍃%f  %F{214}✨%f"'

print -P "%F{166}╭──────────────────────────────────────────────╮%f"
print -P "%F{208}│ 🍂 GPT-DOUG // FALL MATRIX ONLINE 🍁        │%f"
print -P "%F{220}│ 🧠 DOUG   ⚡ CHAOS   🐝 HIVE   🎃 XUNIA     │%f"
print -P "%F{166}╰──────────────────────────────────────────────╯%f"
