# shellcheck shell=bash
# Loaded before every spec file. Sources .aliases and provides a scratch git repo.

ALIASES_FILE="${SHELLSPEC_PROJECT_ROOT}/.aliases"

# Alias expansion must be on in a non-interactive shell for `alias` lines to work.
if [ -n "${BASH_VERSION:-}" ]; then shopt -s expand_aliases; fi
if [ -n "${ZSH_VERSION:-}" ]; then setopt aliases; fi

# shellcheck disable=SC1090
. "$ALIASES_FILE"

# Create a throwaway git repo with a known layout and cd into it.
# Layout:  f.txt (tab + trailing ws)   sub/g.txt   old~   #junk#   branch: feat
make_repo() {
  REPO=$(mktemp -d)
  REPO=$(cd "$REPO" && pwd -P)   # resolve symlinks (macOS /var -> /private/var)
  cd "$REPO" || return 1
  git init -q -b main .
  git config user.email t@t
  git config user.name t
  printf 'a\tb  \nline\n' > f.txt
  mkdir sub && echo x > sub/g.txt
  touch 'old~' '#junk#'
  git add -A && git commit -qm init
  git branch feat
  # a local "origin" so pull/fetch have something to talk to
  git remote add origin "$REPO" && git fetch -q origin && git branch -q -u origin/main
}
rm_repo() { cd / && rm -rf "$REPO"; }

# `When run alias_cmd foo args` runs an alias through eval so it expands in both shells.
alias_cmd() { eval "$*"; }

# has_bin NAME: true if a real executable NAME exists, ignoring any alias of the same name
# (needed for `Skip if` on aliases like pstree that shadow the binary).
has_bin() { ( unalias "$1" 2>/dev/null; command -v "$1" >/dev/null 2>&1 ); }
no_bin() { ! has_bin "$1"; }
