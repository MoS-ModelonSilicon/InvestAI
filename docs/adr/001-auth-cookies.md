# ADR-001: Cookie-Based JWT Authentication

**Date**: 2026-03-03  
**Status**: Accepted  
**Deciders**: Yaron Klein

## Context

The app needs user authentication. Two main approaches:
1. **localStorage tokens** — frontend sends `Authorization: Bearer <token>` header
2. **httponly cookies** — browser automatically sends cookie, server reads it

## Decision

Use **httponly cookie-based JWT authentication**.

## Rationale

- `httponly` cookies are not accessible to JavaScript → immune to XSS token theft
- `secure=True` ensures cookie only sent over HTTPS
- `samesite=lax` prevents CSRF on GET requests
- No need for the frontend to manage token storage or refresh logic
- Works seamlessly with the SPA architecture (no headers to set manually)

## Consequences

- **Good**: Stronger security baseline out of the box
- **Good**: Simpler frontend code (no token management)
- **Bad**: CSRF protection still needed for POST/PUT/DELETE (partially mitigated by `samesite=lax`)
- **Bad**: Harder to use from non-browser API clients (must manage cookies)

## Gotchas

- `SECRET_KEY` regenerates on restart if `INVESTAI_SECRET` env var not set → all sessions invalidated
- Must set `secure=True` even on localhost for HTTPS testing
- Cookie name is `investai_session` — don't change without updating `AuthMiddleware`
