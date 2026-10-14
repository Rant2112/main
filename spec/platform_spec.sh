# shellcheck shell=bash
# Checks that the OS / shell conditionals in .aliases picked the right branch.
Describe 'platform detection'
  It 'sets IS_MAC from OSTYPE'
    case "$OSTYPE" in darwin*) want=1 ;; *) want='' ;; esac
    The variable IS_MAC should eq "$want"
  End
  It 'sets IS_ZSH from ZSH_VERSION'
    [ -n "${ZSH_VERSION:-}" ] && want=1 || want=''
    The variable IS_ZSH should eq "$want"
  End

  Describe 'on linux'
    Skip if 'not linux' [ -n "$IS_MAC" ]
    It 'uses GNU ls color flag'
      When run alias_cmd alias ls
      The output should include '--color'
    End
  End
  Describe 'on mac'
    Skip if 'not mac' [ -z "$IS_MAC" ]
    It 'uses BSD ls color flag'
      When run alias_cmd alias ls
      The output should include 'ls -G'
    End
  End
  Describe 'vnckill'
    It 'is defined on linux'
      Skip if 'not linux' [ -n "$IS_MAC" ]
      When run alias_cmd type vnckill
      The status should be success
      The output should be present
    End
    It 'is not defined on mac'
      Skip if 'not mac' [ -z "$IS_MAC" ]
      When run alias_cmd "type vnckill 2>&1"   # bash reports on stderr, zsh on stdout
      The status should be failure
      The output should include 'not found'
    End
  End
  Describe 'xt'
    It 'is defined on linux'
      Skip if 'not linux' [ -n "$IS_MAC" ]
      When run alias_cmd type xt
      The status should be success
      The output should be present
    End
    It 'is not defined on mac'
      Skip if 'not mac' [ -z "$IS_MAC" ]
      When run alias_cmd "type xt 2>&1"   # bash reports on stderr, zsh on stdout
      The status should be failure
      The output should include 'not found'
    End
  End
  Describe 'myxrdb'
    It 'is defined on linux'
      Skip if 'not linux' [ -n "$IS_MAC" ]
      When run alias_cmd type myxrdb
      The status should be success
      The output should be present
    End
    It 'is not defined on mac'
      Skip if 'not mac' [ -z "$IS_MAC" ]
      When run alias_cmd "type myxrdb 2>&1"   # bash reports on stderr, zsh on stdout
      The status should be failure
      The output should include 'not found'
    End
  End
End
