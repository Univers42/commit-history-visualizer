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

## README:
### If you have Python 3.11 or later, you can use the built-in tomllib module to read TOML files.
TRANSCENDENCE_ROUTE := $(shell python3 -c "import tomllib; print(tomllib.load(open('config.toml', 'rb'))['clone']['directory'])")
### If you have an earlier version of Python, you can use the tomli module instead.
# TRANSCENDENCE_ROUTE := $(shell python3 -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["clone"]["directory"])')
## END OF README

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

# ── Utils ────────────────────────────────────────────────────────────────
.PHONY: clone-repositories
clone-repositories: ## Clone the repositories listed in config.toml
	@$(PRINT_BANNER) "Cloning Repositories"
	@./clone_repositories.sh
	@$(call print_success,Repositories cloned successfully!)

.PHONY: generate-report
generate-report: ## Collect commit history for the repositories in config.toml
# 	@$(MAKE) -s clone-repositories
	@$(PRINT_BANNER) "Collecting Git Commit History"
	@./create_commit_history.sh
	@$(call print_success,Git commit history collected successfully!)

.PHONY: lint
lint: ## Lint all Python scripts in the repository
	@$(PRINT_BANNER) "Linting Python Scripts"
	@./scripts/python/lint_python_scripts.py
	@$(call print_success,Python scripts linted successfully!)

.PHONY: update-submodules
update-submodules: ## Update all git submodules
	@$(PRINT_BANNER) "Updating git submodules"
	@./scripts/bash/update_submodules.sh

.PHONY: clean
clean: ## Clean up cloned repositories
	@$(PRINT_BANNER) "Cleaning up generated files"
# 	@rm -rf $(TRANSCENDENCE_ROUTE)
	@rm -rf ./transcendence
	@$(call print_success,Generated files cleaned up successfully!)
