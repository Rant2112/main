SHELLSPEC = spec/shellspec/shellspec

.PHONY: test test-bash test-zsh
test: test-bash test-zsh          ## run the suite under both shells

test-bash:
	$(SHELLSPEC) --shell bash

test-zsh:
	$(SHELLSPEC) --shell zsh
