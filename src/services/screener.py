from typing import Optional
import logging
import threading

from src.services.market_data import (
    fetch_batch,
    STOCK_UNIVERSE,
    ETF_UNIVERSE,
    ALL_UNIVERSE,
    KNOWN_NAMES,
    SEARCH_ALIASES,
    _ALIAS_TO_SYMBOL,
    format_market_cap,
)

logger = logging.getLogger(__name__)

# ── Pre-computed screener snapshot ───────────────────────────
# Built by refresh_screener_snapshot() after the cache warmer
# finishes, and restored from the DB on startup.  screen_instruments()
# reads from this list so every query is an instant in-memory filter
# instead of a slow fetch_batch + API call.
_snapshot_lock = threading.Lock()
_screener_snapshot: list[dict] = []


def _compute_signal(d: dict) -> dict:
    """Compute a Buy/Hold/Avoid signal with a plain-English reason."""
    points = 0
    reasons = []
    asset = d.get("asset_type", "Stock")

    rec = (d.get("recommendation") or "").lower().replace("_", " ")
    if rec in ("strong buy", "strongbuy"):
        points += 3
        reasons.append("analysts strongly recommend buying")
    elif rec == "buy":
        points += 2
        reasons.append("analysts rate it a buy")
    elif rec == "hold":
        points += 0
        reasons.append("analysts say hold")
    elif rec in ("sell", "underperform", "strong sell"):
        points -= 3
        reasons.append("analysts recommend selling")

    if asset == "Stock":
        pe = d.get("pe_ratio")
        if pe is not None:
            if pe < 15:
                points += 1
                reasons.append(f"low P/E ({pe:.1f}) suggests good value")
            elif pe > 40:
                points -= 1
                reasons.append(f"high P/E ({pe:.1f}) means premium pricing")

        div = d.get("dividend_yield")
        if div is not None and div > 2:
            points += 1
            reasons.append(f"{div:.1f}% dividend yield for passive income")

        beta = d.get("beta")
        if beta is not None:
            if beta < 0.8:
                reasons.append("low volatility — steadier price movement")
            elif beta > 1.5:
                points -= 1
                reasons.append("high volatility — bigger price swings")

        yc = d.get("year_change")
        if yc is not None:
            if yc > 20:
                points += 1
                reasons.append(f"up {yc:.0f}% over the past year")
            elif yc < -20:
                points -= 1
                reasons.append(f"down {abs(yc):.0f}% over the past year")
    else:
        er = d.get("expense_ratio")
        if er is not None and er < 0.2:
            points += 1
            reasons.append(f"very low expense ratio ({er:.2f}%)")
        elif er is not None and er > 0.75:
            points -= 1
            reasons.append(f"high expense ratio ({er:.2f}%) eats into returns")

        div = d.get("dividend_yield")
        if div is not None and div > 2:
            points += 1
            reasons.append(f"{div:.1f}% distribution yield")

        ta = d.get("total_assets")
        if ta and ta > 10e9:
            points += 1
            reasons.append("large, well-established fund")
        elif ta and ta < 500e6:
            reasons.append("smaller fund — less liquidity")

        ret5 = d.get("five_year_return")
        ret3 = d.get("three_year_return")
        if ret5 is not None and ret5 > 10:
            points += 1
            reasons.append(f"{ret5:.1f}% avg annual return over 5 years")
        elif ret3 is not None and ret3 > 8:
            points += 1
            reasons.append(f"{ret3:.1f}% avg annual return over 3 years")

    if points >= 2:
        signal = "Buy"
    elif points >= 0:
        signal = "Hold"
    else:
        signal = "Avoid"

    if not reasons:
        reasons.append("limited data available for analysis")

    return {
        "signal": signal,
        "reason": reasons[0].capitalize() + ("" if len(reasons) < 2 else f"; {reasons[1]}"),
    }


