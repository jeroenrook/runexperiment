.PHONY: commit test lint

commit:
	pre-commit run --all-files; git add -u && git commit

test:
	pytest

lint:
	pre-commit run --all-files
