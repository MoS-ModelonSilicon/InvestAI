"""
DCA (Dollar-Cost Averaging) service.

Analyses the user's DCA plans against their portfolio holdings and live
market data.  Key features:
  - Detect dips (stock drops 15-20%+ from avg cost or 52-week high)
  - Recommend 2X+ buying when dip is detected
  - Build monthly allocation plan based on investor budget
  - Provide portfolio-wide DCA dashboard
  - Backtest DCA strategy with historical data
  - Track execution history (bought / skipped)
  - Guided wizard with strategy presets
"""

import logging
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session

from src.models import DcaPlan, DcaExecution, Holding, RiskProfile
from src.services.market_data import fetch_stock_info, fetch_batch
from src.services.data_provider import get_candles

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────


def _avg_cost_for_symbol(holdings: list[Holding], symbol: str) -> float | None:
    """Weighted-average cost basis for a symbol across all lots."""
    total_qty = 0.0
    total_cost = 0.0
    for h in holdings:
        if h.symbol.upper() == symbol.upper():
            total_qty += h.quantity
            total_cost += h.quantity * h.buy_price
    if total_qty == 0:
        return None
    return round(total_cost / total_qty, 4)


def _total_qty_for_symbol(holdings: list[Holding], symbol: str) -> float:
    return float(sum(h.quantity for h in holdings if h.symbol.upper() == symbol.upper()))


def _urgency_label(drop_pct: float) -> str:
    if drop_pct <= -30:
        return "high"
    if drop_pct <= -20:
        return "medium"
    return "low"


def _next_first_of_month() -> str:
    today = date.today()
    if today.day == 1:
        return today.strftime("%Y-%m-%d")
    y, m = today.year, today.month + 1
    if m > 12:
        m, y = 1, y + 1
    return date(y, m, 1).strftime("%Y-%m-%d")


# ── Core analysis ────────────────────────────────────────────


def analyze_dca_opportunity(plan: DcaPlan, holdings: list[Holding]) -> dict | None:
    """
    Check if a DCA plan's stock has dipped enough to trigger an extra buy.
    Returns an opportunity dict or None.
    """
    info = fetch_stock_info(plan.symbol)
    if not info or not info.get("price"):
        return None

    price = info["price"]
    avg_cost = _avg_cost_for_symbol(holdings, plan.symbol)

    # If no existing holdings, use the plan budget at normal rate
    if avg_cost is None or avg_cost <= 0:
        return None

    drop_from_cost = round((price - avg_cost) / avg_cost * 100, 2)
    drop_from_high = info.get("pct_from_high")  # already computed by market_data

    # Check if dip threshold is breached
    threshold = plan.dip_threshold  # e.g. -15.0
    if drop_from_cost > threshold:
        return None  # stock hasn't dipped enough

    # Calculate multiplier — scale with severity of the dip
    base_mult = plan.dip_multiplier
    # Extra escalation: if drop > 2× threshold, bump multiplier
    if threshold != 0 and drop_from_cost <= threshold * 2:
        applied_mult = round(base_mult * 1.5, 1)  # e.g. 3X for very deep dips
    else:
        applied_mult = base_mult

    recommended_buy = round(plan.monthly_budget * applied_mult, 2)
    shares_to_buy = round(recommended_buy / price, 4) if price > 0 else 0

    urgency = _urgency_label(drop_from_cost)

    reason_parts = [
        f"{plan.symbol} is down {abs(drop_from_cost):.1f}% from your avg cost (${avg_cost:.2f} → ${price:.2f})"
    ]
    if drop_from_high and drop_from_high < -15:
        reason_parts.append(f"Also {abs(drop_from_high):.1f}% below 52-week high")
    reason_parts.append(f"DCA strategy: invest {applied_mult:.1f}× your normal ${plan.monthly_budget:.0f}/mo")

    return {
        "symbol": plan.symbol,
        "name": plan.name or info.get("name", plan.symbol),
        "current_price": price,
        "avg_cost": avg_cost,
        "drop_from_cost": drop_from_cost,
        "drop_from_high": drop_from_high,
        "plan_budget": plan.monthly_budget,
        "recommended_buy": recommended_buy,
        "multiplier": applied_mult,
        "shares_to_buy": shares_to_buy,
        "urgency": urgency,
        "reason": " · ".join(reason_parts),
    }


