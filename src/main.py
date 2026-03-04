from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database import engine, get_db, Base
from src.models import Category, User
from src.auth import (
    AuthMiddleware, COOKIE_NAME, ACCESS_TOKEN_EXPIRE_DAYS,
    create_access_token, hash_password, verify_password,
)
from src.routers import (
    categories, transactions, budgets, dashboard, profile, screener,
    recommendations, market, stock_detail, portfolio, news, comparison,
    alerts, education, calendar_router, israeli_funds, value_scanner,
    autopilot, smart_advisor, trading_advisor, picks_tracker,
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
app.include_router(autopilot.router)
app.include_router(smart_advisor.router)
app.include_router(trading_advisor.router)
app.include_router(picks_tracker.router)


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("static/login.html")


class LoginBody(BaseModel):
    email: str
    password: str


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str = ""


@app.post("/auth/register")
def do_register(body: RegisterBody):
    db: Session = next(get_db())
    try:
        existing = db.query(User).filter(User.email == body.email.lower().strip()).first()
        if existing:
            return JSONResponse(status_code=400, content={"detail": "Email already registered"})
        user = User(
            email=body.email.lower().strip(),
            hashed_password=hash_password(body.password),
            name=body.name.strip(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token(user.id, user.email)
        resp = JSONResponse(content={"ok": True, "name": user.name, "email": user.email})
        resp.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=ACCESS_TOKEN_EXPIRE_DAYS * 86400,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return resp
    finally:
        db.close()


@app.post("/auth/login")
def do_login(body: LoginBody):
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.email == body.email.lower().strip()).first()
        if not user or not verify_password(body.password, user.hashed_password):
            return JSONResponse(status_code=403, content={"detail": "Invalid email or password"})
        token = create_access_token(user.id, user.email)
        resp = JSONResponse(content={"ok": True, "name": user.name, "email": user.email})
        resp.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=ACCESS_TOKEN_EXPIRE_DAYS * 86400,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return resp
    finally:
        db.close()


@app.get("/auth/me")
def get_me(request: Request):
    """Return current user info from JWT cookie."""
    from src.auth import decode_token
    cookie = request.cookies.get(COOKIE_NAME, "")
    payload = decode_token(cookie) if cookie else None
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user:
            return JSONResponse(status_code=401, content={"detail": "User not found"})
        return {"name": user.name, "email": user.email}
    finally:
        db.close()


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

    from src.services.value_scanner import start_auto_scanner
    start_auto_scanner()

    from src.services.trading_advisor import start_trading_advisor
    start_trading_advisor()