def _build_risk_analysis(d: dict) -> dict:
    """Build a multi-factor risk analysis with scores and plain-English explanations."""
    factors = []

    # Volatility
    beta = d.get("beta")
    if beta is not None:
        if beta < 0.6:
            factors.append(
                {
                    "name": "Volatility",
                    "score": 2,
                    "max": 10,
                    "label": "Very Low",
                    "detail": f"Beta {beta:.2f} — moves much less than the market. Very stable.",
                }
            )
        elif beta < 0.9:
            factors.append(
                {
                    "name": "Volatility",
                    "score": 4,
                    "max": 10,
                    "label": "Low",
                    "detail": f"Beta {beta:.2f} — less volatile than average. Relatively stable.",
                }
            )
        elif beta < 1.2:
            factors.append(
                {
                    "name": "Volatility",
                    "score": 6,
                    "max": 10,
                    "label": "Medium",
                    "detail": f"Beta {beta:.2f} — moves roughly with the market.",
                }
            )
        elif beta < 1.6:
            factors.append(
                {
                    "name": "Volatility",
                    "score": 8,
                    "max": 10,
                    "label": "High",
                    "detail": f"Beta {beta:.2f} — more volatile than average. Expect bigger swings.",
                }
            )
        else:
            factors.append(
                {
                    "name": "Volatility",
                    "score": 10,
                    "max": 10,
                    "label": "Very High",
                    "detail": f"Beta {beta:.2f} — significantly more volatile. Not for the faint-hearted.",
                }
            )

    # Valuation
    pe = d.get("pe_ratio")
    fpe = d.get("forward_pe")
    if pe is not None:
        if pe < 0:
            factors.append(
                {
                    "name": "Valuation",
                    "score": 9,
                    "max": 10,
                    "label": "Unprofitable",
                    "detail": f"Negative P/E ({pe:.1f}) — company is currently losing money.",
                }
            )
        elif pe < 12:
            factors.append(
                {
                    "name": "Valuation",
                    "score": 2,
                    "max": 10,
                    "label": "Cheap",
                    "detail": f"P/E {pe:.1f} — trading below market average. Could be undervalued or facing challenges.",
                }
            )
        elif pe < 25:
            factors.append(
                {
                    "name": "Valuation",
                    "score": 4,
                    "max": 10,
                    "label": "Fair",
                    "detail": f"P/E {pe:.1f} — reasonably priced relative to earnings.",
                }
            )
        elif pe < 40:
            factors.append(
                {
                    "name": "Valuation",
                    "score": 6,
                    "max": 10,
                    "label": "Premium",
                    "detail": f"P/E {pe:.1f} — priced above average. Market expects growth.",
                }
            )
        else:
            factors.append(
                {
                    "name": "Valuation",
                    "score": 8,
                    "max": 10,
                    "label": "Expensive",
                    "detail": f"P/E {pe:.1f} — very high expectations baked into the price.",
                }
            )

    # Financial Health
    dte = d.get("debt_to_equity")
    pm = d.get("profit_margin")
    if dte is not None or pm is not None:
        health_score = 5
        parts = []
        if dte is not None:
            if dte < 50:
                health_score -= 2
                parts.append(f"low debt ({dte:.0f}% D/E)")
            elif dte < 100:
                parts.append(f"moderate debt ({dte:.0f}% D/E)")
            elif dte < 200:
                health_score += 1
                parts.append(f"significant debt ({dte:.0f}% D/E)")
            else:
                health_score += 3
                parts.append(f"heavy debt ({dte:.0f}% D/E)")
        if pm is not None:
            if pm > 20:
                health_score -= 1
                parts.append(f"strong margins ({pm:.1f}%)")
            elif pm > 0:
                parts.append(f"positive margins ({pm:.1f}%)")
            else:
                health_score += 2
                parts.append(f"negative margins ({pm:.1f}%)")
        health_score = max(1, min(10, health_score))
        lbl = "Strong" if health_score <= 3 else "Moderate" if health_score <= 6 else "Weak"
        factors.append(
            {
                "name": "Financial Health",
                "score": health_score,
                "max": 10,
                "label": lbl,
                "detail": "; ".join(parts).capitalize() + ".",
            }
        )

    # Growth
    rg = d.get("revenue_growth")
    eg = d.get("earnings_growth")
    if rg is not None or eg is not None:
        parts = []
        growth_score = 5
        if rg is not None:
            if rg > 20:
                growth_score = 2
                parts.append(f"revenue growing fast ({rg:.1f}%)")
            elif rg > 5:
                growth_score = 4
                parts.append(f"revenue growing steadily ({rg:.1f}%)")
            elif rg > -5:
                parts.append(f"revenue flat ({rg:.1f}%)")
            else:
                growth_score = 8
                parts.append(f"revenue declining ({rg:.1f}%)")
        if eg is not None:
            if eg > 20:
                parts.append(f"earnings up {eg:.1f}%")
            elif eg < -10:
                growth_score = min(growth_score + 2, 10)
                parts.append(f"earnings down {eg:.1f}%")
        lbl = "Strong" if growth_score <= 3 else "Moderate" if growth_score <= 6 else "Declining"
        factors.append(
            {
                "name": "Growth",
                "score": growth_score,
                "max": 10,
                "label": lbl,
                "detail": "; ".join(parts).capitalize() + ".",
            }
        )

    # Price Position (vs 52-week range)
    pfh = d.get("pct_from_high")
    pfl = d.get("pct_from_low")
    if pfh is not None and pfl is not None:
        range_pct = 100 * (1 + pfh / 100) if pfh else 0
        if pfh is not None and pfh > -5:
            factors.append(
                {
                    "name": "Price Position",
                    "score": 7,
                    "max": 10,
                    "label": "Near High",
                    "detail": f"{pfh:+.1f}% from 52-week high, {pfl:+.1f}% from low. Trading near its peak.",
                }
            )
        elif pfh is not None and pfh > -15:
            factors.append(
                {
                    "name": "Price Position",
                    "score": 5,
                    "max": 10,
                    "label": "Mid Range",
                    "detail": f"{pfh:+.1f}% from 52-week high, {pfl:+.1f}% from low.",
                }
            )
        else:
            factors.append(
                {
                    "name": "Price Position",
                    "score": 3,
                    "max": 10,
                    "label": "Near Low",
                    "detail": f"{pfh:+.1f}% from 52-week high, {pfl:+.1f}% from low. Could be a buying opportunity or a warning.",
                }
            )

    overall = round(sum(float(f["score"]) for f in factors) / len(factors), 1) if factors else 5  # type: ignore[arg-type, misc]
    if overall <= 3:
        overall_label = "Low Risk"
    elif overall <= 5:
        overall_label = "Moderate Risk"
    elif overall <= 7:
        overall_label = "Elevated Risk"
    else:
        overall_label = "High Risk"

    return {
        "overall_score": overall,
        "overall_label": overall_label,
        "factors": factors,
    }


