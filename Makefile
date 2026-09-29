.DEFAULT_GOAL := help

VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

.PHONY: help venv test lint clean clean-outputs clean-all run-server sso-refresh

help: ## Show this help
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create .venv (if missing), install dev deps, and editable-install this package
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

test: ## Run the pytest suite (override with TEST=path/to/test_file.py)
	pytest $(TEST)

lint: ## Run pylint over src/ and scripts/ (per .pylintrc -- Google Style Guide, see CONTRIBUTING.md)
	pylint src scripts

clean: ## Remove local caches and pyc files (leaves output/ and logs/ data untouched)
	find . -type d -name '__pycache__' -not -path './$(VENV_DIR)/*' -exec rm -rf {} +
	find . -type f -name '*.pyc' -not -path './$(VENV_DIR)/*' -exec rm -f {} +
	rm -rf .pytest_cache

clean-outputs: ## DESTRUCTIVE: delete downloaded query result CSVs (output/) and run logs (logs/) — not part of `clean`
	find output -type f -name '*.csv' -delete
	find logs -type f -name '*.log' -delete

clean-all: clean ## clean + remove the .venv
	rm -rf $(VENV_DIR)

# --- Targets below become live once their backing script lands ---
# (see docs/plans/athena-mcp-server/tasks.md — MCP-1 ports athena_runner,
# MCP-4 adds run_athena_mcp_server.py). Until then these fail on purpose
# with a clear "not implemented yet" message rather than silently no-op'ing.

# --- Targets below become live once their backing code lands ---
# (see docs/plans/athena-mcp-server/tasks.md -- MCP-1 ports athena_runner,
# MCP-4 adds the athena_mcp console-script entry point declared in
# pyproject.toml's [project.scripts]). Until then these fail on purpose
# with a clear "not implemented yet" message rather than silently no-op'ing.

run-server: ## Start the MCP stdio server (needs MCP-4's athena-mcp-server console script)
	@$(PYTHON) -c "import shutil, sys; sys.exit(0 if shutil.which('athena-mcp-server') else 1)" || \
	  (echo "Not implemented yet -- see tasks.md task MCP-4" && exit 1)
	athena-mcp-server

sso-refresh: ## Refresh the AWS SSO session (needs MCP-3's refresh_athena_sso tool / MCP-4's CLI wiring)
	@$(PYTHON) -c "import athena_mcp" 2>/dev/null || \
	  (echo "Not implemented yet -- see tasks.md tasks MCP-2/MCP-3" && exit 1)
	$(PYTHON) -m athena_mcp.cli --refresh-sso

