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
