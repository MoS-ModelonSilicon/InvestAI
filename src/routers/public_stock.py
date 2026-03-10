"""Public SEO-friendly stock pages — no authentication required.

Serves:
  GET /stocks/{symbol}       → server-rendered HTML with JSON-LD
  GET /api/public/stock/{symbol} → lightweight JSON for crawlers / link previews
"""

from __future__ import annotations

import html
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from src.services.stock_detail import get_stock_detail, get_price_history
from src.services.screener import _build_risk_analysis, _build_analyst_view, _compute_signal

_log = logging.getLogger(__name__)
router = APIRouter(tags=["public-stock"])
_pool = ThreadPoolExecutor(max_workers=3)


# ── helpers ──────────────────────────────────────────────────
def _safe(val: Any, fallback: str = "N/A") -> str:
    """Escape a value for safe HTML embedding."""
    if val is None:
        return fallback
    return html.escape(str(val))


def _fmt_number(val: Any, decimals: int = 2) -> str:
    """Format a number with commas, or return N/A."""
    if val is None:
        return "N/A"
    try:
        n = float(val)
        if abs(n) >= 1_000_000_000:
            return f"${n / 1_000_000_000:.1f}B"
        if abs(n) >= 1_000_000:
            return f"${n / 1_000_000:.1f}M"
        if abs(n) >= 1_000:
            return f"${n:,.0f}"
        return f"${n:,.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):+.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def _sparkline_svg(closes: list[float], width: int = 280, height: int = 60) -> str:
    """Return a tiny inline SVG sparkline for the price chart."""
    if not closes or len(closes) < 2:
        return ""
    mn, mx = min(closes), max(closes)
    rng = mx - mn or 1
    step = width / (len(closes) - 1)
    points = " ".join(
        f"{round(i * step, 1)},{round(height - (v - mn) / rng * (height - 4) - 2, 1)}" for i, v in enumerate(closes)
    )
    color = "#22c55e" if closes[-1] >= closes[0] else "#ef4444"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


