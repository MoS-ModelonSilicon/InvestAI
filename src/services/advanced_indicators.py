"""
Advanced Technical Indicators.

New indicators beyond the existing set in technical_analysis.py:
  - VWAP (Volume Weighted Average Price)
  - Keltner Channels + TTM Squeeze detection
  - Parabolic SAR (Stop and Reverse)
  - Williams %R
  - Chaikin Money Flow (CMF)
  - Donchian Channels (Turtle Trading)
  - Aroon Indicator
  - CCI (Commodity Channel Index)
  - Heikin-Ashi candle transformation
  - Force Index
  - Linear Regression Channel
  - Momentum & Rate of Change

Each indicator returns visualization-ready data.
"""

from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════════
# 1. VWAP — Volume Weighted Average Price
# ═══════════════════════════════════════════════════════════════════════════


def vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> list[Optional[float]]:
    """
    Cumulative intraday VWAP. For daily data, this computes a rolling
    VWAP that resets monthly.
    """
    n = len(closes)
    if n == 0:
        return []

    result: list[Optional[float]] = []
    cum_vol = 0.0
    cum_tp_vol = 0.0

    for i in range(n):
        typical = (highs[i] + lows[i] + closes[i]) / 3
        cum_vol += volumes[i]
        cum_tp_vol += typical * volumes[i]

        # Reset monthly (every ~21 trading days)
        if i > 0 and i % 21 == 0:
            cum_vol = volumes[i]
            cum_tp_vol = typical * volumes[i]

        if cum_vol > 0:
            result.append(round(cum_tp_vol / cum_vol, 4))
        else:
            result.append(None)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. KELTNER CHANNELS + TTM SQUEEZE
# ═══════════════════════════════════════════════════════════════════════════


def keltner_channels(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 1.5,
) -> dict[str, list[Optional[float]]]:
    """
    Keltner Channel: EMA ± multiplier * ATR.
    Returns {upper, middle, lower}.
    """
    from src.services.technical_analysis import ema, atr

    mid = ema(closes, ema_period)
    atr_vals = atr(highs, lows, closes, atr_period)
    n = len(closes)

    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []

    for i in range(n):
        m_val = mid[i]
        a_val = atr_vals[i]
        if m_val is not None and a_val is not None:
            upper.append(round(m_val + multiplier * a_val, 4))
            lower.append(round(m_val - multiplier * a_val, 4))
        else:
            upper.append(None)
            lower.append(None)

    return {"upper": upper, "middle": mid, "lower": lower}


