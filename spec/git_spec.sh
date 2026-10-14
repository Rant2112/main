# shellcheck shell=bash
Describe 'git aliases'
  BeforeEach 'make_repo'
  AfterEach  'rm_repo'

  Describe 'g'
    It 'is git'
      When run alias_cmd g log --oneline
      The output should include 'init'
    End
  End
  Describe 'gr'
    It 'prints the repo top level'
      When run alias_cmd gr
      The output should eq "$REPO"
    End
  End
  Describe 'gs'
    It 'is git status'
      When run alias_cmd gs
      The output should include 'On branch main'
    End
  End
  Describe 'gd'
    It 'is git diff'
      echo changed >> f.txt
      When run alias_cmd gd
      The output should include '+changed'
    End
  End
  Describe 'gdn'
    It 'lists only changed file names'
      echo changed >> f.txt
      When run alias_cmd gdn
      The output should eq 'f.txt'
    End
  End
  Describe 'brn'
    It 'prints current branch'
      When run alias_cmd brn
      The output should eq 'main'
    End
  End
  Describe 'gg'
    It 'is git grep'
      When run alias_cmd gg line
      The output should include 'f.txt:line'
    End
  End
  Describe 'gl'
    It 'is git log without merges'
      When run alias_cmd gl --oneline
      The output should include 'init'
    End
  End
  Describe 'gp'
    It 'pulls with prune'
      When run alias_cmd gp
      The status should be success
      The output should include 'up to date'
    End
  End
  Describe 'gf'
    It 'fetches with prune'
      When run alias_cmd gf
      The status should be success
    End
  End
  Describe 'gfg'
    It 'fetches then runs git subcommand'
      When run alias_cmd gfg branch --show-current
      The output should eq 'main'
    End
  End
  Describe 'gm'
    It 'merges without editor'
      git checkout -q feat && echo y > y.txt && git add y.txt && git commit -qm feat && git checkout -q main
      When run alias_cmd gm feat
      The status should be success
      The output should include 'y.txt'
    End
  End
  Describe 'mc'
    It 'lists conflicted files (none here)'
      When run alias_cmd mc
      The output should eq ''
    End
  End
  Describe 'isgit'
    It 'succeeds inside a repo'
      When run alias_cmd isgit
      The status should be success
    End
    It 'fails outside a repo'
      cd /
      When run alias_cmd isgit
      The status should be failure
    End
  End
  Describe 'rps'
    It 'prints a 4-char short sha'
      When call rps HEAD
      The length of output should eq 4
    End
  End
  Describe 'wta'
    It 'adds a worktree on a new branch and cds into it'
      When call wta feat2 HEAD
      The status should be success
      The error should include 'Preparing worktree'
      The output should include 'HEAD is now at'
      The variable PWD should end with '/feat2'
    End
  End
  Describe 'wtao'
    It 'requires exactly one argument'
      When call wtao
      The status should be failure
      The error should include 'Usage'
    End
    It 'checks out an origin branch as a worktree'
      git branch -q -D feat   # keep only origin/feat so wtao has to create the local branch
      When call wtao feat
      The status should be success
      The error should include 'Preparing worktree'
      The output should include 'HEAD is now at'
      The variable PWD should end with '/feat'
    End
  End
  Describe 'grtmp'
    Skip if 'cursor not installed' no_bin cursor
    It 'creates tmp/README at repo root'
      When run alias_cmd grtmp
      The file "$REPO/tmp/README" should be exist
    End
  End
End