def _build_analyst_view(d: dict) -> dict | None:
    """Build analyst price target summary."""
    target = d.get("target_mean_price")
    price = d.get("price", 0)
    if target is None or not price:
        return None
    upside = round((target - price) / price * 100, 1)
    return {
        "target_mean": round(target, 2),
        "target_high": round(d["target_high_price"], 2) if d.get("target_high_price") else None,
        "target_low": round(d["target_low_price"], 2) if d.get("target_low_price") else None,
        "upside_pct": upside,
        "num_analysts": d.get("num_analysts", 0),
    }


def _build_instrument_row(d: dict) -> dict:
    """Transform a raw market-data dict into a screener output row."""
    sig = _compute_signal(d)
    risk = _build_risk_analysis(d)
    analyst = _build_analyst_view(d)
    summary_text = d.get("summary", "")
    if summary_text and len(summary_text) > 250:
        summary_text = summary_text[:247] + "..."

    return {
        "symbol": d["symbol"],
        "name": d.get("name") or KNOWN_NAMES.get(d["symbol"], d["symbol"]),
        "sector": d.get("sector", "N/A"),
        "industry": d.get("industry", "N/A"),
        "price": round(d.get("price", 0), 2),
        "market_cap": d.get("market_cap", 0),
        "market_cap_fmt": format_market_cap(d.get("market_cap", 0)),
        "pe_ratio": round(d["pe_ratio"], 2) if d.get("pe_ratio") else None,
        "forward_pe": round(d["forward_pe"], 2) if d.get("forward_pe") else None,
        "dividend_yield": d.get("dividend_yield"),
        "beta": round(d["beta"], 2) if d.get("beta") else None,
        "year_change": d.get("year_change"),
        "recommendation": d.get("recommendation"),
        "signal": sig["signal"],
        "signal_reason": sig["reason"],
        "week52_high": round(d["week52_high"], 2) if d.get("week52_high") else None,
        "week52_low": round(d["week52_low"], 2) if d.get("week52_low") else None,
        "pct_from_high": d.get("pct_from_high"),
        "revenue_growth": d.get("revenue_growth"),
        "earnings_growth": d.get("earnings_growth"),
        "profit_margin": d.get("profit_margin"),
        "return_on_equity": d.get("return_on_equity"),
        "debt_to_equity": d.get("debt_to_equity"),
        "risk_analysis": risk,
        "analyst_targets": analyst,
        "summary": summary_text,
        "asset_type": d.get("asset_type", "Stock"),
        "region": d.get("region", "US"),
    }


