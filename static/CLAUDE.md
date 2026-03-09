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
6. `assistant.js` — AI chat widget (self-contained, loads after app.js is fine)
7. `app.js` — navigation and page lifecycle (calls `_trackPageVisit` from tour.js)

## AI Chat Widget (`assistant.js`)

Floating chat widget in bottom-right corner. Self-contained — no dependencies on other modules.

- **FAB button** with chat icon → toggles 380px chat panel
- **SSE streaming** — connects to `POST /api/assistant/chat` with `text/event-stream`
- **Model badges** — shows ⚡ gpt-5-nano or 🧠 o3 based on routing decision
- **Tool indicators** — shows contextual labels for all 16 tools (e.g. "Adding AAPL to portfolio...", "Analyzing NVDA...", "Loading budget status...")
- **Navigation handling** — SSE `navigate` events trigger `navLink.click()` to switch pages
- **Suggestion form** — accessible via 💡 button in header
- **20-message context** — last 20 messages sent as conversation history
- **Markdown-lite rendering** — bold, inline code, code blocks, line breaks
- **Mobile responsive** — full-width bottom sheet on screens ≤480px

## Onboarding System

Three integrated features for new user discovery:

1. **Guided Tour** (`tour.js`) — 11-step spotlight walkthrough starting with Risk Profile. Auto-triggers once on first login via `localStorage.investai_tour_completed`. Re-trigger: `window.startTour()` or Help drawer button. Keyboard: →/Enter (next), ← (back), Esc (close).

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

## Trading Advisor Detail Modal (`advisor.js`)

The detail modal (opened by clicking a pick card) renders a full visual decision breakdown:

### Chart Architecture
- **6 Chart.js instances** managed via module-level variables: `_taPriceChart`, `_taRsiChart`, `_taMacdChart`, `_taStochChart`, `_taAdxChart`, `_taWaterfallChart`
- Each is destroyed before recreation to avoid canvas reuse errors
- `_drawAllTACharts(data)` calls all 6 draw functions

### State Management
- `_taCurrentData` — stores the last API response so overlay/mode toggling can re-render without refetching
- `_taChartMode` — `'candle'` or `'line'` — controls main price chart type
- `_taOverlayToggles` — `{sma, bollinger, vwap, keltner, sar, ichimoku}` boolean map
- `_taDetailLoading` — debounce flag to prevent double-click double-fetches
- Toggling an overlay or chart mode calls `_renderTADetailModal(_taCurrentData)` which rebuilds the full modal

### Candlestick Rendering
Uses Chart.js floating bars (not a candlestick plugin):
- **Body**: `type:'bar'` with data `[open, close]` — green if close ≥ open, red otherwise
- **Wicks**: Second `type:'bar'` dataset with data `[low, high]` and `barPercentage: 0.08`
- `borderSkipped: false` is required for floating bars to render correctly

### Pattern Annotations
- Chart patterns (`viz_points`) rendered as connected point markers with dashed lines
- Candlestick patterns rendered as triangle markers at detection indices (upward for bullish, inverted for bearish)
- Hover tooltip uses `afterBody` callback to show candlestick pattern names at the hovered index

### Decision Waterfall
- One horizontal bar per signal from `data.decision_breakdown[]`
- Green bars = positive weighted_score (bullish), Red = negative (bearish)
- Bar width scaled: `Math.abs(weighted_score) / 0.5 * 100` (0.5 = full width)
