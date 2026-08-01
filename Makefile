# `make check` is the gate. Backend runs via uv, frontend via npm.

.DEFAULT_GOAL := help
UV  := uv run
WEB := npm --prefix web

# slr is a source tree, not an installed package ([tool.uv] package=false); put it on
# the path for import-linter and mypy (pytest gets it from pyproject pythonpath).
export PYTHONPATH := $(CURDIR)/backend

.PHONY: help install check lint arch typecheck test-unit test-int test-e2e \
        guard emit-openapi serve dev demo-concurrency demo-resale fmt clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (uv) + frontend (npm) toolchains
	uv sync
	$(WEB) install

check: lint arch typecheck test-unit test-int ## Full gate: lint + arch + types + unit + integration
	@echo "✓ check green"

lint: ## ruff (backend) + eslint (frontend)
	$(UV) ruff check backend tests
	$(WEB) run lint

arch: ## Dependency Rule: import-linter (backend) + dependency-cruiser (frontend)
	$(UV) lint-imports
	$(WEB) run arch

typecheck: ## mypy over the backend package
	$(UV) mypy

# Exit 5 = "no tests matched" (expected while a ring is empty); a real failure still fails.
test-unit: ## Tier 1 — pure unit tests (backend + frontend), milliseconds
	@$(UV) pytest -m unit --no-header; e=$$?; [ $$e -eq 0 ] || [ $$e -eq 5 ]
	$(WEB) run test

test-int: ## Tier 2 — integration: ports (real+fake), use-cases (fakes), contract, arch
	@$(UV) pytest -m "integration or concurrency or contract or arch" --no-header; e=$$?; [ $$e -eq 0 ] || [ $$e -eq 5 ]

test-e2e: ## Tier 3 — system/E2E against the live stack (needs docker compose up)
	docker compose --profile e2e run --rm e2e

guard: ## Plant a banned import in the pure core; import-linter MUST reject it
	@echo "import sqlalchemy  # planted by 'make guard'" > backend/slr/domain/_guard.py
	@echo "→ planted domain→sqlalchemy; expecting import-linter to REJECT…"
	@if $(UV) lint-imports >/dev/null 2>&1; then \
	  rm -f backend/slr/domain/_guard.py; \
	  echo "✗ GATE DEAD: import-linter accepted a banned import"; exit 1; \
	else \
	  rm -f backend/slr/domain/_guard.py; \
	  echo "✓ gate alive: banned import rejected, cleaned up"; \
	fi

emit-openapi: ## Regenerate contract/openapi.json from the live FastAPI app (D13)
	$(UV) python scripts/emit_openapi.py

serve: ## Run the API locally (needs a reachable Postgres from DATABASE_URL)
	$(UV) uvicorn slr.app.main:app --host 0.0.0.0 --port 8000 --reload

dev: ## Zero-infra playground: API on the in-memory fake, seeded with a demo trip
	$(UV) python scripts/dev_server.py

demo-concurrency: ## Fire N holds at one seat/leg → "1 booked, N−1 got 409"
	$(UV) python scripts/demo_concurrency.py

demo-resale: ## A→B and B→C on the same seat both succeed (P7)
	@echo "demo-resale lands with the E2E journey in P7"

fmt: ## Auto-fix lint where possible
	$(UV) ruff check --fix backend tests
	$(UV) ruff format backend tests

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache backend/slr/domain/_guard.py
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
