"""
Playwright E2E test fixtures.

Starts a live uvicorn server (or uses --live-url for a deployed site),
authenticates via the login page, and hands each test a logged-in
Playwright page pointed at the real site.

Usage:
    pytest tests/                                  # local server on :8091
    pytest tests/ --live-url https://investai-utho.onrender.com   # deployed site
"""

import os
import subprocess
import sys
import time
import socket

import pytest
from playwright.sync_api import Page, BrowserContext

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

# Detect if we need Intel corporate proxy (local dev) or not (CI/GitHub Actions)
_NEED_PROXY = os.environ.get("USE_INTEL_PROXY") == "1" and not os.environ.get("CI")
_PROXY_HTTP = "http://proxy-dmz.intel.com:911" if _NEED_PROXY else None
_PROXY_HTTPS = "http://proxy-dmz.intel.com:912" if _NEED_PROXY else None
_PROXIES = {"http": _PROXY_HTTP, "https": _PROXY_HTTPS} if _NEED_PROXY else None

LOCAL_URL = "http://127.0.0.1:8091"
TEST_USER_EMAIL = "testuser@e2e.local"
TEST_USER_PASSWORD = "TestPass123"
TEST_USER_NAME = "E2E Tester"
SERVER_STARTUP_TIMEOUT = 30  # seconds


def pytest_addoption(parser):
    parser.addoption(
        "--live-url",
        action="store",
        default=None,
        help="URL of the deployed site to test (e.g. https://investai-utho.onrender.com). "
             "When set, skips local server startup.",
    )


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def _live_server(request):
    """Start the FastAPI app on port 8091, or use --live-url if provided."""
    live_url = request.config.getoption("--live-url")
    if live_url:
        yield live_url.rstrip("/")
        return

    if _port_is_open(8091):
        yield LOCAL_URL
        return

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.main:app",
            "--host", "127.0.0.1",
            "--port", "8091",
        ],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + SERVER_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _port_is_open(8091):
            break
        time.sleep(0.3)
    else:
        proc.kill()
        raise RuntimeError("Server did not start within timeout")

    yield LOCAL_URL
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def is_remote(request) -> bool:
    """True when testing a remote deployed site (not localhost)."""
    return request.config.getoption("--live-url") is not None


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Chromium launch args — use proxy for CDN but bypass for localhost."""
    return {
        "args": [
            "--proxy-bypass-list=127.0.0.1;localhost;<-loopback>",
        ]
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Playwright browser-context options (session-wide)."""
    opts = {"viewport": {"width": 1280, "height": 1024}}
    if _NEED_PROXY:
        opts["proxy"] = {
            "server": "http://proxy-dmz.intel.com:912",
            "bypass": "127.0.0.1,localhost",
        }
    return opts


@pytest.fixture(scope="session", autouse=True)
def _wake_remote_server(request, _live_server):
    """If targeting a remote Render site, ping it to wake it from cold sleep."""
    live_url = request.config.getoption("--live-url")
    if not live_url:
        return
    import requests as _req
    for attempt in range(6):  # up to ~3 min of retries
        try:
            r = _req.get(f"{live_url.rstrip('/')}/login", proxies=_PROXIES, timeout=60)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(30)
    raise RuntimeError(f"Remote site {live_url} did not wake up after retries")


@pytest.fixture()
def authenticated_page(page: Page, live_url: str) -> Page:
    """Register (if needed) and log in a test user, returning a page on the dashboard."""
    import requests
    # Use proxy for remote sites when behind Intel proxy, skip for local
    px = _PROXIES if "127.0.0.1" not in live_url and "localhost" not in live_url else None
    # Ensure the test user exists (ignore 400 if already registered)
    for _ in range(3):
        try:
            requests.post(
                f"{live_url}/auth/register",
                json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD, "name": TEST_USER_NAME},
                proxies=px,
                timeout=60,
            )
            break
        except Exception:
            time.sleep(5)
    page.goto(f"{live_url}/login", wait_until="domcontentloaded", timeout=120_000)
    page.fill("#login-email", TEST_USER_EMAIL)
    page.fill("#login-password", TEST_USER_PASSWORD)
    page.click("#login-btn")
    page.wait_for_url(f"{live_url}/", timeout=120_000)
    page.wait_for_load_state("domcontentloaded")
    return page


@pytest.fixture(scope="session")
def live_url(_live_server: str) -> str:
    return _live_server


def _api_session(base_url: str, email: str, password: str, name: str = "Test"):
    """Register + login via API. Returns (requests.Session, proxies_dict)."""
    import requests as _req
    px = _PROXIES if "127.0.0.1" not in base_url and "localhost" not in base_url else None
    s = _req.Session()
    if px:
        s.proxies.update(px)
    s.post(f"{base_url}/auth/register",
           json={"email": email, "password": password, "name": name}, timeout=30)
    resp = s.post(f"{base_url}/auth/login",
                  json={"email": email, "password": password}, timeout=30)
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return s
