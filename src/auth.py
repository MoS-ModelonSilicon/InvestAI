import hashlib
import hmac
import os
import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

ACCESS_KEY = os.environ.get("INVESTAI_ACCESS_KEY", "intel2026")

_SECRET = os.environ.get("INVESTAI_SECRET", secrets.token_hex(32))
COOKIE_NAME = "investai_session"
SESSION_TTL = 60 * 60 * 24 * 7  # 7 days

PUBLIC_PATHS = {"/login", "/auth/login", "/auth/logout"}


def _make_token(timestamp: str) -> str:
    msg = f"{ACCESS_KEY}:{timestamp}".encode()
    return hmac.new(_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def create_session_cookie() -> tuple[str, str]:
    ts = str(int(time.time()))
    token = _make_token(ts)
    return f"{ts}:{token}", ts


def verify_session(cookie_value: str) -> bool:
    if not cookie_value:
        return False
    try:
        ts, token = cookie_value.split(":", 1)
        if time.time() - int(ts) > SESSION_TTL:
            return False
        return hmac.compare_digest(token, _make_token(ts))
    except Exception:
        return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in PUBLIC_PATHS:
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME, "")
        if verify_session(cookie):
            return await call_next(request)

        if path.startswith("/api/") or path.startswith("/static/"):
            return Response(status_code=401, content="Unauthorized")

        return RedirectResponse(url="/login", status_code=302)
