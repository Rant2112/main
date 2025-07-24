export EDITOR="emacs"

export COLOR_RED='\[\e[31m\]'
export COLOR_YELLOW='\[\e[33m\]'
export COLOR_DEFAULT='\[\e[0m\]'

# History file:
shopt -s histappend
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTTIMEFORMAT="%F %T "
# Do not ignore duplicates.  This helps with alias / function / env var suggestions.
export HISTCONTROL=''

# Prompt
__prompt_command(){
    local EXIT_CODE=$?
    PS1_EC_COLOR=""
    if [ $EXIT_CODE -ne 0 ]; then
        PS1_EC=$(printf "%3s" $EXIT_CODE)
        PS1_EC_COLOR=$COLOR_RED
    else
        PS1_EC=$(printf "%3s" $EXIT_CODE)
    fi

    local PWDWID=25
    if [ "${#PWD}" -gt "$PWDWID" ]; then
       local PWD25=$(printf "%25s" ${PWD:${#PWD}-25} | sed 's/^[^\/]*\///')
    else
        local PWD25=$PWD
    fi
    PS1_PWD=$(printf " %25s" ${PWD25})

    # (a)ppend current command to history so it is available to the 'history' command in other sessions
    history -a

    # Setting PS1 each time is the only way I could get the colors and the escaped color widths to work (so word wrap works a the correct column).
    PS1="\h ${COLOR_YELLOW}${PS1_PWD}${COLOR_DEFAULT} \! ${PS1_EC_COLOR}${PS1_EC}${COLOR_DEFAULT} $ "
}
PROMPT_COMMAND=__prompt_command
