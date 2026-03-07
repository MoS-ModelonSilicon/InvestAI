GOAL_SCORES = {
    "retirement": 4,
    "wealth_growth": 6,
    "passive_income": 3,
    "short_term": 1,
}

TIMELINE_SCORES = {
    "less_1": 1,
    "1_5": 3,
    "5_10": 6,
    "10_plus": 9,
}

EXPERIENCE_SCORES = {
    "beginner": 2,
    "intermediate": 5,
    "advanced": 8,
}

REACTION_SCORES = {
    "sell_all": 1,
    "sell_some": 3,
    "hold": 6,
    "buy_more": 9,
}

STABILITY_SCORES = {
    "stable": 7,
    "variable": 4,
    "uncertain": 2,
}

PROFILE_LABELS = {
    (1, 2): "Very Conservative",
    (3, 4): "Conservative",
    (5, 6): "Moderate",
    (7, 8): "Growth",
    (9, 10): "Aggressive",
}

ALLOCATIONS = {
    "Very Conservative": {"stocks": 15, "bonds": 55, "cash": 30},
    "Conservative": {"stocks": 30, "bonds": 50, "cash": 20},
    "Moderate": {"stocks": 55, "bonds": 35, "cash": 10},
    "Growth": {"stocks": 75, "bonds": 20, "cash": 5},
    "Aggressive": {"stocks": 90, "bonds": 8, "cash": 2},
}


def calculate_risk_score(
    goal: str,
    timeline: str,
    investment_style: str,
    initial_investment: float,
    monthly_investment: float,
    experience: str,
    risk_reaction: str,
    income_stability: str,
) -> tuple[int, str]:
    raw = (
        GOAL_SCORES.get(goal, 5) * 0.15
        + TIMELINE_SCORES.get(timeline, 5) * 0.25
        + EXPERIENCE_SCORES.get(experience, 5) * 0.15
        + REACTION_SCORES.get(risk_reaction, 5) * 0.30
        + STABILITY_SCORES.get(income_stability, 5) * 0.15
    )

    # Lump-sum-only investors with large amounts get a slight conservatism
    # nudge -- losing 20% of $1M hurts more than losing 20% of $500/mo.
    total_capital = initial_investment + (monthly_investment * 12)
    if total_capital > 500_000 and investment_style != "monthly":
        raw = raw * 0.92
    elif total_capital > 100_000 and investment_style != "monthly":
        raw = raw * 0.96

    score = max(1, min(10, round(raw)))

    label = "Moderate"
    for (lo, hi), lbl in PROFILE_LABELS.items():
        if lo <= score <= hi:
            label = lbl
            break

    return score, label


def get_allocation(profile_label: str) -> dict:
    return ALLOCATIONS.get(profile_label, ALLOCATIONS["Moderate"])


def format_total_investment(style: str, initial: float, monthly: float) -> str:
    parts = []
    if initial > 0:
        parts.append(f"${initial:,.0f} lump sum")
    if monthly > 0:
        parts.append(f"${monthly:,.0f}/mo recurring")
    return " + ".join(parts) if parts else "Not specified"
