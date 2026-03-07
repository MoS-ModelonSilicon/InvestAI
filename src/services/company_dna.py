"""
Company DNA — Buffett / Munger-style qualitative analysis.

Fetches management team, insider activity, analyst consensus, and
computes a "Berkshire Score" rating how well a company aligns with
Buffett & Munger's investing principles:

1. Durable competitive advantage (moat) — inferred from high/stable margins
2. Excellent management with skin in the game — insider ownership & buying
3. Reasonable valuation — P/E, P/B, margin of safety
4. Strong financials — low debt, high ROE, consistent free cash flow
5. Analyst consensus — smart money sentiment
"""

import logging
from typing import Optional

from src.services import data_provider as dp
from src.services.market_data import fetch_stock_info, _get_cached, _set_cache

logger = logging.getLogger(__name__)


# ── Berkshire Scoring weights ───────────────────────────────────

def compute_berkshire_score(info: dict, executives: list, insiders: list,
                            sentiment: dict | None, recommendations: list) -> dict:
    """
    Compute a 0-100 Berkshire Score inspired by Buffett/Munger principles.
    Returns score breakdown with reasoning.
    """
    breakdown = {}
    total = 0

    # ── 1. Moat / Competitive Advantage (25 pts) ──────────
    moat_score = 0
    moat_reasons = []

    pm = info.get("profit_margin")
    if pm is not None:
        if pm >= 20:
            moat_score += 12
            moat_reasons.append(f"Excellent profit margin ({pm:.1f}%)")
        elif pm >= 15:
            moat_score += 9
            moat_reasons.append(f"Strong profit margin ({pm:.1f}%)")
        elif pm >= 10:
            moat_score += 6
            moat_reasons.append(f"Decent profit margin ({pm:.1f}%)")
        elif pm > 0:
            moat_score += 3
            moat_reasons.append(f"Thin margins ({pm:.1f}%)")
        else:
            moat_reasons.append(f"Negative margins ({pm:.1f}%) — no moat signal")

    roe = info.get("return_on_equity")
    if roe is not None:
        if roe >= 20:
            moat_score += 8
            moat_reasons.append(f"Exceptional ROE ({roe:.1f}%) — strong moat indicator")
        elif roe >= 15:
            moat_score += 6
            moat_reasons.append(f"Good ROE ({roe:.1f}%)")
        elif roe >= 10:
            moat_score += 3
            moat_reasons.append(f"Adequate ROE ({roe:.1f}%)")
        else:
            moat_reasons.append(f"Low ROE ({roe:.1f}%)")

    rg = info.get("revenue_growth")
    if rg is not None and rg > 10:
        moat_score += 5
        moat_reasons.append(f"Revenue growing at {rg:.0f}%")
    elif rg is not None and rg > 0:
        moat_score += 2

    moat_score = min(25, moat_score)
    breakdown["moat"] = {"score": moat_score, "max": 25, "reasons": moat_reasons,
                         "label": "Competitive Advantage (Moat)"}
    total += moat_score

    # ── 2. Management Quality & Skin in the Game (25 pts) ──
    mgmt_score = 0
    mgmt_reasons = []

    # Management team presence
    if executives and len(executives) > 0:
        mgmt_score += 3
        ceo = next((e for e in executives if "CEO" in (e.get("position") or "").upper()
                     or "CHIEF EXECUTIVE" in (e.get("position") or "").upper()), None)
        if ceo:
            since = ceo.get("since")
            if since and isinstance(since, (int, float)) and since > 0:
                tenure = 2026 - since
                if tenure >= 10:
                    mgmt_score += 7
                    mgmt_reasons.append(f"CEO in role {tenure}+ years — long-term leadership")
                elif tenure >= 5:
                    mgmt_score += 5
                    mgmt_reasons.append(f"CEO tenure {tenure} years — stable leadership")
                elif tenure >= 2:
                    mgmt_score += 2
                    mgmt_reasons.append(f"CEO tenure {tenure} years — relatively new")
                else:
                    mgmt_reasons.append(f"New CEO (< 2 years) — transition risk")
            else:
                mgmt_score += 2
                mgmt_reasons.append("CEO identified but tenure unknown")
        else:
            mgmt_reasons.append("No CEO clearly identified in filings")
    else:
        mgmt_reasons.append("No executive data available")

    # Insider activity
    if insiders:
        buys = sum(1 for t in insiders[:20] if _is_insider_buy(t))
        sells = sum(1 for t in insiders[:20] if _is_insider_sell(t))
        if buys > sells and buys >= 2:
            mgmt_score += 8
            mgmt_reasons.append(f"Insiders are net buyers ({buys} buys vs {sells} sells) — skin in the game")
        elif buys > 0 and buys >= sells:
            mgmt_score += 4
            mgmt_reasons.append(f"Balanced insider activity ({buys} buys, {sells} sells)")
        elif sells > buys * 2 and sells >= 3:
            mgmt_reasons.append(f"Heavy insider selling ({sells} sells vs {buys} buys) — caution")
        elif sells > buys:
            mgmt_score += 1
            mgmt_reasons.append(f"Mild insider selling ({sells} sells, {buys} buys)")
        else:
            mgmt_score += 2
            mgmt_reasons.append("Limited insider transaction data")
    else:
        mgmt_reasons.append("No insider transaction data available")

    # Insider sentiment (MSPR)
    if sentiment and sentiment.get("data"):
        recent = sentiment["data"][-3:]  # last 3 months
        avg_mspr = sum(d.get("mspr", 0) for d in recent) / max(len(recent), 1)
        if avg_mspr > 0:
            mgmt_score += 4
            mgmt_reasons.append(f"Positive insider sentiment (MSPR: {avg_mspr:.2f})")
        elif avg_mspr < -5:
            mgmt_reasons.append(f"Negative insider sentiment (MSPR: {avg_mspr:.2f})")
        else:
            mgmt_score += 2
            mgmt_reasons.append(f"Neutral insider sentiment (MSPR: {avg_mspr:.2f})")

    mgmt_score = min(25, mgmt_score)
    breakdown["management"] = {"score": mgmt_score, "max": 25, "reasons": mgmt_reasons,
                               "label": "Management & Insider Activity"}
    total += mgmt_score

    # ── 3. Financial Fortress (25 pts) ─────────────────────
    fin_score = 0
    fin_reasons = []

    de = info.get("debt_to_equity")
    if de is not None:
        if de <= 0.3:
            fin_score += 8
            fin_reasons.append(f"Very low debt (D/E: {de:.2f}) — fortress balance sheet")
        elif de <= 0.8:
            fin_score += 6
            fin_reasons.append(f"Conservative debt (D/E: {de:.2f})")
        elif de <= 1.5:
            fin_score += 3
            fin_reasons.append(f"Moderate debt (D/E: {de:.2f})")
        else:
            fin_reasons.append(f"High debt (D/E: {de:.2f}) — Buffett would be cautious")
    else:
        fin_reasons.append("Debt data unavailable")

    cr = info.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            fin_score += 5
            fin_reasons.append(f"Strong liquidity (Current Ratio: {cr:.2f})")
        elif cr >= 1.5:
            fin_score += 3
            fin_reasons.append(f"Adequate liquidity (Current Ratio: {cr:.2f})")
        elif cr >= 1.0:
            fin_score += 1
            fin_reasons.append(f"Tight liquidity (Current Ratio: {cr:.2f})")
        else:
            fin_reasons.append(f"Liquidity concern (Current Ratio: {cr:.2f})")

    fcf = info.get("free_cash_flow")
    if fcf is not None:
        if fcf > 0:
            fin_score += 7
            mcap = info.get("market_cap", 0) or 1
            fcf_yield = (fcf / mcap) * 100 if mcap > 0 else 0
            if fcf_yield > 5:
                fin_score += 2
                fin_reasons.append(f"Excellent FCF yield ({fcf_yield:.1f}%) — cash machine")
            else:
                fin_reasons.append(f"Positive free cash flow (FCF yield: {fcf_yield:.1f}%)")
        else:
            fin_reasons.append("Negative free cash flow — Buffett prefers cash generators")

    eg = info.get("earnings_growth")
    if eg is not None and eg > 10:
        fin_score += 3
        fin_reasons.append(f"Earnings growing at {eg:.0f}%")

    fin_score = min(25, fin_score)
    breakdown["financials"] = {"score": fin_score, "max": 25, "reasons": fin_reasons,
                               "label": "Financial Strength"}
    total += fin_score

    # ── 4. Valuation & Margin of Safety (15 pts) ──────────
    val_score = 0
    val_reasons = []

    pe = info.get("pe_ratio")
    if pe is not None:
        if 0 < pe <= 15:
            val_score += 8
            val_reasons.append(f"Attractively valued (P/E: {pe:.1f}) — classic Buffett zone")
        elif pe <= 20:
            val_score += 6
            val_reasons.append(f"Reasonable P/E of {pe:.1f}")
        elif pe <= 30:
            val_score += 3
            val_reasons.append(f"Growth premium P/E of {pe:.1f}")
        else:
            val_reasons.append(f"Expensive (P/E: {pe:.1f}) — Munger would want a big moat to justify")
    else:
        val_reasons.append("P/E data unavailable")

    pb = info.get("price_to_book")
    if pb is not None:
        if 0 < pb <= 1.5:
            val_score += 4
            val_reasons.append(f"Below book value (P/B: {pb:.2f}) — margin of safety")
        elif pb <= 3.0:
            val_score += 2
            val_reasons.append(f"Reasonable P/B of {pb:.2f}")
        else:
            val_reasons.append(f"P/B of {pb:.2f} — paying premium for intangibles")

    target = info.get("target_mean_price")
    price = info.get("price")
    if target and price and target > price:
        upside = ((target - price) / price) * 100
        if upside > 20:
            val_score += 3
            val_reasons.append(f"Analyst target implies {upside:.0f}% upside — margin of safety")
        elif upside > 10:
            val_score += 2
            val_reasons.append(f"Analyst target implies {upside:.0f}% upside")

    val_score = min(15, val_score)
    breakdown["valuation"] = {"score": val_score, "max": 15, "reasons": val_reasons,
                              "label": "Valuation & Margin of Safety"}
    total += val_score

    # ── 5. Smart Money Consensus (10 pts) ──────────────────
    cons_score = 0
    cons_reasons = []

    if recommendations:
        latest = recommendations[0]
        sb = latest.get("strongBuy", 0)
        b = latest.get("buy", 0)
        h = latest.get("hold", 0)
        s = latest.get("sell", 0)
        ss = latest.get("strongSell", 0)
        total_analysts = sb + b + h + s + ss
        if total_analysts > 0:
            bullish = sb + b
            bearish = s + ss
            bull_pct = (bullish / total_analysts) * 100

            if bull_pct >= 70:
                cons_score += 7
                cons_reasons.append(f"Strong analyst consensus: {bullish} buy vs {bearish} sell ({total_analysts} analysts)")
            elif bull_pct >= 50:
                cons_score += 5
                cons_reasons.append(f"Positive analyst sentiment: {bullish} buy, {h} hold, {bearish} sell")
            elif bull_pct >= 30:
                cons_score += 2
                cons_reasons.append(f"Mixed analyst views: {bullish} buy, {h} hold, {bearish} sell")
            else:
                cons_reasons.append(f"Bearish analyst sentiment: {bearish} sell vs {bullish} buy")

            if total_analysts >= 15:
                cons_score += 3
                cons_reasons.append(f"Well-covered by {total_analysts} analysts")
            elif total_analysts >= 5:
                cons_score += 1
                cons_reasons.append(f"Covered by {total_analysts} analysts")
        else:
            cons_reasons.append("No analyst coverage data")
    else:
        cons_reasons.append("No analyst recommendation data available")

    cons_score = min(10, cons_score)
    breakdown["consensus"] = {"score": cons_score, "max": 10, "reasons": cons_reasons,
                              "label": "Analyst Consensus"}
    total += cons_score

    # ── Overall grade ──────────────────────────────────────
    total = min(100, total)
    if total >= 80:
        grade = "A"
        verdict = "Berkshire-Grade Investment"
    elif total >= 65:
        grade = "B"
        verdict = "Strong Quality Stock"
    elif total >= 50:
        grade = "C"
        verdict = "Decent Fundamentals"
    elif total >= 35:
        grade = "D"
        verdict = "Speculative / Mixed"
    else:
        grade = "F"
        verdict = "Not Buffett's Style"

    return {
        "score": total,
        "grade": grade,
        "verdict": verdict,
        "breakdown": breakdown,
    }


