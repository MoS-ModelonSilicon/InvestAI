# static/ — Frontend Gotchas

## Architecture

Single-page app using hidden `<section>` divs. Navigation is handled by `js/app.js` which shows/hides sections based on URL hash.

## XSS Prevention (CRITICAL)

**NEVER use `innerHTML` with user-supplied data.**

Bad:
```javascript
element.innerHTML = transaction.description;  // XSS!
```

Good:
```javascript
element.textContent = transaction.description;  // Safe
```

If you MUST use `innerHTML` (for structured content), sanitize first or ensure the data is from a trusted source (API-generated HTML, not user input).

Current known `innerHTML` occurrences are for:
- Chart tooltips (trusted data)
- Static HTML structures (no user data)
- Some legacy code that needs fixing (see SECURITY_AUDIT.md)

## Script Loading Order

Scripts in `index.html` must load in this order:
1. Chart.js (CDN)
2. `api.js` — fetch wrapper (used by all other modules)
3. `app.js` — navigation and page lifecycle
4. Domain modules (`dashboard.js`, `portfolio.js`, etc.) — order doesn't matter between these

## Theme System

- CSS variables defined in `style.css` (`:root` for light, `[data-theme="dark"]` for dark)
- Toggle button in `app.js`
- Every new component MUST work in both themes
- Test by toggling theme and checking all colors/borders/backgrounds

## API Calls

All API calls go through `fetchAPI()` in `api.js`:
- Auto-includes credentials (cookies)
- On 401 → redirects to `/login`
- Returns parsed JSON
- Loading spinners should be shown during fetch

## Adding a New Page

1. Add `<section id="pagename-page" class="page-section" style="display:none">` in `index.html`
2. Create `js/pagename.js` with init function
3. Add `<script>` tag in `index.html` (after `app.js`)
4. Register in `app.js` navigation map
5. Add sidebar nav item