def build_monthly_allocation(plans: list[DcaPlan], holdings: list[Holding]) -> dict:
    """
    Build a full monthly allocation recommendation across all active DCA plans.
    """
    allocations = []
    total_normal = 0.0
    total_recommended = 0.0
    month_str = datetime.now().strftime("%Y-%m")

    for plan in plans:
        if not plan.active:
            continue

        info = fetch_stock_info(plan.symbol)
        price = info.get("price", 0) if info else 0
        avg_cost = _avg_cost_for_symbol(holdings, plan.symbol)
        name = plan.name or (info.get("name", plan.symbol) if info else plan.symbol)

        dip_pct = 0.0
        dip_detected = False
        multiplier_applied = 1.0
        recommended = plan.monthly_budget
        reason = "Regular monthly DCA investment"

        if avg_cost and avg_cost > 0 and price > 0:
            dip_pct = round((price - avg_cost) / avg_cost * 100, 2)

            if dip_pct <= plan.dip_threshold:
                dip_detected = True
                # Scale multiplier with dip severity
                if plan.dip_threshold != 0 and dip_pct <= plan.dip_threshold * 2:
                    multiplier_applied = round(plan.dip_multiplier * 1.5, 1)
                else:
                    multiplier_applied = plan.dip_multiplier
                recommended = round(plan.monthly_budget * multiplier_applied, 2)
                reason = (
                    f"🔻 Dip detected: {plan.symbol} is {abs(dip_pct):.1f}% below avg cost. "
                    f"Investing {multiplier_applied:.1f}× normal amount."
                )

        shares = round(recommended / price, 4) if price > 0 else 0

        allocations.append(
            {
                "symbol": plan.symbol,
                "name": name,
                "normal_amount": plan.monthly_budget,
                "dip_detected": dip_detected,
                "dip_pct": dip_pct,
                "recommended_amount": recommended,
                "multiplier_applied": multiplier_applied,
                "reason": reason,
                "current_price": price if price > 0 else None,
                "avg_cost": avg_cost,
                "shares_to_buy": shares,
            }
        )

        total_normal += plan.monthly_budget
        total_recommended += recommended

    over_budget = total_recommended > total_normal
    over_amount = round(total_recommended - total_normal, 2) if over_budget else 0

    # Build tips
    suggestions = []
    dip_count = sum(1 for a in allocations if a["dip_detected"])
    if dip_count > 0:
        suggestions.append(
            f"💡 {dip_count} stock(s) are in dip territory — great DCA opportunity to lower your average cost."
        )
    if over_budget:
        suggestions.append(
            f"⚠️ This month's recommended total (${total_recommended:,.0f}) exceeds your normal budget "
            f"(${total_normal:,.0f}) by ${over_amount:,.0f} due to dip buys. "
            f"Adjust plan budgets if this exceeds your cash reserves."
        )
    if not allocations:
        suggestions.append("Add DCA plans for stocks you want to invest in regularly.")
    else:
        no_dip = [a for a in allocations if not a["dip_detected"]]
        if no_dip:
            suggestions.append(
                f"✅ {len(no_dip)} stock(s) at normal DCA pace — steady accumulation builds wealth over time."
            )

    return {
        "total_monthly_budget": round(total_normal, 2),
        "total_recommended": round(total_recommended, 2),
        "over_budget": over_budget,
        "over_budget_amount": over_amount,
        "allocations": allocations,
        "month": month_str,
        "suggestions": suggestions,
    }


