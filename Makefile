.PHONY: sync
sync:
	@uv sync --all-extras

.PHONY: format
format:
	@ruff format .
	@ruff check --fix .

.PHONY: check
check:
	@ruff check .

.PHONY: annotate
annotate:
	@uv run chrome-extension/annotation_server.py
