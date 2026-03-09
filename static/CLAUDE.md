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
3. Domain modules (`dashboard.js`, `portfolio.js`, etc.) — order doesn't matter between these
4. `tour.js` — guided tour (must load before `app.js` so `window.startTour` is defined)
5. `help-drawer.js` — help drawer (must load before `app.js` so sidebar button handler is bound)
6. `app.js` — navigation and page lifecycle (calls `_trackPageVisit` from tour.js)

## Onboarding System

Three integrated features for new user discovery:

1. **Guided Tour** (`tour.js`) — 10-step spotlight walkthrough. Auto-triggers once on first login via `localStorage.investai_tour_completed`. Re-trigger: `window.startTour()` or Help drawer button. Keyboard: →/Enter (next), ← (back), Esc (close).

2. **Help Drawer** (`help-drawer.js`) — Right slide-out panel opened by sidebar "? Help & Tour" button (`#help-drawer-btn`). Contains Quick Start checklist (8 items with progress bar, persisted in `localStorage.investai_checklist`), feature guide cards with click-to-navigate, and Hidden Gems pro tips.

3. **Feature Hint Dots** (`tour.js` bottom) — Pulsing purple dots on sidebar nav items for unvisited pages. Tracked in `localStorage.investai_visited_pages`. `navigateTo()` in `app.js` calls `window._trackPageVisit(page)` to remove dots on visit.

To reset all onboarding state for testing:
```javascript
localStorage.removeItem('investai_tour_completed');
localStorage.removeItem('investai_visited_pages');
localStorage.removeItem('investai_checklist');
location.reload();
```

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
