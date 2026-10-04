SHELL := /usr/bin/bash
.SHELLFLAGS := -ec

GREEN := $(shell printf '\033[0;32m')
YELLOW := $(shell printf '\033[0;33m')
RESET := $(shell printf '\033[0m')
CYAN := $(shell printf '\033[0;36m')
RED := $(shell printf '\033[0;31m')
SUCCESS := $(GREEN)✓
FAIL := $(RED)✗
INFO := $(CYAN)ℹ
WARN := $(YELLOW)⚠

PRINT_BANNER := ./scripts/bash/print_banner.sh
PRINT_SUCCESS := ./scripts/bash/print_success.sh
PRINT_FAIL := ./scripts/bash/print_fail.sh
PRINT_INFO := ./scripts/bash/print_info.sh
PRINT_WARN := ./scripts/bash/print_warn.sh
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python

.DEFAULT_GOAL := help

help: ## Show available targets
	@$(PRINT_BANNER) "Available Makefile Targets"
	@LC_ALL=C.UTF-8 awk '\
		function trim(s) { \
			sub(/^[[:space:]]+/, "", s); \
			sub(/[[:space:]]+$$/, "", s); \
			return s \
		} \
		/^# ──[[:space:]]+/ { \
			title = $$0; \
			sub(/^# ──[[:space:]]+/, "", title); \
			sub(/[[:space:]]*─+[[:space:]]*$$/, "", title); \
			title = trim(title); \
			n++; kind[n] = "section"; text[n] = title; \
			next \
		} \
		/^[a-zA-Z_-]+:.*## / { \
			name = $$0; sub(/:.*/, "", name); \
			msg = $$0; sub(/^[^#]*## /, "", msg); \
			n++; kind[n] = "target"; names[n] = name; msgs[n] = msg; \
			if (length(name) > name_width) name_width = length(name); \
			next \
		} \
		END { \
			for (i = 1; i <= n; i++) \
				if (kind[i] == "target") { \
					line = 2 + name_width + 1 + length(msgs[i]); \
					if (line > line_width) line_width = line \
				} \
			for (i = 1; i <= n; i++) \
				if (kind[i] == "section") { \
					label = "── " text[i] " "; \
					pad = line_width - length(label); \
					if (pad < 1) pad = 1; \
					dashes = ""; \
					for (j = 0; j < pad; j++) dashes = dashes "─"; \
					printf "%s%s\n", label, dashes \
				} else \
					printf "  $(CYAN)%-*s$(RESET) %s\n", name_width, names[i], msgs[i] \
		}' Makefile

.PHONY: venv
venv: ## Create the project virtual environment if needed
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		if ! python3 -m venv "$(VENV_DIR)"; then \
			echo "Unable to create a Python virtual environment at $(VENV_DIR)." >&2; \
			echo "Install the venv module for this Python (on Debian/Ubuntu: sudo apt install python3-venv) and run the target again." >&2; \
			exit 1; \
		fi; \
		"$(VENV_PYTHON)" -m pip install --disable-pip-version-check -r requirements.txt; \
	fi

.PHONY: clone-repositories
clone-repositories: ## Clone the repositories listed in config.toml
	@$(PRINT_BANNER) "Cloning Repositories"
	@./clone_repositories.sh
	@$(PRINT_SUCCESS) "Repositories cloned successfully!"

.PHONY: generate-report
generate-report: ## Collect commit history for the repositories in config.toml
	@$(PRINT_BANNER) "Collecting Git Commit History"
	@./create_commit_history.sh
	@$(PRINT_SUCCESS) "Git commit history collected successfully!"

.PHONY: lint
lint: venv ## Lint all Python scripts in the repository
	@$(PRINT_BANNER) "Linting Python Scripts"
	@$(VENV_PYTHON) -m compileall clone_repositories.py project_config.py store_github_commit_history.py github_commit_history_visualizer.py
	@$(PRINT_SUCCESS) "Python scripts linted successfully!"

.PHONY: update-submodules
update-submodules: ## Update all git submodules
	@$(PRINT_BANNER) "Updating git submodules"
	@./scripts/bash/update_submodules.sh
	@$(PRINT_SUCCESS) "Git submodules updated successfully!"

.PHONY: clean
clean: ## Clean up generated repositories and local virtual environment
	@$(PRINT_BANNER) "Cleaning up generated files"
	@rm -rf ./transcendence $(VENV_DIR)
	@$(PRINT_SUCCESS) "Generated files cleaned up successfully!"
