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
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python

.DEFAULT_GOAL := help

define print_error
echo -e "$(FAIL) $(1)$(RESET)"
endef

define print_success
echo -e "$(SUCCESS) $(1)$(RESET)"
endef

.PHONY: help
help: ## Show available targets
	@$(PRINT_BANNER) "Available Makefile Targets"
	@echo ""
	@grep -hE '^[a-zA-Z_-]+:.*## .*$$' Makefile | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  $(CYAN)%-35s$(RESET) %s\n", $$1, $$2}'
	@echo ""

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
	@$(call print_success,Repositories cloned successfully!)

.PHONY: generate-report
generate-report: ## Collect commit history for the repositories in config.toml
	@$(PRINT_BANNER) "Collecting Git Commit History"
	@./create_commit_history.sh
	@$(call print_success,Git commit history collected successfully!)

.PHONY: lint
lint: venv ## Lint all Python scripts in the repository
	@$(PRINT_BANNER) "Linting Python Scripts"
	@$(VENV_PYTHON) -m compileall clone_repositories.py project_config.py store_github_commit_history.py github_commit_history_visualizer.py
	@$(call print_success,Python scripts linted successfully!)

.PHONY: update-submodules
update-submodules: ## Update all git submodules
	@$(PRINT_BANNER) "Updating git submodules"
	@./scripts/bash/update_submodules.sh

.PHONY: clean
clean: ## Clean up generated repositories and local virtual environment
	@$(PRINT_BANNER) "Cleaning up generated files"
	@rm -rf ./transcendence $(VENV_DIR)
	@$(call print_success,Generated files cleaned up successfully!)