def ttm_squeeze(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    bb_period: int = 20,
    bb_mult: float = 2.0,
    kc_period: int = 20,
    kc_mult: float = 1.5,
) -> dict[str, Any]:
    """
    TTM Squeeze: detects when Bollinger Bands are inside Keltner Channels,
    indicating a volatility squeeze about to fire.

    Returns {squeeze_on: list[bool], momentum: list[float],
             current_squeeze, signal, detail}.
    """
    from src.services.technical_analysis import bollinger_bands

    bb = bollinger_bands(closes, bb_period, bb_mult)
    kc = keltner_channels(highs, lows, closes, kc_period, 10, kc_mult)
    n = len(closes)

    squeeze_on: list[Optional[bool]] = []
    momentum: list[Optional[float]] = []

    for i in range(n):
        bb_u = bb["upper"][i]
        bb_l = bb["lower"][i]
        kc_u = kc["upper"][i]
        kc_l = kc["lower"][i]
        if bb_u is not None and kc_u is not None and bb_l is not None and kc_l is not None:
            # Squeeze = BB inside KC
            sq = bb_l > kc_l and bb_u < kc_u
            squeeze_on.append(sq)
        else:
            squeeze_on.append(None)

        # Simple momentum: close - midline of donchian
        if i >= 20:
            highest = max(highs[i - 19 : i + 1])
            lowest = min(lows[i - 19 : i + 1])
            mid_dc = (highest + lowest) / 2
            bb_mid = bb["middle"][i]
            mid_bb: float = bb_mid if bb_mid is not None else closes[i]
            avg_mid = (mid_dc + mid_bb) / 2
            momentum.append(round(closes[i] - avg_mid, 4))
        else:
            momentum.append(None)

    # Current state
    recent_squeeze = [s for s in squeeze_on[-5:] if s is not None]
    any_recent = any(s for s in recent_squeeze) if recent_squeeze else False
    was_squeeze = len(recent_squeeze) >= 3 and any(recent_squeeze[:-1]) and not recent_squeeze[-1]
    recent_mom = [m for m in momentum[-3:] if m is not None]
    mom_direction = "bullish" if recent_mom and recent_mom[-1] > 0 else "bearish" if recent_mom else "neutral"

    if was_squeeze:
        detail = f"Squeeze FIRED! Momentum {mom_direction} — expect explosive move"
        signal = 1.5 if mom_direction == "bullish" else -1.5
    elif any_recent:
        detail = f"Squeeze ON (building) — volatility compression, breakout imminent"
        signal = 0.3 if mom_direction == "bullish" else -0.3
    else:
        detail = "No squeeze — normal volatility"
        signal = 0

    return {
        "squeeze_on": squeeze_on,
        "momentum": momentum,
        "keltner": kc,
        "current_squeeze": any_recent,
        "squeeze_fired": was_squeeze,
        "signal": signal,
        "detail": detail,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. PARABOLIC SAR — Stop and Reverse (Wilder, 1978)
# ═══════════════════════════════════════════════════════════════════════════


def parabolic_sar(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    af_start: float = 0.02,
    af_step: float = 0.02,
    af_max: float = 0.20,
) -> dict[str, list[Optional[float]]]:
    """
    Parabolic SAR. Returns {sar: list, trend: list (1=up, -1=down)}.
    When SAR crosses price, trend reverses.
    """
    n = len(closes)
    if n < 3:
        return {"sar": [None] * n, "trend": [None] * n}

    sar: list[Optional[float]] = [None] * n
    trend: list[Optional[float]] = [None] * n

    # Initialize
    is_up = closes[1] > closes[0]
    af = af_start
    ep = highs[0] if is_up else lows[0]
    sar_val = lows[0] if is_up else highs[0]

    for i in range(1, n):
        prev_sar = sar_val

        if is_up:
            sar_val = prev_sar + af * (ep - prev_sar)
            sar_val = min(sar_val, lows[i - 1])
            if i >= 2:
                sar_val = min(sar_val, lows[i - 2])
        else:
            sar_val = prev_sar + af * (ep - prev_sar)
            sar_val = max(sar_val, highs[i - 1])
            if i >= 2:
                sar_val = max(sar_val, highs[i - 2])

        # Check for reversal
        reverse = False
        if is_up and lows[i] < sar_val:
            reverse = True
            is_up = False
            sar_val = ep
            ep = lows[i]
            af = af_start
        elif not is_up and highs[i] > sar_val:
            reverse = True
            is_up = True
            sar_val = ep
            ep = highs[i]
            af = af_start

        if not reverse:
            if is_up:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)

        sar[i] = round(sar_val, 4)
        trend[i] = 1 if is_up else -1

    return {"sar": sar, "trend": trend}


# ═══════════════════════════════════════════════════════════════════════════
# 4. WILLIAMS %R
# ═══════════════════════════════════════════════════════════════════════════