# ── public JSON API ──────────────────────────────────────────
@router.get("/api/public/stock/{symbol}")
def public_stock_json(symbol: str):
    """Lightweight public stock data — no auth required."""
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(400, "Invalid symbol")
    info = get_stock_detail(sym)
    if not info:
        raise HTTPException(404, f"No data for {sym}")

    sig = _compute_signal(info)
    risk = _build_risk_analysis(info)

    return JSONResponse(
        content={
            "symbol": sym,
            "name": info.get("name", sym),
            "price": info.get("price"),
            "change_pct": info.get("change_pct"),
            "market_cap": info.get("market_cap"),
            "pe_ratio": info.get("pe_ratio"),
            "dividend_yield": info.get("dividend_yield"),
            "week52_high": info.get("week52_high"),
            "week52_low": info.get("week52_low"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "signal": sig.get("signal"),
            "signal_reason": sig.get("reason"),
            "risk_level": risk.get("level") if risk else None,
        },
        headers={"Cache-Control": "public, max-age=300"},
    )


# ── server-rendered stock page ───────────────────────────────
@router.get("/stocks/{symbol}", response_class=HTMLResponse)
def public_stock_page(symbol: str):
    """SEO-optimised HTML stock page with JSON-LD structured data."""
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(400, "Invalid symbol")

    # Fetch data in parallel
    info_future = _pool.submit(get_stock_detail, sym)
    history_future = _pool.submit(get_price_history, sym, "6mo", "1d")

    info = info_future.result(timeout=15)
    if not info:
        raise HTTPException(404, f"No data for {sym}")

    sig = _compute_signal(info)
    risk = _build_risk_analysis(info)
    analyst = _build_analyst_view(info)
    history = history_future.result(timeout=15)

    name = info.get("name", sym)
    price = info.get("price")
    change_pct = info.get("change_pct")
    market_cap = info.get("market_cap")
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    pe = info.get("pe_ratio")
    dy = info.get("dividend_yield")
    w52_hi = info.get("week52_high")
    w52_lo = info.get("week52_low")
    beta = info.get("beta")
    avg_vol = info.get("avg_volume")
    eps = info.get("eps")

    sparkline = _sparkline_svg(history.get("close", [])[-120:]) if history else ""

    # Change direction
    is_up = (change_pct or 0) >= 0
    change_color = "#22c55e" if is_up else "#ef4444"
    change_arrow = "▲" if is_up else "▼"

    signal = sig.get("signal", "Hold")
    signal_reason = sig.get("reason", "")
    signal_color = {"Buy": "#22c55e", "Avoid": "#ef4444"}.get(signal, "#eab308")
    risk_level = risk.get("level", "Medium") if risk else "Medium"
    risk_color = {"Low": "#22c55e", "High": "#ef4444"}.get(risk_level, "#eab308")

    # JSON-LD structured data for Google
    json_ld = {
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": f"{name} ({sym})",
        "description": f"Real-time stock analysis for {name} ({sym}). Current price ${price}, signal: {signal}.",
        "url": f"https://investai.app/stocks/{sym}",
        "provider": {"@type": "Organization", "name": "InvestAI", "url": "https://investai.app"},
        "category": sector or "Equity",
    }
    json_ld_str = json.dumps(json_ld, ensure_ascii=False)

    # Analyst targets section
    analyst_html = ""
    if analyst:
        low = analyst.get("low")
        median = analyst.get("median")
        high = analyst.get("high")
        consensus = analyst.get("consensus", "")
        if median:
            upside = round((median - price) / price * 100, 1) if price else 0
            analyst_html = f"""
            <div class="card">
              <h3>Analyst Targets</h3>
              <div class="stat-row">
                <span class="label">Low</span><span class="value">{_fmt_number(low)}</span>
              </div>
              <div class="stat-row">
                <span class="label">Median</span><span class="value">{_fmt_number(median)}</span>
              </div>
              <div class="stat-row">
                <span class="label">High</span><span class="value">{_fmt_number(high)}</span>
              </div>
              <div class="stat-row">
                <span class="label">Consensus</span><span class="value">{_safe(consensus)}</span>
              </div>
              <div class="stat-row">
                <span class="label">Upside</span>
                <span class="value" style="color:{"#22c55e" if upside > 0 else "#ef4444"}">{upside:+.1f}%</span>
              </div>
            </div>"""

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_safe(name)} ({sym}) Stock Price, Analysis &amp; Signal | InvestAI</title>
<meta name="description" content="Live {_safe(name)} ({sym}) stock analysis: price ${_safe(price)}, signal {signal}. Key metrics, risk assessment, analyst targets and 6-month chart.">
<meta name="keywords" content="{sym}, {_safe(name)}, stock price, stock analysis, {_safe(sector)}, investing">
<link rel="canonical" href="https://investai.app/stocks/{sym}">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:title" content="{_safe(name)} ({sym}) — ${_safe(price)} | InvestAI">
<meta property="og:description" content="AI-powered stock analysis for {_safe(name)}. Signal: {signal}. Get real-time insights.">
<meta property="og:url" content="https://investai.app/stocks/{sym}">
<meta property="og:site_name" content="InvestAI">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{_safe(name)} ({sym}) — ${_safe(price)}">
<meta name="twitter:description" content="Signal: {signal}. {_safe(signal_reason)[:100]}">

<!-- JSON-LD Structured Data -->
<script type="application/ld+json">{json_ld_str}</script>