# ── Snapshot refresh (called by cache warmer) ────────────────


def refresh_screener_snapshot() -> int:
    """Re-build the full screener snapshot from cached market data.

    Called after the cache warmer finishes so every instrument's data
    is already in the in-memory cache.  The result is stored both in
    _screener_snapshot (for instant queries) and in the database
    (for instant restore after a restart).

    Returns the number of instruments in the snapshot.
    """
    import time

    t0 = time.time()
    all_data = fetch_batch(ALL_UNIVERSE, cached_only=True)
    rows = []
    for d in all_data:
        try:
            rows.append(_build_instrument_row(d))
        except Exception:
            logger.warning("Failed to build screener row for %s", d.get("symbol"))

    rows.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

    # Don't overwrite an existing (possibly DB-restored) snapshot with
    # a smaller one — e.g. if the warm cycle only fetched a fraction
    # of the universe so far.
    with _snapshot_lock:
        if len(rows) >= len(_screener_snapshot):
            _screener_snapshot.clear()
            _screener_snapshot.extend(rows)
        elif len(rows) == 0:
            logger.info("Skipping empty snapshot refresh (keeping %d existing rows)", len(_screener_snapshot))
            elapsed = time.time() - t0
            return len(_screener_snapshot)
        else:
            logger.info(
                "New snapshot (%d) smaller than existing (%d) — keeping existing",
                len(rows),
                len(_screener_snapshot),
            )
            elapsed = time.time() - t0
            return len(_screener_snapshot)

    # Persist to DB for instant cold-start restore
    try:
        from src.services.persistence import save_scan

        save_scan("screener_snapshot", rows)
    except Exception:
        logger.exception("Failed to persist screener snapshot to DB")

    elapsed = time.time() - t0
    logger.info("Screener snapshot refreshed: %d instruments in %.1fs", len(rows), elapsed)
    return len(rows)


def restore_screener_snapshot(data: list[dict]) -> None:
    """Restore the screener snapshot from DB data (called at startup)."""
    with _snapshot_lock:
        _screener_snapshot.clear()
        _screener_snapshot.extend(data)
    logger.info("Restored screener snapshot: %d instruments", len(data))


def get_screener_snapshot() -> list[dict]:
    """Return a copy of the current snapshot (for diagnostics)."""
    with _snapshot_lock:
        return list(_screener_snapshot)


# ── Main screener query (reads from snapshot) ────────────────


def _matches_query(query_lower: str, symbol: str, name: str) -> bool:
    """Check if query matches symbol, name, known name, or any search alias."""
    sym_lower = symbol.lower()
    name_lower = name.lower()
    known = KNOWN_NAMES.get(symbol, "").lower()
    if query_lower in sym_lower or query_lower in name_lower or query_lower in known:
        return True
    # Check aliases for this symbol
    aliases = SEARCH_ALIASES.get(symbol)
    if aliases:
        for alias in aliases:
            if query_lower in alias.lower():
                return True
    # Check if query itself is an alias that maps to this symbol
    matched_sym = _ALIAS_TO_SYMBOL.get(query_lower)
    if matched_sym and matched_sym == symbol:
        return True
    # Partial reverse alias match: check if any alias *contains* the query
    # This helps with partial Hebrew input (e.g. "לאומ" matching "לאומי")
    return any(alias_sym == symbol and query_lower in alias_key for alias_key, alias_sym in _ALIAS_TO_SYMBOL.items())


