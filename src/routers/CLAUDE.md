# src/routers/ — Router Patterns & Gotchas

## Standard Router Pattern

Every router follows this exact pattern:

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth import get_current_user, require_admin  # if admin routes

router = APIRouter(prefix="/api/<domain>", tags=["<Domain>"])

@router.get("/")
def list_items(request: Request, db: Session = Depends(get_db)):
    user = request.state.user  # Set by AuthMiddleware
    # Call service, return Pydantic model
```

## Key Rules

1. **Thin routers** — no business logic, only HTTP concerns:
   - Parse request parameters
   - Call service function
   - Return response with proper status code
   - Handle errors with HTTPException

2. **User isolation** — every data query MUST include `user_id`:
   ```python
   items = db.query(Model).filter(Model.user_id == user.id).all()
   ```

3. **Admin protection** — admin endpoints use:
   ```python
   @router.get("/admin-thing")
   def admin_action(user=Depends(require_admin), db=Depends(get_db)):
   ```

4. **Response models** — always use Pydantic schemas from `src/schemas/`

## Router Registration

All routers are registered in `src/main.py`:
```python
app.include_router(domain.router)
```

## Gotchas

- `request.state.user` is the full User ORM object (set by `AuthMiddleware` + `get_current_user`)
- `request.state.user_id` is set by middleware BEFORE the route handler runs
- Market data routes may be slow (external API fetch) — frontend shows spinners
- Route prefix must start with `/api/` for auth middleware to require authentication
- Routes NOT under `/api/` are treated as public by AuthMiddleware
- `calendar_router.py` is named with suffix to avoid conflict with Python's `calendar` stdlib module

## Bulk Delete Pattern

Portfolio and Watchlist support bulk deletion via POST (not DELETE, to allow a JSON body):

```python
class BulkDeleteRequest(BaseModel):
    ids: List[int]

@router.post("/holdings/bulk-delete")
def bulk_remove(payload: BulkDeleteRequest, db=Depends(get_db), user=Depends(get_current_user)):
    count = db.query(Model).filter(Model.id.in_(payload.ids), Model.user_id == user.id).delete(synchronize_session="fetch")
    db.commit()
    return {"ok": True, "deleted": count}
```

Endpoints: `POST /api/portfolio/holdings/bulk-delete`, `POST /api/screener/watchlist/bulk-delete`

## AI Assistant Router (`assistant.py`)

Two-tier AI chat with model routing + suggestion management.

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/assistant/chat` | user | SSE streaming chat — routes to gpt-5-nano (simple) or o3 (complex) |
| GET | `/api/assistant/status` | user | Check if AI assistant is configured |
| POST | `/api/assistant/suggest` | user | Submit a feature suggestion |
| POST | `/api/assistant/suggest/{id}/vote` | user | Upvote a suggestion |
| GET | `/api/assistant/suggestions` | admin | List all suggestions (with pagination) |
| PUT | `/api/assistant/suggestions/{id}` | admin | Update suggestion status/notes |
| GET | `/api/assistant/suggestions/stats` | admin | Suggestion stats by status |

### Key Patterns

- **SSE streaming**: `POST /chat` returns `text/event-stream` via `StreamingResponse`. Each event is `data: {json}\n\n`. Event types: `model` (which model was chosen), `token` (text chunk), `tool` (tool invocation), `error`, `done`.
- **Model routing**: The service classifies each message as SIMPLE/COMPLEX/SUGGESTION using gpt-5-nano, then routes accordingly.
- **Tool calling**: o3 can call 16 tools — results are fed back and the model streams a final answer.
  - Write: `add_to_portfolio`, `add_to_watchlist`, `remove_from_watchlist`, `create_alert`, `add_transaction`
  - Read: `get_my_portfolio`, `get_my_watchlist`, `get_my_alerts`, `get_dashboard_summary`, `get_my_budgets`
  - Analyze: `get_stock_quote`, `search_screener`, `get_ai_picks`, `get_trading_signals`
  - Navigate: `navigate_to` — emits SSE `navigate` event so frontend switches pages
  - Meta: `submit_suggestion` — creates DB entry + GitHub Issue
- **GitHub Issues sync**: suggestions auto-create GitHub issues; admin status changes sync back (close/reopen/comment)
- **No `_is_configured()` → 501**: If Azure env vars aren't set, endpoints return 501 Service Unavailable.