def williams_r(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[Optional[float]]:
    """
    Williams %R oscillator. Range: -100 to 0.
    > -20: overbought. < -80: oversold.
    """
    n = len(closes)
    result: list[Optional[float]] = []

    for i in range(n):
        if i < period - 1:
            result.append(None)
        else:
            hh = max(highs[i - period + 1 : i + 1])
            ll = min(lows[i - period + 1 : i + 1])
            if hh == ll:
                result.append(-50.0)
            else:
                wr = (hh - closes[i]) / (hh - ll) * -100
                result.append(round(wr, 2))

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 5. CHAIKIN MONEY FLOW (CMF)
# ═══════════════════════════════════════════════════════════════════════════


def chaikin_money_flow(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    period: int = 20,
) -> list[Optional[float]]:
    """
    CMF = Sum(Money Flow Volume) / Sum(Volume) over period.
    Range: -1 to +1. Positive = buying pressure. Negative = selling.
    """
    n = len(closes)
    result: list[Optional[float]] = []

    for i in range(n):
        if i < period - 1:
            result.append(None)
        else:
            mfv_sum = 0.0
            vol_sum = 0.0
            for j in range(i - period + 1, i + 1):
                hl = highs[j] - lows[j]
                if hl > 0:
                    mfm = ((closes[j] - lows[j]) - (highs[j] - closes[j])) / hl
                else:
                    mfm = 0.0
                mfv_sum += mfm * volumes[j]
                vol_sum += volumes[j]
            if vol_sum > 0:
                result.append(round(mfv_sum / vol_sum, 4))
            else:
                result.append(0.0)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 6. DONCHIAN CHANNELS (Turtle Trading, Richard Dennis)
# ═══════════════════════════════════════════════════════════════════════════


def donchian_channels(
    highs: list[float],
    lows: list[float],
    period: int = 20,
) -> dict[str, list[Optional[float]]]:
    """
    Donchian Channel = highest high / lowest low over N periods.
    Returns {upper, middle, lower}.
    """
    n = len(highs)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    middle: list[Optional[float]] = []

    for i in range(n):
        if i < period - 1:
            upper.append(None)
            lower.append(None)
            middle.append(None)
        else:
            hh = max(highs[i - period + 1 : i + 1])
            ll = min(lows[i - period + 1 : i + 1])
            upper.append(round(hh, 4))
            lower.append(round(ll, 4))
            middle.append(round((hh + ll) / 2, 4))

    return {"upper": upper, "middle": middle, "lower": lower}


# ═══════════════════════════════════════════════════════════════════════════
# 7. AROON INDICATOR
# ═══════════════════════════════════════════════════════════════════════════


def aroon(
    highs: list[float],
    lows: list[float],
    period: int = 25,
) -> dict[str, list[Optional[float]]]:
    """
    Aroon Up/Down: how recently the highest high / lowest low occurred.
    Range: 0-100. Both > 70 = strong trend. Crossovers signal changes.
    Returns {up, down, oscillator}.
    """
    n = len(highs)
    aroon_up: list[Optional[float]] = []
    aroon_down: list[Optional[float]] = []
    oscillator: list[Optional[float]] = []

    for i in range(n):
        if i < period:
            aroon_up.append(None)
            aroon_down.append(None)
            oscillator.append(None)
        else:
            window_h = highs[i - period : i + 1]
            window_l = lows[i - period : i + 1]
            hh_idx = window_h.index(max(window_h))
            ll_idx = window_l.index(min(window_l))
            up = round(hh_idx / period * 100, 2)
            down = round(ll_idx / period * 100, 2)
            aroon_up.append(up)
            aroon_down.append(down)
            oscillator.append(round(up - down, 2))

    return {"up": aroon_up, "down": aroon_down, "oscillator": oscillator}


# ═══════════════════════════════════════════════════════════════════════════
# 8. CCI — Commodity Channel Index (Donald Lambert, 1980)
# ═══════════════════════════════════════════════════════════════════════════


def cci(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 20,
) -> list[Optional[float]]:
    """
    CCI = (Typical Price - SMA of TP) / (0.015 * Mean Deviation).
    > +100: overbought / strong uptrend. < -100: oversold / strong downtrend.
    """
    n = len(closes)
    result: list[Optional[float]] = []
    tp_list = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(n)]

    for i in range(n):
        if i < period - 1:
            result.append(None)
        else:
            window = tp_list[i - period + 1 : i + 1]
            sma_tp = sum(window) / period
            mean_dev = sum(abs(v - sma_tp) for v in window) / period
            if mean_dev > 0:
                result.append(round((tp_list[i] - sma_tp) / (0.015 * mean_dev), 2))
            else:
                result.append(0.0)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 9. HEIKIN-ASHI Candle Transformation
# ═══════════════════════════════════════════════════════════════════════════


