# Dotfiles repo (Rant2112/main)

Shell aliases/functions in `.aliases`, shared between Linux (bash) and macOS (zsh).

## Testing

- Run `make test` — runs the shellspec suite under both bash and zsh. Both must pass.
- Suite lives in `spec/`; read `spec/README.md` before adding or changing tests.
- Every alias/function in `.aliases` needs a `Describe '<exact name>'` block;
  `spec/coverage_spec.sh` fails otherwise. Helpers starting with `_` are exempt.
- When a test fails, decide whether the alias is wrong or the test is wrong before
  editing. Say which.

## Portability rules for `.aliases`

- OS-specific behavior is gated per alias with `if [[ -n $IS_MAC ]]`; shell-specific
  with `if [[ -n $IS_ZSH ]]`. Keep both branches next to each other.
- macOS ships BSD tools: no `ls --color`, `sed -i` needs `''`, no `\t`/`\+` in sed,
  no `find -printf`, no `date -d`, `stat -f` not `stat -c`, `ps` column is `command`
  not `cmd`, `pbpaste` not `xclip`. macOS `/bin/bash` is 3.2.
- Tests must not assume GNU wording either (e.g. `mkdir -v`, `rm -v` output differs),
  and macOS temp dirs are under `/var` -> `/private/var` (use `pwd -P`).
- `Skip if` conditions must use `no_bin NAME`, not `command -v`, because aliases
  can shadow binary names (`pstree`).

## Don't

- Don't commit; leave that to me.
- Don't add new dependencies; shellspec is vendored in `spec/shellspec/`.
