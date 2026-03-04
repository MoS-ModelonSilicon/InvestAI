import os
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from src.database import get_db

# ── Config ────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("INVESTAI_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
COOKIE_NAME = "investai_session"

PUBLIC_PATHS = {"/login", "/auth/login", "/auth/register", "/auth/logout"}

# ── Password hashing ─────────────────────────────────────────
import bcrypt as _bcrypt


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────
def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── FastAPI dependency ────────────────────────────────────────
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Extract user from the JWT cookie. Returns the User ORM object."""
    from src.models import User  # local import to avoid circular

    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Middleware ────────────────────────────────────────────────
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Allow static files without auth
        if path.startswith("/static/"):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        payload = decode_token(cookie) if cookie else None

        if payload:
            request.state.user_id = int(payload["sub"])
            return await call_next(request)

        if path.startswith("/api/"):
            return Response(status_code=401, content="Unauthorized")

        return RedirectResponse(url="/login", status_code=302)
