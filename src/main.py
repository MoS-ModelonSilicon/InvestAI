from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.database import engine, get_db, Base
from src.models import Category, User, PasswordReset
from src.auth import (
    AuthMiddleware,
    COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_DAYS,
    create_access_token,
    hash_password,
    verify_password,
)
from src.routers import (
    categories,
    transactions,
    budgets,
    dashboard,
    profile,
    screener,
    recommendations,
    market,
    stock_detail,
    portfolio,
    news,
    comparison,
    alerts,
    education,
    calendar_router,
    israeli_funds,
    value_scanner,
    autopilot,
    smart_advisor,
    trading_advisor,
    picks_tracker,
    dca,
    admin,
)

import time as _time, logging as _logging

_log = _logging.getLogger(__name__)


def _init_db(retries: int = 3, delay: float = 2.0):
    """Create tables with retry for transient connection issues."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            _log.info("Database tables ready (attempt %d)", attempt)
            return
        except Exception as exc:
            _log.warning("DB init attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                _time.sleep(delay * attempt)
            else:
                _log.error("All DB init attempts failed — starting without tables")


_init_db()


# ── Auto-migrate: add missing columns/indexes to existing tables ──
def _auto_migrate():
    """Add columns and indexes introduced after initial deploy (safe to re-run)."""
    from sqlalchemy import inspect, text
    from src.database import _is_sqlite

    insp = inspect(engine)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        with engine.begin() as conn:
            if "is_admin" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0"))
            if "is_active" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"))
    # Add performance indexes
    with engine.begin() as conn:
        try:
            if _is_sqlite:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_user_id ON alerts (user_id)"))
            else:
                # PostgreSQL: CREATE INDEX IF NOT EXISTS is supported
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (date)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_alerts_user_id ON alerts (user_id)"))
        except Exception:
            pass  # Indexes already exist or table not yet created


_auto_migrate()

import os as _os

_is_production = _os.environ.get("RENDER") or _os.environ.get("PRODUCTION")
app = FastAPI(
    title="InvestAI",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ── Rate limiting ─────────────────────────────────────────────
_testing = _os.environ.get("TESTING") == "1"
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not _testing,  # disable rate limiting during pytest
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


app.add_middleware(SecurityHeadersMiddleware)
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


# ── Health / version check (public, no auth) ─────────────────
import subprocess as _sp

try:
    _GIT_SHA = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], timeout=3, text=True).strip()
except Exception:
    _GIT_SHA = "unknown"


@app.get("/health")
def health_check():
    """Public health endpoint — returns git commit for deploy verification."""
    from src.services.market_data import _warm_done, _cache

    # Show which of the 12 advisor combos are cached
    advisor_combos = {}
    for risk in ["balanced", "conservative", "aggressive"]:
        for period in ["1m", "3m", "6m", "1y"]:
            key = f"advisor:full:10000:{risk}:{period}"
            advisor_combos[f"{risk}/{period}"] = key in _cache

    return {
        "status": "ok",
        "version": _GIT_SHA,
        "cache_ready": _warm_done.is_set(),
        "cache_entries": len(_cache),
        "advisor_combos": advisor_combos,
    }


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
    email: EmailStr
    password: str
    name: str = ""


@app.post("/auth/register")
@limiter.limit("3/minute")
def do_register(body: RegisterBody, request: Request):
    if len(body.password) < 8:
        return JSONResponse(status_code=400, content={"detail": "Password must be at least 8 characters"})
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
            secure=True,
        )
        return resp
    finally:
        db.close()


@app.post("/auth/login")
@limiter.limit("5/minute")
def do_login(body: LoginBody, request: Request):
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
            secure=True,
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
@limiter.limit("3/minute")
def forgot_password(body: ForgotPasswordBody, request: Request):
    """Generate a 6-digit reset code. Sends via email if SMTP is configured, otherwise logs it."""
    import secrets as _secrets, os, logging

    logger = logging.getLogger("investai")
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.email == body.email.lower().strip()).first()
        # Always return OK to not leak whether email exists
        if not user:
            return JSONResponse(
                content={"ok": True, "message": "If that email is registered, a reset code has been sent."}
            )

        code = f"{_secrets.randbelow(1000000):06d}"
        # Store hashed code — never plaintext in DB
        from src.auth import hash_password as _hash_pw

        reset = PasswordReset(user_id=user.id, code=_hash_pw(code))
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
        # No email service — log code but never return it in response
        return JSONResponse(content={"ok": True, "message": "If that email is registered, a reset code has been sent."})
    finally:
        db.close()


@app.post("/auth/reset-password")
def reset_password(body: ResetPasswordBody):
    """Verify reset code and set a new password."""
    from datetime import datetime, timedelta

    if len(body.new_password) < 8:
        return JSONResponse(status_code=400, content={"detail": "Password must be at least 8 characters"})
    db: Session = next(get_db())
    try:
        user = db.query(User).filter(User.email == body.email.lower().strip()).first()
        if not user:
            return JSONResponse(status_code=400, content={"detail": "Invalid code or email"})

        cutoff = datetime.utcnow() - timedelta(minutes=15)
        # Reset codes are stored hashed — fetch all recent unused codes and verify
        from src.auth import verify_password as _verify_pw

        candidates = (
            db.query(PasswordReset)
            .filter(
                PasswordReset.user_id == user.id,
                PasswordReset.used == 0,
                PasswordReset.created_at >= cutoff,
            )
            .order_by(PasswordReset.created_at.desc())
            .limit(5)
            .all()
        )
        reset = None
        for candidate in candidates:
            if _verify_pw(body.code.strip(), candidate.code):
                reset = candidate
                break
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
        if admin_password and len(admin_password) < 8:
            logger.warning("ADMIN_PASSWORD is too short (min 8 chars) — skipping auto-create")
            admin_password = ""
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

    if not _testing:
        # Restore cached data from DB before starting scanners
        # This lets the API serve last-known data immediately
        try:
            from src.services.persistence import restore_all_caches

            restore_all_caches()
        except Exception:
            import logging

            logging.getLogger("investai").exception("Failed to restore caches from DB")

        from src.services.market_data import start_cache_warmer

        start_cache_warmer()

        # Single background scheduler handles all periodic scans
        # (value scanner, trading advisor) on fixed server-side intervals
        from src.services.background_scheduler import start_background_scheduler

        start_background_scheduler()