<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f1117;color:#e4e4e7;min-height:100vh}}
a{{color:#818cf8;text-decoration:none}}
a:hover{{text-decoration:underline}}

/* Header */
.topbar{{background:#1a1c2e;border-bottom:1px solid rgba(255,255,255,.06);padding:12px 24px;display:flex;align-items:center;justify-content:space-between}}
.topbar .logo{{display:flex;align-items:center;gap:8px;color:#818cf8;font-weight:700;font-size:1.15rem}}
.topbar .logo span{{color:#e4e4e7}}
.topbar .cta{{background:#818cf8;color:#fff;padding:8px 20px;border-radius:8px;font-weight:600;font-size:.9rem;border:none;cursor:pointer;transition:background .2s}}
.topbar .cta:hover{{background:#6366f1;text-decoration:none}}

/* Hero */
.hero{{max-width:1100px;margin:0 auto;padding:32px 24px 0}}
.breadcrumb{{font-size:.8rem;color:#8b8fa3;margin-bottom:16px}}
.breadcrumb a{{color:#818cf8}}
.hero-header{{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:20px;margin-bottom:24px}}
.hero-left h1{{font-size:1.75rem;margin-bottom:6px}}
.hero-left .sector{{color:#8b8fa3;font-size:.9rem}}
.price-block{{text-align:right}}
.price{{font-size:2rem;font-weight:700}}
.change{{font-size:1.1rem;font-weight:600}}

/* Signal badge */
.signal-badge{{display:inline-block;padding:6px 16px;border-radius:20px;font-weight:700;font-size:.9rem;margin-top:8px}}

/* Content grid */
.content{{max-width:1100px;margin:0 auto;padding:24px;display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:768px){{.content{{grid-template-columns:1fr}}.hero-header{{flex-direction:column}}.price-block{{text-align:left}}}}

.card{{background:#1a1c2e;border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:20px}}
.card h3{{font-size:1rem;color:#818cf8;margin-bottom:14px;font-weight:600}}
.card.full{{grid-column:1/-1}}
.stat-row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04)}}
.stat-row:last-child{{border-bottom:none}}
.stat-row .label{{color:#8b8fa3;font-size:.88rem}}
.stat-row .value{{font-weight:600;font-size:.88rem}}

/* Chart */
.chart-card{{grid-column:1/-1}}
.chart-card svg{{width:100%;height:auto;max-height:100px}}

/* CTA banner */
.cta-banner{{max-width:1100px;margin:32px auto;padding:0 24px}}
.cta-box{{background:linear-gradient(135deg,#1e1b4b,#312e81);border:1px solid rgba(129,140,248,.2);border-radius:16px;padding:40px;text-align:center}}
.cta-box h2{{font-size:1.4rem;margin-bottom:10px}}
.cta-box p{{color:#a5b4fc;margin-bottom:20px;font-size:.95rem}}
.cta-box .btn{{display:inline-block;background:#818cf8;color:#fff;padding:12px 32px;border-radius:8px;font-weight:700;font-size:1rem;transition:background .2s}}
.cta-box .btn:hover{{background:#6366f1;text-decoration:none}}

/* Footer */
.footer{{max-width:1100px;margin:0 auto;padding:24px;text-align:center;color:#4a4d5e;font-size:.78rem;border-top:1px solid rgba(255,255,255,.04)}}

/* Screening links */
.related{{max-width:1100px;margin:0 auto;padding:0 24px 24px}}
.related h3{{font-size:.95rem;color:#8b8fa3;margin-bottom:12px}}
.pill-list{{display:flex;flex-wrap:wrap;gap:8px}}
.pill{{background:#1a1c2e;border:1px solid rgba(255,255,255,.08);padding:6px 14px;border-radius:20px;font-size:.82rem;color:#e4e4e7;transition:border-color .2s}}
.pill:hover{{border-color:#818cf8;text-decoration:none}}
</style>
</head>
<body>

<!-- Top bar -->
<nav class="topbar">
  <a href="/" class="logo">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
    <span>InvestAI</span>
  </a>
  <a href="/login" class="cta">Sign Up Free</a>
</nav>

<!-- Hero -->
<section class="hero">
  <div class="breadcrumb"><a href="/">Home</a> / <a href="/stocks/{sym}">{sym}</a></div>
  <div class="hero-header">
    <div class="hero-left">
      <h1>{_safe(name)} <span style="color:#8b8fa3;font-weight:400">({sym})</span></h1>
      <div class="sector">{_safe(sector)}{(" · " + _safe(industry)) if industry else ""}</div>
      <div class="signal-badge" style="background:{signal_color}22;color:{signal_color};border:1px solid {signal_color}44">
        {signal} — {_safe(signal_reason)[:80]}
      </div>
    </div>
    <div class="price-block">
      <div class="price">${_safe(price)}</div>
      <div class="change" style="color:{change_color}">{change_arrow} {_fmt_pct(change_pct)}</div>
    </div>
  </div>
</section>

<!-- 6-month sparkline chart -->
{'<div class="content"><div class="chart-card card"><h3>6-Month Price Chart</h3>' + sparkline + "</div></div>" if sparkline else ""}

<!-- Key stats grid -->
<div class="content">
  <div class="card">
    <h3>Key Statistics</h3>
    <div class="stat-row"><span class="label">Market Cap</span><span class="value">{_fmt_number(market_cap)}</span></div>
    <div class="stat-row"><span class="label">P/E Ratio</span><span class="value">{_safe(pe)}</span></div>
    <div class="stat-row"><span class="label">EPS</span><span class="value">{_safe(eps)}</span></div>
    <div class="stat-row"><span class="label">Dividend Yield</span><span class="value">{_fmt_pct(dy) if dy else "N/A"}</span></div>
    <div class="stat-row"><span class="label">Beta</span><span class="value">{_safe(beta)}</span></div>
    <div class="stat-row"><span class="label">Avg Volume</span><span class="value">{f"{int(avg_vol):,}" if avg_vol else "N/A"}</span></div>
  </div>

  <div class="card">
    <h3>52-Week Range</h3>
    <div class="stat-row"><span class="label">52-Week Low</span><span class="value">{_fmt_number(w52_lo)}</span></div>
    <div class="stat-row"><span class="label">52-Week High</span><span class="value">{_fmt_number(w52_hi)}</span></div>
    <div class="stat-row"><span class="label">Current vs High</span>
      <span class="value" style="color:{change_color}">{_fmt_pct(((price or 0) / w52_hi - 1) * 100) if w52_hi and price else "N/A"}</span>
    </div>
    <div class="stat-row">
      <span class="label">Risk Level</span>
      <span class="value" style="color:{risk_color}">{_safe(risk_level)}</span>
    </div>
  </div>

  {analyst_html}
</div>

<!-- CTA Banner -->
<div class="cta-banner">
  <div class="cta-box">
    <h2>Unlock Full AI-Powered Analysis</h2>
    <p>Get personalised trade signals, portfolio tracking, AI advisor, DCA planner, and more — 100% free.</p>
    <a href="/login" class="btn">Create Free Account →</a>
  </div>
</div>

<!-- Related stocks (internal linking for SEO) -->
<div class="related">
  <h3>Popular Stocks</h3>
  <div class="pill-list">
    <a href="/stocks/AAPL" class="pill">AAPL</a>
    <a href="/stocks/MSFT" class="pill">MSFT</a>
    <a href="/stocks/GOOGL" class="pill">GOOGL</a>
    <a href="/stocks/AMZN" class="pill">AMZN</a>
    <a href="/stocks/TSLA" class="pill">TSLA</a>
    <a href="/stocks/NVDA" class="pill">NVDA</a>
    <a href="/stocks/META" class="pill">META</a>
    <a href="/stocks/JPM" class="pill">JPM</a>
    <a href="/stocks/V" class="pill">V</a>
    <a href="/stocks/JNJ" class="pill">JNJ</a>
    <a href="/stocks/INTC" class="pill">INTC</a>
    <a href="/stocks/AMD" class="pill">AMD</a>
  </div>
</div>

<footer class="footer">
  <p>© 2025 InvestAI · Data provided for informational purposes only · Not financial advice</p>
  <p style="margin-top:6px"><a href="/">Dashboard</a> · <a href="/login">Sign In</a></p>
</footer>

</body>
</html>"""

    return HTMLResponse(content=page_html, headers={"Cache-Control": "public, max-age=300"})


# ── sitemap & robots for SEO crawling ────────────────────────
@router.get("/sitemap.xml")
def sitemap():
    """Dynamic sitemap with all public stock pages."""
    from starlette.responses import Response as _Resp

    from src.services.market_data import ALL_UNIVERSE

    base = "https://investai.app"
    urls = [
        f"  <url><loc>{base}/stocks/{sym}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>"
        for sym in sorted(ALL_UNIVERSE)
    ]
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{base}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n"
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return _Resp(content=xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/robots.txt")
def robots():
    """Allow crawlers to find stock pages and sitemap."""
    from starlette.responses import Response as _Resp

    txt = (
        "User-agent: *\n"
        "Allow: /stocks/\n"
        "Allow: /login\n"
        "Disallow: /api/\n"
        "Allow: /api/public/\n"
        "Sitemap: https://investai.app/sitemap.xml\n"
    )
    return _Resp(content=txt, media_type="text/plain", headers={"Cache-Control": "public, max-age=86400"})