def heikin_ashi(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> dict[str, list[float]]:
    """
    Transform OHLC to Heikin-Ashi candles for smoother trend visualization.
    Returns {open, high, low, close} lists.
    """
    n = len(closes)
    if n == 0:
        return {"open": [], "high": [], "low": [], "close": []}

    ha_close: list[float] = []
    ha_open: list[float] = []
    ha_high: list[float] = []
    ha_low: list[float] = []

    for i in range(n):
        ha_c = round((opens[i] + highs[i] + lows[i] + closes[i]) / 4, 4)
        if i == 0:
            ha_o = round((opens[0] + closes[0]) / 2, 4)
        else:
            ha_o = round((ha_open[i - 1] + ha_close[i - 1]) / 2, 4)
        ha_h = max(highs[i], ha_o, ha_c)
        ha_l = min(lows[i], ha_o, ha_c)

        ha_close.append(ha_c)
        ha_open.append(ha_o)
        ha_high.append(round(ha_h, 4))
        ha_low.append(round(ha_l, 4))

    return {"open": ha_open, "high": ha_high, "low": ha_low, "close": ha_close}


# ═══════════════════════════════════════════════════════════════════════════
# 10. FORCE INDEX (Alexander Elder)
# ═══════════════════════════════════════════════════════════════════════════


def force_index(
    closes: list[float],
    volumes: list[float],
    period: int = 13,
) -> list[Optional[float]]:
    """
    Force Index = EMA(close_change * volume, period).
    Positive = bulls in control. Negative = bears.
    """
    n = len(closes)
    if n < 2:
        return [None] * n

    raw: list[float] = [0.0]
    for i in range(1, n):
        raw.append((closes[i] - closes[i - 1]) * volumes[i])

    from src.services.technical_analysis import ema

    return ema(raw, period)


# ═══════════════════════════════════════════════════════════════════════════
# 11. LINEAR REGRESSION CHANNEL
# ═══════════════════════════════════════════════════════════════════════════


def linear_regression(
    closes: list[float],
    period: int = 50,
) -> dict[str, list[Optional[float]]]:
    """
    Linear regression line + upper/lower channel (±2 std dev).
    Returns {line, upper, lower, slope, r_squared}.
    """
    n = len(closes)
    line: list[Optional[float]] = [None] * n
    upper: list[Optional[float]] = [None] * n
    lower: list[Optional[float]] = [None] * n
    slope_list: list[Optional[float]] = [None] * n
    r2_list: list[Optional[float]] = [None] * n

    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        x_mean = (period - 1) / 2
        y_mean = sum(window) / period

        sum_xy = sum((j - x_mean) * (window[j] - y_mean) for j in range(period))
        sum_x2 = sum((j - x_mean) ** 2 for j in range(period))

        if sum_x2 == 0:
            continue

        slope = sum_xy / sum_x2
        intercept = y_mean - slope * x_mean

        # Regression value at current position
        reg_val = intercept + slope * (period - 1)
        line[i] = round(reg_val, 4)
        slope_list[i] = round(slope, 6)

        # Standard deviation from regression
        residuals = [window[j] - (intercept + slope * j) for j in range(period)]
        std = (sum(r**2 for r in residuals) / period) ** 0.5
        upper[i] = round(reg_val + 2 * std, 4)
        lower[i] = round(reg_val - 2 * std, 4)

        # R-squared
        ss_res = sum(r**2 for r in residuals)
        ss_tot = sum((window[j] - y_mean) ** 2 for j in range(period))
        r2_list[i] = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0

    return {"line": line, "upper": upper, "lower": lower, "slope": slope_list, "r_squared": r2_list}


# ═══════════════════════════════════════════════════════════════════════════
# 12. MOMENTUM & RATE OF CHANGE
# ═══════════════════════════════════════════════════════════════════════════


def momentum(closes: list[float], period: int = 10) -> list[Optional[float]]:
    """Price momentum = close - close[n periods ago]."""
    result: list[Optional[float]] = [None] * period
    for i in range(period, len(closes)):
        result.append(round(closes[i] - closes[i - period], 4))
    return result


def rate_of_change(closes: list[float], period: int = 10) -> list[Optional[float]]:
    """ROC = (close - close[n]) / close[n] * 100."""
    result: list[Optional[float]] = [None] * period
    for i in range(period, len(closes)):
        if closes[i - period] != 0:
            result.append(round((closes[i] - closes[i - period]) / closes[i - period] * 100, 2))
        else:
            result.append(None)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# MASTER: Compute all advanced indicators at once
# ═══════════════════════════════════════════════════════════════════════════


def compute_all_advanced(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> dict[str, Any]:
    """
    Compute all advanced indicators in a single pass.
    Returns a dict keyed by indicator name, each with its data arrays.
    """
    result: dict[str, Any] = {}

    result["vwap"] = vwap(highs, lows, closes, volumes)
    result["keltner"] = keltner_channels(highs, lows, closes)
    result["ttm_squeeze"] = ttm_squeeze(highs, lows, closes)
    result["parabolic_sar"] = parabolic_sar(highs, lows, closes)
    result["williams_r"] = williams_r(highs, lows, closes)
    result["cmf"] = chaikin_money_flow(highs, lows, closes, volumes)
    result["donchian"] = donchian_channels(highs, lows)
    result["aroon"] = aroon(highs, lows)
    result["cci"] = cci(highs, lows, closes)
    result["heikin_ashi"] = heikin_ashi(opens, highs, lows, closes)
    result["force_index"] = force_index(closes, volumes)
    result["linear_regression"] = linear_regression(closes)
    result["momentum"] = momentum(closes)
    result["roc"] = rate_of_change(closes)

    # Build an aggregate advanced signal score
    adv_score = 0.0
    adv_signals: list[dict[str, Any]] = []

    # TTM Squeeze signal
    sq = result["ttm_squeeze"]
    if sq["signal"] != 0:
        adv_score += sq["signal"] * 0.3
        adv_signals.append(
            {
                "name": "TTM Squeeze",
                "score": sq["signal"],
                "direction": "bullish" if sq["signal"] > 0 else "bearish",
                "detail": sq["detail"],
            }
        )

    # Parabolic SAR trend
    sar = result["parabolic_sar"]
    if sar["trend"] and sar["trend"][-1] is not None:
        sar_dir = "bullish" if sar["trend"][-1] > 0 else "bearish"
        sar_score = 0.5 if sar_dir == "bullish" else -0.5
        adv_score += sar_score * 0.2
        adv_signals.append(
            {
                "name": "Parabolic SAR",
                "score": sar_score,
                "direction": sar_dir,
                "detail": f"SAR trend: {sar_dir} — price {'above' if sar_dir == 'bullish' else 'below'} SAR",
            }
        )

    # Williams %R
    wr_vals = result["williams_r"]
    wr = wr_vals[-1] if wr_vals and wr_vals[-1] is not None else None
    if wr is not None:
        if wr > -20:
            adv_score -= 0.2
            adv_signals.append(
                {
                    "name": "Williams %R",
                    "score": -0.5,
                    "direction": "bearish",
                    "detail": f"Williams %R = {wr:.0f} — overbought",
                }
            )
        elif wr < -80:
            adv_score += 0.2
            adv_signals.append(
                {
                    "name": "Williams %R",
                    "score": 0.5,
                    "direction": "bullish",
                    "detail": f"Williams %R = {wr:.0f} — oversold",
                }
            )

    # CMF
    cmf_vals = result["cmf"]
    cmf_val = cmf_vals[-1] if cmf_vals and cmf_vals[-1] is not None else None
    if cmf_val is not None:
        if cmf_val > 0.1:
            adv_score += 0.15
            adv_signals.append(
                {
                    "name": "CMF",
                    "score": 0.5,
                    "direction": "bullish",
                    "detail": f"CMF = {cmf_val:.3f} — buying pressure",
                }
            )
        elif cmf_val < -0.1:
            adv_score -= 0.15
            adv_signals.append(
                {
                    "name": "CMF",
                    "score": -0.5,
                    "direction": "bearish",
                    "detail": f"CMF = {cmf_val:.3f} — selling pressure",
                }
            )

    # Aroon
    ar = result["aroon"]
    if ar["oscillator"] and ar["oscillator"][-1] is not None:
        osc = ar["oscillator"][-1]
        if osc > 50:
            adv_score += 0.15
            adv_signals.append(
                {
                    "name": "Aroon",
                    "score": 0.5,
                    "direction": "bullish",
                    "detail": f"Aroon osc = {osc:.0f} — strong uptrend",
                }
            )
        elif osc < -50:
            adv_score -= 0.15
            adv_signals.append(
                {
                    "name": "Aroon",
                    "score": -0.5,
                    "direction": "bearish",
                    "detail": f"Aroon osc = {osc:.0f} — strong downtrend",
                }
            )

    # CCI
    cci_vals = result["cci"]
    cci_val = cci_vals[-1] if cci_vals and cci_vals[-1] is not None else None
    if cci_val is not None:
        if cci_val > 100:
            adv_score -= 0.1
            adv_signals.append(
                {"name": "CCI", "score": -0.3, "direction": "bearish", "detail": f"CCI = {cci_val:.0f} — overbought"}
            )
        elif cci_val < -100:
            adv_score += 0.1
            adv_signals.append(
                {"name": "CCI", "score": 0.3, "direction": "bullish", "detail": f"CCI = {cci_val:.0f} — oversold"}
            )

    # Linear regression slope
    lr = result["linear_regression"]
    if lr["slope"] and lr["slope"][-1] is not None:
        slope = lr["slope"][-1]
        price = closes[-1] if closes else 1
        slope_pct = slope / price * 100 if price > 0 else 0
        if slope_pct > 0.3:
            adv_score += 0.1
            adv_signals.append(
                {
                    "name": "Regression",
                    "score": 0.3,
                    "direction": "bullish",
                    "detail": f"Linear regression slope +{slope_pct:.2f}%/day",
                }
            )
        elif slope_pct < -0.3:
            adv_score -= 0.1
            adv_signals.append(
                {
                    "name": "Regression",
                    "score": -0.3,
                    "direction": "bearish",
                    "detail": f"Linear regression slope {slope_pct:.2f}%/day",
                }
            )

    result["advanced_score"] = round(adv_score, 3)
    result["advanced_signals"] = adv_signals

    return result
