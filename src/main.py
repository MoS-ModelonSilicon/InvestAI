from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database import engine, get_db, Base
from src.models import Category, User, PasswordReset
from src.auth import (
    AuthMiddleware, COOKIE_NAME, ACCESS_TOKEN_EXPIRE_DAYS,
    create_access_token, hash_password, verify_password,
)
from src.routers import (
    categories, transactions, budgets, dashboard, profile, screener,
    recommendations, market, stock_detail, portfolio, news, comparison,
    alerts, education, calendar_router, israeli_funds, value_scanner,
    autopilot, smart_advisor, trading_advisor, picks_tracker, dca, admin,
)

Base.metadata.create_all(bind=engine)

# ── Auto-migrate: add missing columns to existing tables ──────
def _auto_migrate():
    """Add columns introduced after initial deploy (safe to re-run)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "is_admin" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"))
            if "is_active" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"))

_auto_migrate()

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
app.include_router(dca.router)
app.include_router(admin.router)


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
    if len(body.password) < 4:
        return JSONResponse(status_code=400, content={"detail": "Password must be at least 4 characters"})
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
        if not getattr(user, "is_active", 1):
            return JSONResponse(status_code=403, content={"detail": "Account is disabled. Contact an administrator."})
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
        return {"name": user.name, "email": user.email, "is_admin": user.is_admin or 0}
    finally:
        db.close()


class ForgotPasswordBody(BaseModel):
    email: str


class ResetPasswordBody(BaseModel):
    email: str
    code: str
    new_password: str


@app.post("/auth/forgot-password")
def forgot_password(body: ForgotPasswordBody):
    """Generate a 6-digit reset code. Sends via email if SMTP is configured, otherwise logs it."""
    import random, os, logging
    logger = logging.getLogger("investai")
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.email == body.email.lower().strip()).first()
        # Always return OK to not leak whether email exists
        if not user:
            return JSONResponse(content={"ok": True, "message": "If that email is registered, a reset code has been sent."})

        code = f"{random.randint(0, 999999):06d}"
        reset = PasswordReset(user_id=user.id, code=code)
        db.add(reset)
        db.commit()

        # Try sending email
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")
        email_sent = False
        if smtp_host and smtp_user:
            try:
                import smtplib
                from email.mime.text import MIMEText
                msg = MIMEText(f"Your InvestAI password reset code is: {code}\n\nThis code expires in 15 minutes.")
                msg["Subject"] = "InvestAI \u2014 Password Reset Code"
                msg["From"] = smtp_user
                msg["To"] = user.email
                with smtplib.SMTP(smtp_host, int(os.environ.get("SMTP_PORT", 587))) as s:
                    s.starttls()
                    s.login(smtp_user, smtp_pass or "")
                    s.send_message(msg)
                logger.info(f"Reset code sent to {user.email}")
                email_sent = True
            except Exception as e:
                logger.warning(f"SMTP failed, code for {user.email}: {code} ({e})")
        else:
            logger.info(f"[NO SMTP] Password reset code for {user.email}: {code}")

        if email_sent:
            return JSONResponse(content={"ok": True, "message": "A reset code has been sent to your email."})
        # No email service configured or sending failed — return code directly
        return JSONResponse(content={"ok": True, "message": f"Your reset code is: {code}", "code": code})
    finally:
        db.close()


@app.post("/auth/reset-password")
def reset_password(body: ResetPasswordBody):
    """Verify reset code and set a new password."""
    from datetime import datetime, timedelta
    if len(body.new_password) < 4:
        return JSONResponse(status_code=400, content={"detail": "Password must be at least 4 characters"})
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.email == body.email.lower().strip()).first()
        if not user:
            return JSONResponse(status_code=400, content={"detail": "Invalid code or email"})

        cutoff = datetime.utcnow() - timedelta(minutes=15)
        reset = (
            db.query(PasswordReset)
            .filter(
                PasswordReset.user_id == user.id,
                PasswordReset.code == body.code.strip(),
                PasswordReset.used == 0,
                PasswordReset.created_at >= cutoff,
            )
            .order_by(PasswordReset.created_at.desc())
            .first()
        )
        if not reset:
            return JSONResponse(status_code=400, content={"detail": "Invalid or expired reset code"})

        reset.used = 1
        user.hashed_password = hash_password(body.new_password)
        db.commit()
        return JSONResponse(content={"ok": True, "message": "Password has been reset. You can now sign in."})
    finally:
        db.close()


@app.get("/auth/logout")
def do_logout():
    resp = RedirectResponse(url="/login", status_code=302)
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

    # ── Auto-promote admin via env var (for Render / headless deploy) ──
    # Set ADMIN_EMAIL + ADMIN_PASSWORD to auto-create & promote an admin account
    import os, logging
    logger = logging.getLogger("investai")
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if admin_email:
        user = db.query(User).filter(User.email == admin_email).first()
        if not user and admin_password:
            # Auto-create admin account if it doesn't exist
            user = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                name="Admin",
                is_admin=1,
                is_active=1,
            )
            db.add(user)
            db.commit()
            logger.info(f"Auto-created admin account: {admin_email}")
        elif user and not user.is_admin:
            user.is_admin = 1
            db.commit()
            logger.info(f"Auto-promoted {admin_email} to admin")

    db.close()

    from src.services.market_data import start_cache_warmer
    start_cache_warmer()

    # Stagger background scans to avoid memory spikes from concurrent fetching
    import time as _time

    def _delayed_value_scanner():
        _time.sleep(90)  # wait 90s after cache warmer starts
        from src.services.value_scanner import start_auto_scanner
        start_auto_scanner()

    def _delayed_trading_advisor():
        _time.sleep(180)  # wait 3 min after cache warmer starts
        from src.services.trading_advisor import start_trading_advisor
        start_trading_advisor()

    import threading
    threading.Thread(target=_delayed_value_scanner, daemon=True, name="delay-vs").start()
    threading.Thread(target=_delayed_trading_advisor, daemon=True, name="delay-ta").start()