def get_company_dna(symbol: str) -> Optional[dict]:
    """
    Full Company DNA analysis for a symbol. Returns management team,
    insider activity, analyst consensus, peers, and Berkshire Score.
    """
    cache_key = f"company_dna:{symbol}"
    cached = _get_cached(cache_key)
    if isinstance(cached, dict):
        return cached

    info = fetch_stock_info(symbol)
    if not info:
        return None

    # Fetch all the qualitative data
    executives = dp.get_executives(symbol)
    insiders = dp.get_insider_transactions(symbol)
    sentiment = dp.get_insider_sentiment(symbol)
    recommendations = dp.get_recommendation_trends(symbol)
    peers = dp.get_peers(symbol)
    price_target = dp.get_price_target(symbol)

    # Format executives for display
    exec_list = []
    for ex in executives[:10]:
        exec_list.append({
            "name": ex.get("name", "Unknown"),
            "position": ex.get("position", "N/A"),
            "since": ex.get("since"),
            "compensation": ex.get("compensation"),
            "age": ex.get("age"),
        })

    # Format insider transactions
    insider_list = []
    for tx in insiders[:15]:
        insider_list.append({
            "name": tx.get("name", "Unknown"),
            "share": tx.get("share", 0),
            "change": tx.get("change", 0),
            "filing_date": tx.get("filingDate", ""),
            "transaction_type": _classify_insider_tx(tx),
            "transaction_price": tx.get("transactionPrice"),
        })

    # Format analyst recommendations
    rec_summary = None
    if recommendations:
        latest = recommendations[0]
        rec_summary = {
            "period": latest.get("period", ""),
            "strong_buy": latest.get("strongBuy", 0),
            "buy": latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0),
            "strong_sell": latest.get("strongSell", 0),
        }

    # Format price target
    pt = None
    if price_target:
        pt = {
            "high": price_target.get("targetHigh"),
            "low": price_target.get("targetLow"),
            "mean": price_target.get("targetMean"),
            "median": price_target.get("targetMedian"),
        }

    # Compute Berkshire score
    berkshire = compute_berkshire_score(info, executives, insiders, sentiment, recommendations)

    result = {
        "symbol": symbol,
        "name": info.get("name", symbol),
        "sector": info.get("sector", "N/A"),
        "price": info.get("price"),
        "market_cap": info.get("market_cap"),
        "executives": exec_list,
        "insider_transactions": insider_list,
        "insider_sentiment_trend": _format_sentiment(sentiment),
        "analyst_recommendations": rec_summary,
        "price_target": pt,
        "peers": peers[:8] if peers else [],
        "berkshire_score": berkshire,
        # Pass through key fundamental data for display
        "fundamentals": {
            "pe_ratio": info.get("pe_ratio"),
            "price_to_book": info.get("price_to_book"),
            "profit_margin": info.get("profit_margin"),
            "return_on_equity": info.get("return_on_equity"),
            "debt_to_equity": info.get("debt_to_equity"),
            "current_ratio": info.get("current_ratio"),
            "free_cash_flow": info.get("free_cash_flow"),
            "revenue_growth": info.get("revenue_growth"),
            "dividend_yield": info.get("dividend_yield"),
        },
    }

    _set_cache(cache_key, result)
    return result


# ── Helpers ─────────────────────────────────────────────────

def _is_insider_buy(tx: dict) -> bool:
    code = (tx.get("transactionCode") or "").upper()
    change = tx.get("change", 0)
    return code in ("P", "A", "M") or (change and change > 0)


def _is_insider_sell(tx: dict) -> bool:
    code = (tx.get("transactionCode") or "").upper()
    change = tx.get("change", 0)
    return code == "S" or (change and change < 0)


def _classify_insider_tx(tx: dict) -> str:
    code = (tx.get("transactionCode") or "").upper()
    mapping = {
        "P": "Purchase",
        "S": "Sale",
        "A": "Grant/Award",
        "M": "Option Exercise",
        "G": "Gift",
        "F": "Tax Withholding",
        "C": "Conversion",
    }
    return mapping.get(code, code or "Unknown")


def _format_sentiment(sentiment: dict | None) -> list[dict]:
    if not sentiment or not sentiment.get("data"):
        return []
    result = []
    for d in sentiment["data"][-6:]:
        result.append({
            "year": d.get("year"),
            "month": d.get("month"),
            "mspr": round(d.get("mspr", 0), 2),
            "change": d.get("change", 0),
        })
    return result
