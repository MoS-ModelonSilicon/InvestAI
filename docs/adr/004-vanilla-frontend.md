# ADR-004: Vanilla JS Frontend (No Frameworks)

**Date**: 2026-03-03  
**Status**: Accepted  
**Deciders**: Yaron Klein

## Context

Needed a frontend for the investment platform. Options: React, Vue, vanilla JS.

## Decision

Use **vanilla HTML/CSS/JS**. No frontend frameworks.

## Rationale

- Zero build step — edit and refresh
- No node_modules, no webpack/vite config
- Simpler deployment (static files served by FastAPI)
- Full control over DOM manipulation
- Smaller bundle size for free-tier hosting (512MB RAM)

## Implementation

- `static/index.html`: All pages as hidden `<section>` divs (SPA pattern)
- `static/js/app.js`: Navigation — shows/hides sections, manages URL hash
- `static/js/api.js`: `fetchAPI()` wrapper with auto 401→login redirect
- 28 JS modules, one per feature domain
- Chart.js 4.x for all visualizations, loaded from CDN

## Consequences

- **Good**: No build pipeline, instant deploys, tiny footprint
- **Bad**: More boilerplate for DOM manipulation
- **Bad**: No component reuse system (we use function-based patterns instead)
- **Bad**: Global namespace (mitigated by module pattern in each JS file)

## Gotchas

- **XSS**: Must use `textContent` not `innerHTML` for any user-supplied data
- **Navigation**: All page switching goes through `app.js` — don't manipulate `display` directly
- **Script order**: `<script>` tags in `index.html` must load in dependency order (api.js first)
- **Theme**: Both dark and light themes must be tested — CSS variables in `style.css`
