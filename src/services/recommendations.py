from src.services.market_data import fetch_batch, STOCK_UNIVERSE, ETF_UNIVERSE, format_market_cap
from src.services.risk_profile import get_allocation


def generate_recommendations(risk_score: int, profile_label: str) -> dict:
    allocation = get_allocation(profile_label)

    all_stocks = fetch_batch(STOCK_UNIVERSE, cached_only=True)
    all_etfs = fetch_batch(ETF_UNIVERSE, cached_only=True)

    scored_stocks = [_score_instrument(s, risk_score, profile_label) for s in all_stocks if s]
    scored_etfs = [_score_instrument(e, risk_score, profile_label) for e in all_etfs if e]

    scored_stocks.sort(key=lambda x: x["match_score"], reverse=True)
    scored_etfs.sort(key=lambda x: x["match_score"], reverse=True)

    recs = scored_stocks[:8] + scored_etfs[:7]
    recs.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "profile_label": profile_label,
        "risk_score": risk_score,
        "allocation": {
            "stocks": allocation["stocks"],
            "bonds": allocation["bonds"],
            "cash": allocation["cash"],
        },
        "recommendations": recs,
    }


def _score_instrument(data: dict, risk_score: int, profile_label: str) -> dict:
    score = 50
    beta = data.get("beta")
    pe = data.get("pe_ratio")
    div_yield = data.get("dividend_yield")
    year_chg = data.get("year_change")

    if beta is not None:
        if profile_label in ("Very Conservative", "Conservative"):
            if beta < 0.8:
                score += 20
            elif beta < 1.0:
                score += 10
            elif beta > 1.3:
                score -= 15
        elif profile_label in ("Growth", "Aggressive"):
            if beta > 1.2:
                score += 15
            elif beta > 1.0:
                score += 10
            elif beta < 0.7:
                score -= 10

    if div_yield is not None:
        if profile_label in ("Very Conservative", "Conservative"):
            if div_yield > 3.0:
                score += 15
            elif div_yield > 1.5:
                score += 8
        elif profile_label in ("Growth", "Aggressive"):
            if div_yield > 4.0:
                score -= 5

    if pe is not None and pe > 0:
        if profile_label in ("Very Conservative", "Conservative"):
            if pe < 15:
                score += 10
            elif pe > 35:
                score -= 10
        elif profile_label in ("Growth", "Aggressive"):
            if pe < 30:
                score += 5

    if year_chg is not None:
        if year_chg > 20 and risk_score >= 7:
            score += 10
        elif year_chg < -10 and risk_score <= 3:
            score -= 10

    rec = data.get("recommendation", "")
    if rec in ("buy", "strong_buy"):
        score += 10
    elif rec == "sell":
        score -= 15

    score = max(10, min(99, score))

    risk_level = "Low"
    if beta and beta > 1.3:
        risk_level = "High"
    elif beta and beta > 1.0:
        risk_level = "Medium"

    reason = _build_reason(data, profile_label, risk_level)

    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "asset_type": data.get("asset_type", "Stock"),
        "sector": data.get("sector", "N/A"),
        "price": round(data.get("price", 0), 2),
        "match_score": score,
        "risk_level": risk_level,
        "reason": reason,
        "pe_ratio": round(pe, 2) if pe else None,
        "dividend_yield": div_yield,
        "beta": round(beta, 2) if beta else None,
        "year_change": year_chg,
    }


def _build_reason(data: dict, profile_label: str, risk_level: str) -> str:
    parts = []
    beta = data.get("beta")
    div_yield = data.get("dividend_yield")

    if profile_label in ("Very Conservative", "Conservative"):
        if beta and beta < 0.8:
            parts.append("Low volatility")
        if div_yield and div_yield > 2.5:
            parts.append(f"Strong {div_yield:.1f}% dividend yield")
        if not parts:
            parts.append("Established company with stable track record")
    elif profile_label == "Moderate":
        parts.append("Balanced risk-return profile")
        if div_yield and div_yield > 1.5:
            parts.append(f"{div_yield:.1f}% dividend")
    else:
        if beta and beta > 1.2:
            parts.append("High growth potential")
        yr = data.get("year_change")
        if yr and yr > 15:
            parts.append(f"Strong momentum (+{yr:.0f}% YoY)")
        if not parts:
            parts.append("Growth-oriented with upside potential")

    return ". ".join(parts)
