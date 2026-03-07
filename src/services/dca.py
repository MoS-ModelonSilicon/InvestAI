"""
DCA (Dollar-Cost Averaging) service.

Analyses the user's DCA plans against their portfolio holdings and live
market data.  Key features:
  - Detect dips (stock drops 15-20%+ from avg cost or 52-week high)
  - Recommend 2X+ buying when dip is detected
  - Build monthly allocation plan based on investor budget
  - Provide portfolio-wide DCA dashboard
"""

import logging
from datetime import datetime, date

from sqlalchemy.orm import Session

from src.models import DcaPlan, Holding, RiskProfile
from src.services.market_data import fetch_stock_info

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

    reason_parts = [f"{plan.symbol} is down {abs(drop_from_cost):.1f}% from your avg cost (${avg_cost:.2f} → ${price:.2f})"]
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

        allocations.append({
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
        })

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
    plans = (
        db.query(DcaPlan)
        .filter(DcaPlan.user_id == user_id)
        .order_by(DcaPlan.created_at.desc())
        .all()
    )
    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()

    active_plans = [p for p in plans if p.active]

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
        plan_dicts.append({
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
        })

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
        db.query(RiskProfile)
        .filter(RiskProfile.user_id == user_id)
        .order_by(RiskProfile.created_at.desc())
        .first()
    )

    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
    plans = (
        db.query(DcaPlan)
        .filter(DcaPlan.user_id == user_id, DcaPlan.active == 1)
        .all()
    )

    current_dca_total = sum(p.monthly_budget for p in plans)

    # Defaults if no risk profile
    monthly_investment = 500
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
        suggestions.append(
            f"Moderate strategy: {stock_pct}% stocks, {etf_pct}% ETFs, {cash_pct}% dip reserve."
        )

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
