# shellcheck shell=bash
Describe 'file and directory aliases'
  BeforeEach 'make_repo'
  AfterEach  'rm_repo'

  Describe 'ls'
    It 'lists with color flag accepted'
      When run alias_cmd ls
      The status should be success
      The output should include 'f.txt'
    End
  End
  Describe 'll'
    It 'long lists including dotfiles'
      When run alias_cmd ll
      The output should include '.git'
    End
  End
  Describe 'lld'
    It 'lists a directory itself, not contents'
      When run alias_cmd lld sub
      The lines of output should eq 1
      The output should include 'sub'
    End
  End
  Describe 'llt'
    It 'lists sorted by time'
      When run alias_cmd llt
      The status should be success
      The output should include 'f.txt'
    End
  End
  Describe 'ldir'
    It 'shows only directories'
      When run alias_cmd ldir
      The output should include 'sub'
      The output should not include 'f.txt'
    End
  End
  Describe 'l'
    It 'is less -i'
      When run alias_cmd l f.txt
      The output should include 'line'
    End
  End
  Describe 'mcd'
    It 'makes a dir and cds into it'
      When call mcd newdir/deeper
      The output should include 'newdir'   # GNU says 'created directory', BSD just prints the path
      The variable PWD should end with '/newdir/deeper'
    End
  End
  Describe 'cdrp'
    It 'cds to the real path'
      ln -s sub link && cd link
      When run alias_cmd 'cdrp && pwd'
      The output should eq "$REPO/sub"
    End
  End
  Describe 'newname'
    It 'returns name unchanged if free'
      When call newname nope.txt
      The output should eq 'nope.txt'
    End
    It 'appends .N if taken'
      touch f.txt.0
      When call newname f.txt
      The output should eq 'f.txt.1'
    End
  End
  Describe 'clean'
    It 'removes editor backup files without erroring'
      When run alias_cmd clean
      The status should be success
      The output should include "old~"   # GNU: removed 'old~'   BSD: old~
      The file 'old~' should not be exist
      The file '#junk#' should not be exist
    End
    It 'does not error when nothing matches'
      rm -f 'old~' '#junk#'
      When run alias_cmd clean
      The status should be success
    End
  End
  Describe 'nows'
    It 'turns tabs into 3 spaces and strips trailing whitespace'
      When run alias_cmd nows f.txt
      The contents of file f.txt should eq "a   b
line"
    End
  End
  Describe 'latest'
    It 'lists recent files with timestamps'
      When run alias_cmd latest
      The output should include 'f.txt'
      The line 1 of output should match pattern '20[0-9][0-9]-[0-9][0-9]-[0-9][0-9] *'
    End
  End
  Describe 'awkp'
    It 'prints matching paragraphs with file header'
      printf 'para one\n\npara two has needle\n' > p.txt
      When call awkp needle p.txt
      The status should be success
      The output should include '==> p.txt <=='
      The output should include 'para two'
      The output should not include 'para one'
    End
    It 'fails when nothing matches'
      When call awkp zzz f.txt
      The status should be failure
    End
  End
  Describe 'sp'
    It 'prints 5 blank lines'
      When run alias_cmd 'sp | wc -l | tr -d " "'   # BSD wc pads with spaces
      The output should eq 5
    End
  End
End
