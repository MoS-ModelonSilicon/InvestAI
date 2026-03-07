# Skill: Refactor Playbook

Guidelines for safely refactoring InvestAI code.

## Before You Start

1. **Run smoke tests** — establish a green baseline
   ```bash
   TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short
   ```
2. **Identify blast radius** — which endpoints/pages will be affected?
3. **Check file size** — if a file is over 400 lines, splitting is the right call

## Safe Refactor Patterns

### Extracting a Service from a Router
Routers should be thin (HTTP in/out). If you see business logic in a router:

1. Create `src/services/<domain>.py`
2. Move logic there, accepting `db: Session` + plain types (not Request)
3. Router calls service, handles HTTP concerns (status codes, response models)
4. Run tests after each file change

### Splitting a Large File
When a file exceeds 400 lines:

1. Identify logical groupings (e.g., CRUD vs analytics vs cache)
2. Create new module with clear name
3. Move functions, update imports everywhere
4. `grep -r "from src.services.old_module import"` to find all callers
5. Run tests

### Renaming an Endpoint
1. Update router
2. Update AGENTS.md API reference
3. Update frontend JS (`static/js/<domain>.js`)
4. Search for old path: `grep -r "/api/old-path" static/`
5. Run tests

### Changing a Database Model
- **Adding a column**: Safe with defaults or nullable — auto-migration handles it
- **Renaming a column**: DANGEROUS — breaks all queries. Create new + migrate data + drop old
- **Removing a column**: Drop queries first, then column
- See `DATABASE_MIGRATION.md` for PostgreSQL specifics

## Gotchas

- `src/services/technical_analysis.py` is 1100+ lines — it's intentionally large (pure math, self-contained). Don't split unless adding capabilities.
- `src/main.py` has auth routes + middleware + router registration — keep core auth here, domain routes in routers.
- `static/js/app.js` handles ALL navigation — be very careful with the page-switching logic.
- Front-end uses `display: none` sections — check you're not hiding the wrong one.

## After Refactor

1. Run full smoke test suite
2. Manual-check affected pages in browser
3. Verify no orphaned imports: `python -c "from src.main import app"`
4. Update AGENTS.md if structure changed
