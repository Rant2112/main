# Testing `.aliases`

## Run

```
cd ~/Documents/git/github/main
make test
```

One shell only: `make test-zsh` / `make test-bash`.
One file: `spec/shellspec/shellspec --shell zsh spec/git_spec.sh`.
One example: append `:LINE`, e.g. `spec/git_spec.sh:57`.

### Or let Claude Code run it

```
cd ~/Documents/git/github/main
claude
```

then tell it: `run make test and fix any failures`. It runs on the real
macOS shells, reads the failures, and can edit `.aliases` or the specs
directly. `CLAUDE.md` at the repo root gives it the standing rules for this
suite. Review its diff (`git diff`) before committing.

## What it is

A [shellspec](https://github.com/shellspec/shellspec) suite. shellspec is a
single POSIX-shell script, vendored at `spec/shellspec/`, so nothing needs
installing. The same specs run under bash and zsh, which matters because
`.aliases` has `IS_ZSH` branches.

Every test sources `.aliases` (via `spec/spec_helper.sh`) and most run inside
a throwaway git repo (`make_repo`) with a fixed layout:

```
f.txt        contains a tab and trailing whitespace
sub/g.txt
old~  #junk#  editor backup files for `clean`
branch feat   plus a local "origin" remote so gp / gf / wtao work
```

## Files

| file                   | covers                                               |
|------------------------|------------------------------------------------------|
| `spec_helper.sh`       | sources `.aliases`, `make_repo`/`rm_repo`, `alias_cmd` |
| `git_spec.sh`          | g gr gs gd gdn brn gg gl gp gf gfg gm mc isgit rps wta wtao grtmp |
| `files_spec.sh`        | ls ll lld llt ldir l mcd cdrp newname clean nows latest awkp sp |
| `history_spec.sh`      | h hg                                                 |
| `process_spec.sh`      | j mdps pstree pstreefull wat mylsof pause relabel rlbn tm e xc |
| `platform_spec.sh`     | IS_MAC / IS_ZSH detection; vnckill xt myxrdb defined only on Linux |
| `coverage_spec.sh`     | fails if any alias/function lacks a `Describe` block |

## Adding an alias

1. Add it to `.aliases`.
2. Add a `Describe '<name>'` block in the matching `*_spec.sh`. The name in
   quotes must match the alias/function name exactly; `coverage_spec.sh`
   greps for it and fails the suite otherwise. Helpers starting with `_`
   (like `_tm_try`) are exempt.
3. `make test`.

Pattern for an alias (needs `alias_cmd` so it expands in both shells):

```
Describe 'gs'
  It 'is git status'
    When run alias_cmd gs
    The output should include 'On branch main'
  End
End
```

Pattern for a function (`When call` runs it in the current shell, so you can
check side effects like `PWD` or exported variables):

```
Describe 'mcd'
  It 'makes a dir and cds into it'
    When call mcd newdir/deeper
    The output should include 'created directory'
    The variable PWD should end with '/newdir/deeper'
  End
End
```

shellspec warns if a command produces stdout/stderr or a non-zero status that
no `The ...` line checks, so assert on everything the command emits.

## Platform-specific branches

Tests that only make sense on one platform use `Skip if`:

```
Skip if 'not mac' [ -z "$IS_MAC" ]
```

Skipped tests are listed at the end of the run. Linux-only branches can't be
verified on a Mac and vice versa, so run the suite on both when you touch an
`IS_MAC` conditional.

## Known skips

- `grtmp` needs the `cursor` CLI.
- `pause` is only checked for definition; `read -k`/`read -n` need a tty.
