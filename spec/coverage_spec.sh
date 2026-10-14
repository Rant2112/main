# shellcheck shell=bash
# Fails if any alias or function defined by .aliases has no `Describe '<name>'` block in spec/.
# Helper functions in .aliases that are internal (start with _) are exempt.

defined_names() {
  # Names the running shell actually defined when it sourced .aliases.
  if [ -n "${ZSH_VERSION:-}" ]; then
    # shellcheck disable=SC2296
    print -l -- ${(k)aliases} ${(k)functions}
  else
    alias | sed -E "s/^alias ([^=]+)=.*/\1/"
    declare -F | awk '{print $3}'
  fi
}
# Names belonging to .aliases only: diff against a clean shell that has not sourced it.
aliases_only_names() {
  defined_names | grep -v '^_' | sort -u | grep -vxF -f "$SHELLSPEC_TMPBASE/baseline" | grep -vxF -f "$SHELLSPEC_TMPBASE/helpers"
}
described_names() {
  grep -hoE "^ *Describe '[A-Za-z0-9_]+'" "$SHELLSPEC_PROJECT_ROOT"/spec/*_spec.sh | sed -E "s/.*'(.*)'/\1/" | sort -u
}
prepare() {
  # Baseline: what the bare shell + shellspec define without .aliases.
  if [ -n "${ZSH_VERSION:-}" ]; then
    zsh -c 'print -l -- ${(k)aliases} ${(k)functions}' | sort -u > "$SHELLSPEC_TMPBASE/baseline"
  else
    bash -c 'alias; declare -F | awk "{print \$3}"' | sort -u > "$SHELLSPEC_TMPBASE/baseline"
  fi
  # spec_helper's own helpers, and shellspec internals (shellspec_*).
  printf '%s\n' make_repo rm_repo alias_cmd has_bin no_bin defined_names aliases_only_names described_names prepare seed_history count_names > "$SHELLSPEC_TMPBASE/helpers"
}

Describe 'coverage: every alias and function has a Describe block'
  Before 'prepare'
  count_names() { aliases_only_names | grep -vc '^shellspec'; }
  It 'finds at least 40 names in .aliases (sanity check that extraction works)'
    When call count_names
    The output should satisfy test "[ \$(count_names) -ge 40 ]"
  End
  It 'has no untested names'
    missing=$(aliases_only_names | grep -v '^shellspec' | grep -vxF -f <(described_names) || true)
    When call printf '%s' "$missing"
    The output should eq ''
  End
End
