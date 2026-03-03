import hmac

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import engine, get_db, Base
from src.models import Category
from src.auth import (
    AuthMiddleware, ACCESS_KEY, COOKIE_NAME,
    create_session_cookie, SESSION_TTL,
)
from src.routers import (
    categories, transactions, budgets, dashboard, profile, screener,
    recommendations, market, stock_detail, portfolio, news, comparison,
    alerts, education, calendar_router, israeli_funds, value_scanner,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="InvestAI")


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


app.add_middleware(NoCacheStaticMiddleware)
app.add_middleware(AuthMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(dashboard.router)
app.include_router(profile.router)
app.include_router(screener.router)
app.include_router(recommendations.router)
app.include_router(market.router)
app.include_router(stock_detail.router)
app.include_router(portfolio.router)
app.include_router(news.router)
app.include_router(comparison.router)
app.include_router(alerts.router)
app.include_router(education.router)
app.include_router(calendar_router.router)
app.include_router(israeli_funds.router)
app.include_router(value_scanner.router)


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("static/login.html")


class LoginBody(BaseModel):
    key: str


@app.post("/auth/login")
def do_login(body: LoginBody):
    if not hmac.compare_digest(body.key, ACCESS_KEY):
        return JSONResponse(status_code=403, content={"detail": "Invalid access key"})
    cookie_val, _ = create_session_cookie()
    resp = JSONResponse(content={"ok": True})
    resp.set_cookie(
        key=COOKIE_NAME,
        value=cookie_val,
        max_age=SESSION_TTL,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return resp


@app.get("/auth/logout")
def do_logout():
    resp = FileResponse("static/login.html")
    resp.delete_cookie(key=COOKIE_NAME, path="/")
    return resp


def _seed_default_categories(db: Session):
    if db.query(Category).count() > 0:
        return
    defaults = [
        ("Salary", "#22c55e", "income"),
        ("Freelance", "#10b981", "income"),
        ("Investments", "#06b6d4", "income"),
        ("Food & Dining", "#f97316", "expense"),
        ("Transportation", "#eab308", "expense"),
        ("Housing", "#ef4444", "expense"),
        ("Utilities", "#8b5cf6", "expense"),
        ("Entertainment", "#ec4899", "expense"),
        ("Shopping", "#6366f1", "expense"),
        ("Healthcare", "#14b8a6", "expense"),
        ("Education", "#3b82f6", "expense"),
        ("Other", "#64748b", "expense"),
    ]
    for name, color, typ in defaults:
        db.add(Category(name=name, color=color, type=typ))
    db.commit()


@app.on_event("startup")
def startup():
    db = next(get_db())
    _seed_default_categories(db)
    db.close()

    from src.services.market_data import start_cache_warmer
    start_cache_warmer()
