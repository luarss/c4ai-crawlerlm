.PHONY: sync
sync:
	@uv sync --all-extras

.PHONY: format
format:
	@ruff format .
	@ruff check --fix .

.PHONY: complexity
complexity:
	@uv run complexipy --max-complexity-allowed 16

.PHONY: check
check:
	@ruff check .

.PHONY: label
label:
	@streamlit run scripts/label_app.py