def screen_instruments(
    asset_type: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    pe_min: Optional[float] = None,
    pe_max: Optional[float] = None,
    dividend_yield_min: Optional[float] = None,
    dividend_yield_max: Optional[float] = None,
    beta_min: Optional[float] = None,
    beta_max: Optional[float] = None,
    signal: Optional[str] = None,
    query: Optional[str] = None,
    year_change_min: Optional[float] = None,
    year_change_max: Optional[float] = None,
    profit_margin_min: Optional[float] = None,
    return_on_equity_min: Optional[float] = None,
    debt_to_equity_max: Optional[float] = None,
    revenue_growth_min: Optional[float] = None,
    earnings_growth_min: Optional[float] = None,
    pct_from_high_min: Optional[float] = None,
    pct_from_high_max: Optional[float] = None,
    region_not: Optional[str] = None,
) -> list[dict]:
    query_lower = query.strip().lower() if query else None

    # Read from the pre-computed snapshot (instant).
    with _snapshot_lock:
        snapshot = list(_screener_snapshot)

    # If the snapshot is empty (first startup, warmer not done yet),
    # fall back to the old live-fetch path so users still get results.
    if not snapshot:
        logger.info("Screener snapshot empty — falling back to live fetch")
        if query_lower:
            matched_syms = [sym for sym in ALL_UNIVERSE if _matches_query(query_lower, sym, KNOWN_NAMES.get(sym, sym))]
            all_data = fetch_batch(matched_syms, cached_only=False) if matched_syms else []
        elif asset_type == "ETF":
            all_data = fetch_batch(ETF_UNIVERSE, cached_only=True)
        elif asset_type == "Stock":
            all_data = fetch_batch(STOCK_UNIVERSE, cached_only=True)
        else:
            all_data = fetch_batch(ALL_UNIVERSE, cached_only=True)
        snapshot = []
        for d in all_data:
            try:
                snapshot.append(_build_instrument_row(d))
            except Exception:
                pass
        snapshot.sort(key=lambda x: x.get("market_cap", 0), reverse=True)

    # ── Filter the snapshot ──────────────────────────────────
    filtered = []
    for row in snapshot:
        if query_lower:
            sym = row.get("symbol") or ""
            name = row.get("name") or ""
            sector_val = (row.get("sector") or "").lower()
            industry_val = (row.get("industry") or "").lower()
            if (
                not _matches_query(query_lower, sym, name)
                and query_lower not in sector_val
                and query_lower not in industry_val
            ):
                continue
            # When query is active, skip asset_type/sector/region filters
        else:
            if asset_type and row.get("asset_type") != asset_type:
                continue
            if sector and (row.get("sector") or "").lower() != sector.lower():
                continue
            if region and row.get("region", "US") != region:
                continue
        if market_cap_min and (row.get("market_cap") or 0) < market_cap_min:
            continue
        if market_cap_max and (row.get("market_cap") or 0) > market_cap_max:
            continue
        if pe_min and (row.get("pe_ratio") is None or row["pe_ratio"] < pe_min):
            continue
        if pe_max and (row.get("pe_ratio") is None or row["pe_ratio"] > pe_max):
            continue
        if dividend_yield_min and (row.get("dividend_yield") is None or row["dividend_yield"] < dividend_yield_min):
            continue
        if dividend_yield_max and (row.get("dividend_yield") is None or row["dividend_yield"] > dividend_yield_max):
            continue
        if beta_min and (row.get("beta") is None or row["beta"] < beta_min):
            continue
        if beta_max and (row.get("beta") is None or row["beta"] > beta_max):
            continue
        if signal and (row.get("signal") or "").lower() != signal.lower():
            continue
        if year_change_min is not None and (row.get("year_change") is None or row["year_change"] < year_change_min):
            continue
        if year_change_max is not None and (row.get("year_change") is None or row["year_change"] > year_change_max):
            continue
        if profit_margin_min is not None and (row.get("profit_margin") is None or row["profit_margin"] < profit_margin_min):
            continue
        if return_on_equity_min is not None and (row.get("return_on_equity") is None or row["return_on_equity"] < return_on_equity_min):
            continue
        if debt_to_equity_max is not None and (row.get("debt_to_equity") is None or row["debt_to_equity"] > debt_to_equity_max):
            continue
        if revenue_growth_min is not None and (row.get("revenue_growth") is None or row["revenue_growth"] < revenue_growth_min):
            continue
        if earnings_growth_min is not None and (row.get("earnings_growth") is None or row["earnings_growth"] < earnings_growth_min):
            continue
        if pct_from_high_min is not None and (row.get("pct_from_high") is None or row["pct_from_high"] < pct_from_high_min):
            continue
        if pct_from_high_max is not None and (row.get("pct_from_high") is None or row["pct_from_high"] > pct_from_high_max):
            continue
        if region_not and row.get("region", "US") == region_not:
            continue

        filtered.append(row)

    filtered.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
    return filtered
