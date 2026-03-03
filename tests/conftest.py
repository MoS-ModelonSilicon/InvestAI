"""
Playwright E2E test fixtures.

Starts a live uvicorn server, authenticates via the login page,
and hands each test a logged-in Playwright page pointed at the real site.
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

BASE_URL = "http://127.0.0.1:8091"
ACCESS_KEY = "intel2026"
SERVER_STARTUP_TIMEOUT = 15  # seconds


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def _live_server():
    """Start the FastAPI app on port 8091 for the entire test session."""
    if _port_is_open(8091):
        yield BASE_URL
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

    yield BASE_URL
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Chromium launch args — bypass proxy for localhost."""
    return {
        "args": [
            "--no-proxy-server",
            "--proxy-bypass-list=<-loopback>",
        ]
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Playwright browser-context options (session-wide)."""
    return {
        "viewport": {"width": 1280, "height": 1024},
        "proxy": {"server": "direct://", "bypass": "127.0.0.1,localhost"},
    }


@pytest.fixture()
def authenticated_page(page: Page, live_url: str) -> Page:
    """Navigate to the site and log in, returning a page on the dashboard."""
    page.goto(f"{live_url}/login", wait_until="domcontentloaded")
    page.fill("#access-key", ACCESS_KEY)
    page.click("#login-btn")
    page.wait_for_url(f"{live_url}/", timeout=15_000)
    page.wait_for_load_state("domcontentloaded")
    return page


@pytest.fixture(scope="session")
def live_url(_live_server: str) -> str:
    return _live_server
