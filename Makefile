SHELL := /usr/bin/bash
.SHELLFLAGS := -ec

BLUE := $(shell printf '\033[0;34m')
GREEN := $(shell printf '\033[0;32m')
YELLOW := $(shell printf '\033[0;33m')
RESET := $(shell printf '\033[0m')
CYAN := $(shell printf '\033[0;36m')
ORANGE := $(shell printf '\033[0;31m')
RED := $(shell printf '\033[0;31m')
SUCCESS := $(GREEN)✓
FAIL := $(RED)✗
INFO := $(CYAN)ℹ
WARN := $(YELLOW)⚠

## README:
### If you have Python 3.11 or later, you can use the built-in tomllib module to read TOML files.
TRANSCENDENCE_ROUTE := $(shell python3 -c "import tomllib; print(tomllib.load(open('config.toml', 'rb'))['clone']['directory'])")
### If you have an earlier version of Python, you can use the tomli module instead.
# TRANSCENDENCE_ROUTE := $(shell python3 -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["clone"]["directory"])')
## END OF README

# * Top row (╭━━━╮) - round corners, full-span
# * Bottom row (╰━━━╯) - round corners, full-span
# * Merge row (┣━━━┫) - full-span, left/right T junctions
# * Merge-bottom (╰━━━╯) - alias for kind 3
# * Column cross (┣━╋━┫) - cross junctions (columns above/below)
# * Column open (┣━┳━┫) - T-down (columns start below)
# * Column close (┣━┻━┫) - T-up (columns end above)

TOP_LEFT_CORNER := $(BLUE)╭$(RESET)
TOP_RIGHT_CORNER := $(BLUE)╮$(RESET)
BOTTOM_LEFT_CORNER := $(BLUE)╰$(RESET)
BOTTOM_RIGHT_CORNER := $(BLUE)╯$(RESET)
HORIZONTAL_LINE := $(BLUE)━$(RESET)
VERTICAL_LINE := $(BLUE)┃$(RESET)
LEFT_JUNCTION := $(BLUE)┣$(RESET)
RIGHT_JUNCTION := $(BLUE)┫$(RESET)
CROSS_JUNCTION := $(BLUE)┣$(RESET)$(BLUE)━$(RESET)$(BLUE)┫$(RESET)
OPEN_JUNCTION := $(BLUE)┣$(RESET)$(BLUE)━$(RESET)$(BLUE)┫$(RESET)
CLOSE_JUNCTION := $(BLUE)┣$(RESET)$(BLUE)━$(RESET)$(BLUE)┫$(RESET)

.DEFAULT_GOAL := help

# Reusable text banner: $(call print_banner,Your message)
define print_banner
box_width=50; \
inner_width=$$((box_width - 2)); \
message="$(1)"; \
message_length=$${#message}; \
padding=$$((inner_width - message_length)); \
left_padding=$$((padding / 2)); \
right_padding=$$((padding - left_padding)); \
top_border="$(TOP_LEFT_CORNER)"; \
bottom_border="$(BOTTOM_LEFT_CORNER)"; \
horizontal_line="$(HORIZONTAL_LINE)"; \
vertical_line="$(VERTICAL_LINE)"; \
for ((i=0; i<box_width-2; i++)); do top_border="$$top_border$$horizontal_line"; bottom_border="$$bottom_border$$horizontal_line"; done; \
top_border="$$top_border$(TOP_RIGHT_CORNER)"; \
bottom_border="$$bottom_border$(BOTTOM_RIGHT_CORNER)"; \
printf "%s\n" "$$top_border"; \
printf "%s%*s%s%*s%s\n" "$$vertical_line" "$$left_padding" '' "$$message" "$$right_padding" '' "$$vertical_line"; \
printf "%s\n" "$$bottom_border"
endef

define print_error
echo -e "$(FAIL) $(1)$(RESET)"
endef

define print_success
echo -e "$(SUCCESS) $(1)$(RESET)"
endef

.PHONY: help
help: ## Show available targets
	@$(call print_banner,Available Makefile Targets)
	@echo ""
	@grep -hE '^[a-zA-Z_-]+:.*## .*$$' Makefile | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  $(CYAN)%-35s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Utils ────────────────────────────────────────────────────────────────
.PHONY: clone-repositories
clone-repositories: ## Clone the repositories listed in config.toml
	@$(call print_banner,Cloning Repositories)
	@./clone_repositories.sh
	@$(call print_success,Repositories cloned successfully!)

.PHONY: generate-report
generate-report: ## Collect commit history for the repositories in config.toml
# 	@$(MAKE) -s clone-repositories
	@$(call print_banner,Collecting Git Commit History)
	@./create_commit_history.sh
	@$(call print_success,Git commit history collected successfully!)

.PHONY: lint
lint: ## Lint all Python scripts in the repository
	@$(call print_banner,Linting Python Scripts)
	@./scripts/python/lint_python_scripts.py
	@$(call print_success,Python scripts linted successfully!)

.PHONY: update-submodules
update-submodules: ## Update all git submodules
	@$(call print_banner,Updating git submodules)
	@./scripts/bash/update_submodules.sh

.PHONY: clean
clean: ## Clean up cloned repositories
	@$(call print_banner,Cleaning up generated files)
	@rm -rf $(TRANSCENDENCE_ROUTE)
	@$(call print_success,Generated files cleaned up successfully!)