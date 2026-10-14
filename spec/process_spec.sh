# shellcheck shell=bash
Describe 'process / session aliases'
  Describe 'j'
    It 'lists jobs'
      When run alias_cmd j
      The status should be success
    End
  End
  Describe 'mdps'
    It 'prints a ps table with the expected columns'
      When run alias_cmd mdps
      The line 1 of output should include 'PID'
      The line 1 of output should include 'ELAPSED'
    End
  End
  Describe 'pstree'
    Skip if 'pstree not installed' no_bin pstree
    It 'runs with the baked-in flags'
      When run alias_cmd pstree $$
      The status should be success
      The output should be present
    End
  End
  Describe 'pstreefull'
    Skip if 'pstree not installed' no_bin pstree
    It 'prints header then matching ps rows'
      # exit status is just that of the last grep, so only the output is checked
      When run alias_cmd "pstreefull $$ || true"
      The line 1 of output should include 'PID'
    End
  End
  Describe 'wat'
    Skip if 'watch not installed' no_bin watch
    It 'is watch with 60s interval'
      When run alias_cmd wat --version
      The status should be success
      The output should be present
    End
  End
  Describe 'mylsof'
    It 'prints lsof header'
      When run alias_cmd mylsof
      The output should include 'COMMAND'
    End
  End
  Describe 'pause'
    It 'is defined as a read'
      When run alias_cmd alias pause
      The output should include 'read'
    End
  End
  Describe 'relabel'
    It 'sets LABEL and emits a title escape'
      When call relabel my title
      The variable LABEL should eq 'my title'
      The output should include 'my title'
    End
  End
  Describe 'rlbn'
    BeforeEach 'make_repo'
    AfterEach  'rm_repo'
    It 'relabels to the repo basename'
      When run alias_cmd 'rlbn; echo "$LABEL"'
      The output should include "$(basename "$REPO")"
    End
  End
  Describe 'tm'
    Skip if 'tmux not installed' no_bin tmux
    It '_tm_try and tm are defined'
      When run alias_cmd 'type _tm_try && type tm'
      The status should be success
      The output should include 'function'
    End
  End
  Describe 'e'
    It 'is defined as a function'
      When run alias_cmd type e
      The output should include 'function'
    End
  End
  Describe 'xc'
    It 'is a clipboard paste command'
      When run alias_cmd alias xc
      The output should match pattern '*pbpaste*|*xclip*'
    End
  End
End
