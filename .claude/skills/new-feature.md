# Skill: New Feature Workflow

Standard process for adding a new feature to InvestAI.

## Pre-Flight

1. Check AGENTS.md for existing similar features to avoid duplication
2. Decide: does it need a new router, or extend an existing one?
3. Check Finnhub API docs if market data is involved — stay within rate limits

## Backend (ordered)

### 1. Model (if new data)
- File: `src/models.py`
- Add SQLAlchemy model with `user_id` foreign key
- Add indexes on frequently queried columns
- Ensure cascade delete behavior is defined
- Auto-migration handles new tables, but ALTER requires care (see `docs/adr/002-database-migration.md`)

### 2. Schema
- File: `src/schemas/<domain>.py`
- Create Pydantic models for: Create, Update, Response
- Use `ConfigDict(from_attributes=True)` for ORM compatibility
- Validate: enums for fixed values, min/max for numbers, max_length for strings

### 3. Service
- File: `src/services/<domain>.py`
- Pure business logic — NO request/response objects
- Accept `db: Session` and plain data types
- Wrap external API calls in try/except
- Cache expensive operations (see `market_data.py` pattern)

### 4. Router
- File: `src/routers/<domain>.py`
- `APIRouter(prefix="/api/<domain>", tags=["<Domain>"])`
- Use `Depends(get_db)` and `request.state.user`
- Return Pydantic response models
- Add `Depends(require_admin)` if admin-only

### 5. Register Router
- File: `src/main.py`
- Add `from src.routers import <domain>` 
- Add `app.include_router(<domain>.router)`

### 6. Update AGENTS.md
- Add endpoints to the API reference table

## Frontend (ordered)

### 7. HTML Section
- File: `static/index.html`
- Add `<section id="<domain>-page" class="page-section" style="display:none">`
- Include loading spinner, content container

### 8. JS Module
- File: `static/js/<domain>.js`
- Use `fetchAPI()` from `api.js` for all HTTP calls
- Use `textContent` not `innerHTML` for user data (XSS prevention)
- Add loading/error states
- Support dark/light theme

### 9. Wire Up
- Add `<script src="/static/js/<domain>.js"></script>` in `index.html`
- Register nav item in `static/js/app.js`
- Add CSS in `static/style.css`

## Testing

### 10. Smoke Test
- File: `tests/test_api_smoke.py`
- Add test for each new endpoint (auth required, returns non-500)
- Test CRUD operations if applicable
- Test user isolation (user A can't see user B's data)

### 11. Run Tests
```bash
TESTING=1 python -m pytest tests/test_api_smoke.py -v --tb=short
```

## Checklist Before Done

- [ ] All 10 steps completed
- [ ] Smoke tests pass
- [ ] No file over 400 lines
- [ ] User data filtered by user_id
- [ ] External API calls cached and fault-tolerant
- [ ] Frontend works in dark and light theme
- [ ] Mobile responsive verified
