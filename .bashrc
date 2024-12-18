export EDITOR="emacs"

export COLOR_RED='\033[31m'
export COLOR_YELLOW='\033[33m'
export COLOR_DEFAULT='\033[0m'

# Prompt
__prompt_command(){
    local EXIT_CODE=$?
#    printf " ${HOSTNAME}"
    local PWDWID=25
    if [ "${#PWD}" -gt "$PWDWID" ]; then
       local PWD25=$(printf "%25s" ${PWD:${#PWD}-25} | sed 's/^[^\/]*\///')
    else
        local PWD25=$PWD
    fi
    PS1_PWD=$(printf " ${COLOR_YELLOW}%25s${COLOR_DEFAULT}" ${PWD25})
#    local HISTNUM=$HISTCMD
#    printf " %4s" $HISTNUM
    if [ $EXIT_CODE -ne 0 ]; then
        PS1_EC=$(printf "${COLOR_RED}%3s${COLOR_DEFAULT}" $EXIT_CODE)
    else
        PS1_EC=$(printf "%3s" $EXIT_CODE)
    fi
 
#    printf " $ "
}
PROMPT_COMMAND=__prompt_command

export PS1='\h '"${COLOR_YELLOW}"'${PS1_PWD}'"${COLOR_DEFAULT}"' \! ${PS1_EC} $ '
