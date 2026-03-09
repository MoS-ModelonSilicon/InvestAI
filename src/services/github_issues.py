"""
GitHub Issues integration — creates issues from user suggestions.

Uses the GitHub REST API directly (no `gh` CLI dependency) so it works
on the server (Render) as well as local dev.

Required env vars:
  GITHUB_TOKEN — a PAT or fine-grained token with `issues: write` scope
  GITHUB_REPO  — owner/repo, e.g. "MoS-ModelonSilicon/InvestAI" (auto-detected from git remote if omitted)
"""

import logging
import os
import re
import subprocess

import requests

logger = logging.getLogger(__name__)

_GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_GITHUB_REPO = os.environ.get("GITHUB_REPO", "")

# Proxy for Intel network (same pattern as assistant.py)
_PROXIES: dict[str, str] = {}
_http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
_https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
if _http_proxy:
    _PROXIES["http"] = _http_proxy
if _https_proxy:
    _PROXIES["https"] = _https_proxy

if not _PROXIES and not (os.environ.get("RENDER") or os.environ.get("CI")):
    import socket

    try:
        socket.getaddrinfo("proxy-dmz.intel.com", 911, socket.AF_INET, socket.SOCK_STREAM)
        _PROXIES = {
            "http": "http://proxy-dmz.intel.com:911",
            "https": "http://proxy-dmz.intel.com:912",
        }
    except (socket.gaierror, OSError):
        pass


def _get_token() -> str:
    """Get GitHub token. Fallback: try `gh auth token` CLI."""
    token = _GITHUB_TOKEN
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _get_repo() -> str:
    """Get repo slug. Fallback: parse git remote."""
    if _GITHUB_REPO:
        return _GITHUB_REPO
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        # Parse https://github.com/owner/repo.git or git@github.com:owner/repo.git
        m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""


def is_configured() -> bool:
    """Check if GitHub Issues integration is available."""
    return bool(_get_token() and _get_repo())


# Label mapping: suggestion category → GitHub labels
_LABEL_MAP = {
    "feature": ["user-feedback", "feature-request", "enhancement"],
    "bug": ["user-feedback", "user-bug", "bug"],
    "improvement": ["user-feedback", "enhancement"],
    "content": ["user-feedback", "documentation"],
}


def create_issue(
    title: str,
    body: str,
    category: str = "feature",
    user_email: str = "",
) -> dict | None:
    """
    Create a GitHub Issue for a user suggestion.

    Returns {"url": "https://github.com/.../issues/123", "number": 123}
    or None on failure.
    """
    token = _get_token()
    repo = _get_repo()

    if not token or not repo:
        logger.warning("GitHub Issues not configured (missing token or repo)")
        return None

    labels = _LABEL_MAP.get(category, ["user-feedback", "enhancement"])

    # Build issue body with metadata
    full_body = f"""## User Suggestion

{body}

---

| Field | Value |
|-------|-------|
| **Category** | {category} |
| **Submitted by** | {user_email or "anonymous"} |
| **Source** | InvestAI Assistant / Suggestion Form |

*Auto-created by InvestAI suggestion system*"""

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": f"[{category}] {title}",
        "body": full_body,
        "labels": labels,
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            proxies=_PROXIES,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        issue_url = data.get("html_url", "")
        issue_number = data.get("number", 0)
        logger.info("Created GitHub Issue #%d: %s", issue_number, issue_url)
        return {"url": issue_url, "number": issue_number}
    except Exception as e:
        logger.exception("Failed to create GitHub Issue: %s", e)
        return None


def close_issue(issue_number: int) -> bool:
    """Close a GitHub Issue (e.g. when suggestion is marked 'done' or 'declined')."""
    token = _get_token()
    repo = _get_repo()
    if not token or not repo or not issue_number:
        return False

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.patch(
            url,
            headers=headers,
            json={"state": "closed"},
            proxies=_PROXIES,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Closed GitHub Issue #%d", issue_number)
        return True
    except Exception as e:
        logger.exception("Failed to close GitHub Issue #%d: %s", issue_number, e)
        return False


def reopen_issue(issue_number: int) -> bool:
    """Reopen a previously closed GitHub Issue."""
    token = _get_token()
    repo = _get_repo()
    if not token or not repo or not issue_number:
        return False

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.patch(
            url,
            headers=headers,
            json={"state": "open"},
            proxies=_PROXIES,
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("Reopened GitHub Issue #%d", issue_number)
        return True
    except Exception as e:
        logger.exception("Failed to reopen GitHub Issue #%d: %s", issue_number, e)
        return False


def add_comment(issue_number: int, comment: str) -> bool:
    """Add a comment to a GitHub Issue (e.g. admin notes update)."""
    token = _get_token()
    repo = _get_repo()
    if not token or not repo or not issue_number:
        return False

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.post(
            url,
            headers=headers,
            json={"body": comment},
            proxies=_PROXIES,
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.exception("Failed to comment on GitHub Issue #%d: %s", issue_number, e)
        return False
