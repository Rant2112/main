# shellcheck shell=bash
seed_history() {
  if [ -n "${ZSH_VERSION:-}" ]; then print -s "seedmarker"; else history -s "seedmarker"; fi
}
Describe 'history aliases'
  Before 'seed_history'
  Describe 'h'
    It 'shows recent history'
      When run alias_cmd h
      The status should be success
      The output should include 'seedmarker'
    End
  End
  Describe 'hg'
    It 'greps all history'
      When run alias_cmd hg seedmarker
      The output should include 'seedmarker'
    End
  End
End