def get_dca_dashboard(db: Session, user_id: int) -> dict:
    """Full DCA dashboard: plans, opportunities, monthly allocation."""
    plans = db.query(DcaPlan).filter(DcaPlan.user_id == user_id).order_by(DcaPlan.created_at.desc()).all()
    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()

    active_plans = [p for p in plans if p.active]

    # Pre-fetch all needed symbols in parallel so subsequent
    # fetch_stock_info calls hit the in-memory cache instantly.
    # full=False skips the expensive get_metrics() Finnhub call for
    # uncached symbols — DCA only needs price, name, and pct_from_high.
    all_symbols = list({p.symbol for p in active_plans} | {h.symbol for h in holdings})
    if all_symbols:
        fetch_batch(all_symbols, full=False)

    # Find opportunities (dipped stocks)
    opportunities = []
    for p in active_plans:
        opp = analyze_dca_opportunity(p, holdings)
        if opp:
            opportunities.append(opp)

    # Sort by urgency (high first) then by drop magnitude
    urgency_order = {"high": 0, "medium": 1, "low": 2}
    opportunities.sort(key=lambda o: (urgency_order.get(o["urgency"], 3), o["drop_from_cost"]))

    # Build this month's allocation
    allocation = build_monthly_allocation(active_plans, holdings)

    # Total $ in DCA plans
    total_dca = sum(p.monthly_budget for p in active_plans)

    plan_dicts = []
    for p in plans:
        plan_dicts.append(
            {
                "id": p.id,
                "symbol": p.symbol,
                "name": p.name,
                "monthly_budget": p.monthly_budget,
                "dip_threshold": p.dip_threshold,
                "dip_multiplier": p.dip_multiplier,
                "is_long_term": bool(p.is_long_term),
                "notes": p.notes,
                "active": bool(p.active),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    return {
        "plans": plan_dicts,
        "opportunities": opportunities,
        "monthly_allocation": allocation,
        "portfolio_dca_value": round(total_dca, 2),
        "next_buy_date": _next_first_of_month(),
    }


def suggest_monthly_budget(db: Session, user_id: int) -> dict:
    """
    Suggest how much the investor should invest monthly based on their
    risk profile and current portfolio.
    """
    profile = (
        db.query(RiskProfile).filter(RiskProfile.user_id == user_id).order_by(RiskProfile.created_at.desc()).first()
    )

    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
    plans = db.query(DcaPlan).filter(DcaPlan.user_id == user_id, DcaPlan.active == 1).all()

    current_dca_total = sum(p.monthly_budget for p in plans)

    # Defaults if no risk profile
    monthly_investment: float = 500
    risk_label = "moderate"
    timeline = "5-10 years"
    goal = "growth"

    if profile:
        monthly_investment = profile.monthly_investment or 500
        risk_label = profile.profile_label or "moderate"
        timeline = profile.timeline or "5-10 years"
        goal = profile.goal or "growth"

    # Calculate current portfolio value
    total_portfolio_value = 0.0
    for h in holdings:
        info = fetch_stock_info(h.symbol)
        if info and info.get("price"):
            total_portfolio_value += h.quantity * info["price"]

    # Suggest allocation strategy based on risk profile
    suggestions = []
    allocation_rules: list[str] = []

    if "aggressive" in risk_label.lower():
        stock_pct = 80
        etf_pct = 15
        cash_pct = 5
        suggestions.append(
            f"With your aggressive risk profile, allocate ~{stock_pct}% to individual stocks "
            f"and {etf_pct}% to broad ETFs (SPY, QQQ) as a baseline."
        )
    elif "conservative" in risk_label.lower():
        stock_pct = 40
        etf_pct = 45
        cash_pct = 15
        suggestions.append(
            f"With your conservative profile, favor ETFs ({etf_pct}%) over individual stocks ({stock_pct}%). "
            f"Keep {cash_pct}% in cash reserves for dip-buying opportunities."
        )
    else:
        stock_pct = 60
        etf_pct = 30
        cash_pct = 10
        suggestions.append(f"Moderate strategy: {stock_pct}% stocks, {etf_pct}% ETFs, {cash_pct}% dip reserve.")

    # Position sizing rule
    max_per_stock = round(monthly_investment * 0.25, 2)
    suggestions.append(
        f"Rule of thumb: no single stock should exceed 25% of your monthly budget "
        f"(max ${max_per_stock:.0f}/stock/month from your ${monthly_investment:.0f} budget)."
    )

    if current_dca_total > monthly_investment:
        suggestions.append(
            f"⚠️ Your DCA plans total ${current_dca_total:,.0f}/mo but your stated budget is "
            f"${monthly_investment:,.0f}/mo. Consider adjusting."
        )
    elif current_dca_total < monthly_investment * 0.5:
        remaining = monthly_investment - current_dca_total
        suggestions.append(
            f"You have ${remaining:,.0f}/mo unallocated. Consider adding DCA plans for "
            f"diversified ETFs like SPY or VTI."
        )

    # Recommend number of DCA positions
    if monthly_investment >= 2000:
        ideal_positions = "8-12"
    elif monthly_investment >= 1000:
        ideal_positions = "5-8"
    elif monthly_investment >= 500:
        ideal_positions = "3-5"
    else:
        ideal_positions = "2-3"

    suggestions.append(
        f"For a ${monthly_investment:,.0f}/mo budget, aim for {ideal_positions} DCA positions "
        f"to balance diversification with meaningful position sizes."
    )

    # Timeline-based guidance
    if "1" in timeline or "short" in timeline.lower():
        suggestions.append(
            "⏰ Short timeline: favor stable, dividend-paying stocks and bond ETFs. "
            "Avoid high-volatility growth stocks for DCA."
        )
    elif "10" in timeline or "long" in timeline.lower() or "20" in timeline:
        suggestions.append(
            "🎯 Long horizon: perfect for aggressive DCA in quality growth stocks. "
            "Dips are your friend — lean into 2-3× buys when they happen."
        )

    return {
        "monthly_budget": monthly_investment,
        "risk_profile": risk_label,
        "timeline": timeline,
        "goal": goal,
        "current_dca_allocated": round(current_dca_total, 2),
        "remaining_budget": round(max(monthly_investment - current_dca_total, 0), 2),
        "portfolio_value": round(total_portfolio_value, 2),
        "num_active_plans": len(plans),
        "suggested_stock_pct": stock_pct,
        "suggested_etf_pct": etf_pct,
        "suggested_cash_reserve_pct": cash_pct,
        "max_per_stock": max_per_stock,
        "suggestions": suggestions,
    }


# ── Wizard Presets ───────────────────────────────────────────

DCA_PRESETS = [
    {
        "key": "conservative",
        "label": "🛡️ Conservative",
        "dip_threshold": -10.0,
        "dip_multiplier": 1.5,
        "description": "Buy 1.5× when stock dips 10%+. Lower risk, smaller extra buys.",
    },
    {
        "key": "balanced",
        "label": "⚖️ Balanced",
        "dip_threshold": -15.0,
        "dip_multiplier": 2.0,
        "description": "Double down when stock dips 15%+. Good for most investors.",
    },
    {
        "key": "aggressive",
        "label": "🔥 Aggressive",
        "dip_threshold": -25.0,
        "dip_multiplier": 3.0,
        "description": "Triple down on 25%+ dips. High conviction, deeper pockets.",
    },
]


def get_wizard_preview(symbol: str, user_id: int, db: Session) -> dict:
    """Fetch stock info + suggest budget for the wizard's first step."""
    info = fetch_stock_info(symbol)
    if not info or not info.get("price"):
        return {"error": f"Could not find stock data for {symbol}"}

    # Get risk profile for budget suggestion
    profile = (
        db.query(RiskProfile).filter(RiskProfile.user_id == user_id).order_by(RiskProfile.created_at.desc()).first()
    )
    monthly_investment: float = 500.0
    if profile and profile.monthly_investment:
        monthly_investment = float(profile.monthly_investment)

    # Suggest 10-25% of monthly budget for this stock
    suggested = round(monthly_investment * 0.15, 0)
    suggested_range = [
        max(round(monthly_investment * 0.05, 0), 25),
        round(monthly_investment * 0.25, 0),
    ]

    return {
        "symbol": info["symbol"],
        "name": info.get("name", symbol),
        "price": info["price"],
        "change_pct": info.get("pct_from_high"),
        "week52_high": info.get("week52_high"),
        "week52_low": info.get("week52_low"),
        "pct_from_high": info.get("pct_from_high"),
        "sector": info.get("sector", ""),
        "pe_ratio": info.get("pe_ratio"),
        "suggested_budget": suggested,
        "suggested_budget_range": suggested_range,
    }


# ── Execution Tracking ──────────────────────────────────────


def log_execution(
    db: Session,
    user_id: int,
    plan_id: int,
    amount_invested: float = 0,
    shares_bought: float = 0,
    price: float = 0,
    was_dip_buy: bool = False,
    skipped: bool = False,
    skip_reason: str = "",
    exec_date: date | None = None,
) -> dict:
    """Record a DCA buy or skip for a plan."""
    plan = db.query(DcaPlan).filter(DcaPlan.id == plan_id, DcaPlan.user_id == user_id).first()
    if not plan:
        return {"error": "Plan not found"}

    execution = DcaExecution(
        plan_id=plan_id,
        user_id=user_id,
        date=exec_date or date.today(),
        amount_invested=amount_invested,
        shares_bought=shares_bought,
        price=price,
        was_dip_buy=1 if was_dip_buy else 0,
        skipped=1 if skipped else 0,
        skip_reason=skip_reason,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return {
        "id": execution.id,
        "plan_id": execution.plan_id,
        "symbol": plan.symbol,
        "date": execution.date.isoformat(),
        "amount_invested": execution.amount_invested,
        "shares_bought": execution.shares_bought,
        "price": execution.price,
        "was_dip_buy": bool(execution.was_dip_buy),
        "skipped": bool(execution.skipped),
        "skip_reason": execution.skip_reason,
    }


def get_execution_history(db: Session, user_id: int, plan_id: int | None = None) -> dict:
    """Get execution history with streak tracking."""
    q = db.query(DcaExecution).filter(DcaExecution.user_id == user_id)
    if plan_id:
        q = q.filter(DcaExecution.plan_id == plan_id)
    execs = q.order_by(DcaExecution.date.desc()).all()

    # Build per-plan stats
    plan_stats: dict[int, dict] = {}
    for ex in execs:
        pid = ex.plan_id
        if pid not in plan_stats:
            plan_stats[pid] = {
                "plan_id": pid,
                "total_invested": 0,
                "total_shares": 0,
                "buy_count": 0,
                "skip_count": 0,
                "dip_buy_count": 0,
                "streak": 0,
                "streak_counting": True,
            }
        s = plan_stats[pid]
        if not ex.skipped:
            s["total_invested"] += ex.amount_invested
            s["total_shares"] += ex.shares_bought
            s["buy_count"] += 1
            if ex.was_dip_buy:
                s["dip_buy_count"] += 1
            if s["streak_counting"]:
                s["streak"] += 1
        else:
            s["skip_count"] += 1
            s["streak_counting"] = False

    # Clean up internal field
    for s in plan_stats.values():
        del s["streak_counting"]
        s["total_invested"] = round(s["total_invested"], 2)
        s["total_shares"] = round(s["total_shares"], 4)
        if s["total_shares"] > 0:
            s["avg_cost"] = round(s["total_invested"] / s["total_shares"], 2)
        else:
            s["avg_cost"] = 0

    exec_list = [
        {
            "id": ex.id,
            "plan_id": ex.plan_id,
            "date": ex.date.isoformat(),
            "amount_invested": ex.amount_invested,
            "shares_bought": ex.shares_bought,
            "price": ex.price,
            "was_dip_buy": bool(ex.was_dip_buy),
            "skipped": bool(ex.skipped),
            "skip_reason": ex.skip_reason,
        }
        for ex in execs
    ]

    return {
        "executions": exec_list,
        "plan_stats": list(plan_stats.values()),
        "total_executions": len(exec_list),
    }


# ── Backtest Engine ──────────────────────────────────────────


def backtest_dca(
    symbol: str,
    monthly_budget: float,
    dip_threshold: float = -15.0,
    dip_multiplier: float = 2.0,
    months: int = 24,
) -> dict:
    """
    Simulate a DCA strategy over historical data.
    Compares smart-DCA (with dip amplification) vs plain DCA (same amount every month).
    """
    now = datetime.now()
    start = now - timedelta(days=months * 31)  # approximate
    from_ts = int(start.timestamp())
    to_ts = int(now.timestamp())

    candles = get_candles(symbol, "D", from_ts, to_ts)
    if not candles or candles.get("s") != "ok" or not candles.get("c"):
        # Return empty result if no data
        return {
            "symbol": symbol,
            "months": months,
            "monthly_budget": monthly_budget,
            "dip_threshold": dip_threshold,
            "dip_multiplier": dip_multiplier,
            "total_invested_dca": 0,
            "portfolio_value_dca": 0,
            "total_shares_dca": 0,
            "avg_cost_dca": 0,
            "total_invested_plain": 0,
            "portfolio_value_plain": 0,
            "total_shares_plain": 0,
            "avg_cost_plain": 0,
            "dca_return_pct": 0,
            "plain_dca_return_pct": 0,
            "dip_buys_count": 0,
            "monthly_data": [],
            "error": "No historical data available",
        }

    closes = candles["c"]
    timestamps = candles["t"]

    # Group candles by month, take first trading day of each month
    monthly_prices: list[tuple[str, float]] = []
    seen_months: set[str] = set()
    for i, ts in enumerate(timestamps):
        dt = datetime.fromtimestamp(ts)
        month_key = dt.strftime("%Y-%m")
        if month_key not in seen_months:
            seen_months.add(month_key)
            monthly_prices.append((month_key, closes[i]))

    if len(monthly_prices) < 2:
        return {
            "symbol": symbol,
            "months": months,
            "monthly_budget": monthly_budget,
            "dip_threshold": dip_threshold,
            "dip_multiplier": dip_multiplier,
            "total_invested_dca": 0,
            "portfolio_value_dca": 0,
            "total_shares_dca": 0,
            "avg_cost_dca": 0,
            "total_invested_plain": 0,
            "portfolio_value_plain": 0,
            "total_shares_plain": 0,
            "avg_cost_plain": 0,
            "dca_return_pct": 0,
            "plain_dca_return_pct": 0,
            "dip_buys_count": 0,
            "monthly_data": [],
            "error": "Insufficient historical data",
        }

    # Simulate
    smart_total_invested = 0.0
    smart_total_shares = 0.0
    plain_total_invested = 0.0
    plain_total_shares = 0.0
    dip_buys = 0
    monthly_data = []

    for i, (month, price) in enumerate(monthly_prices):
        # Plain DCA: buy same amount every month
        plain_shares = monthly_budget / price if price > 0 else 0
        plain_total_invested += monthly_budget
        plain_total_shares += plain_shares

        # Smart DCA: check if price dipped from running avg cost
        smart_avg = (smart_total_invested / smart_total_shares) if smart_total_shares > 0 else price
        drop_pct = ((price - smart_avg) / smart_avg * 100) if smart_avg > 0 else 0

        is_dip = drop_pct <= dip_threshold and i > 0
        if is_dip:
            # Extra escalation for very deep dips
            if dip_threshold != 0 and drop_pct <= dip_threshold * 2:
                mult = round(dip_multiplier * 1.5, 1)
            else:
                mult = dip_multiplier
            invest_amount = monthly_budget * mult
            dip_buys += 1
        else:
            mult = 1.0
            invest_amount = monthly_budget

        smart_shares = invest_amount / price if price > 0 else 0
        smart_total_invested += invest_amount
        smart_total_shares += smart_shares

        monthly_data.append(
            {
                "month": month,
                "price": round(price, 2),
                "smart_invested": round(invest_amount, 2),
                "smart_shares": round(smart_shares, 4),
                "smart_total_shares": round(smart_total_shares, 4),
                "smart_total_invested": round(smart_total_invested, 2),
                "smart_value": round(smart_total_shares * price, 2),
                "plain_invested": round(monthly_budget, 2),
                "plain_shares": round(plain_shares, 4),
                "plain_total_shares": round(plain_total_shares, 4),
                "plain_total_invested": round(plain_total_invested, 2),
                "plain_value": round(plain_total_shares * price, 2),
                "dip_detected": is_dip,
                "multiplier": mult,
                "drop_pct": round(drop_pct, 2),
            }
        )

    last_price = monthly_prices[-1][1] if monthly_prices else 0
    smart_value = round(smart_total_shares * last_price, 2)
    plain_value = round(plain_total_shares * last_price, 2)

    smart_return = round((smart_value / smart_total_invested - 1) * 100, 2) if smart_total_invested > 0 else 0
    plain_return = round((plain_value / plain_total_invested - 1) * 100, 2) if plain_total_invested > 0 else 0

    return {
        "symbol": symbol,
        "months": months,
        "monthly_budget": monthly_budget,
        "dip_threshold": dip_threshold,
        "dip_multiplier": dip_multiplier,
        "total_invested_dca": round(smart_total_invested, 2),
        "portfolio_value_dca": smart_value,
        "total_shares_dca": round(smart_total_shares, 4),
        "avg_cost_dca": round(smart_total_invested / smart_total_shares, 2) if smart_total_shares > 0 else 0,
        "total_invested_plain": round(plain_total_invested, 2),
        "portfolio_value_plain": plain_value,
        "total_shares_plain": round(plain_total_shares, 4),
        "avg_cost_plain": round(plain_total_invested / plain_total_shares, 2) if plain_total_shares > 0 else 0,
        "dca_return_pct": smart_return,
        "plain_dca_return_pct": plain_return,
        "dip_buys_count": dip_buys,
        "monthly_data": monthly_data,
    }


# ── Rebalance Suggestions ───────────────────────────────────


def get_rebalance_suggestions(db: Session, user_id: int) -> list[dict]:
    """Detect portfolio concentration drift and suggest DCA adjustments."""
    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
    plans = db.query(DcaPlan).filter(DcaPlan.user_id == user_id, DcaPlan.active == 1).all()

    if not holdings or not plans:
        return []

    # Pre-fetch all holding symbols in parallel (may already be cached
    # from get_dca_dashboard, but this covers standalone calls too).
    holding_symbols = list({h.symbol for h in holdings})
    if holding_symbols:
        fetch_batch(holding_symbols, full=False)

    # Calculate current portfolio weights
    symbol_values: dict[str, float] = {}
    total_value = 0.0
    for h in holdings:
        info = fetch_stock_info(h.symbol)
        if info and info.get("price"):
            val = h.quantity * info["price"]
            key = h.symbol.upper()
            symbol_values[key] = symbol_values.get(key, 0) + val
            total_value += val

    if total_value == 0:
        return []

    suggestions = []
    total_dca_budget = sum(p.monthly_budget for p in plans)
    plan_symbols = {p.symbol.upper() for p in plans}

    for sym, val in symbol_values.items():
        weight = val / total_value * 100
        if weight > 35 and sym in plan_symbols:
            suggestions.append(
                {
                    "type": "overweight",
                    "symbol": sym,
                    "weight_pct": round(weight, 1),
                    "message": (
                        f"⚠️ {sym} is {weight:.0f}% of your portfolio. "
                        f"Consider reducing its DCA budget and diversifying."
                    ),
                }
            )
        elif weight < 5 and sym in plan_symbols:
            suggestions.append(
                {
                    "type": "underweight",
                    "symbol": sym,
                    "weight_pct": round(weight, 1),
                    "message": (
                        f"📈 {sym} is only {weight:.1f}% of your portfolio. "
                        f"Consider increasing its DCA allocation to build this position."
                    ),
                }
            )

    return suggestions
