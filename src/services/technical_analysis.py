"""
Pure-math technical indicator computations on lists.

All functions take plain Python lists (close prices, high, low, volume)
and return lists of the same length, padded with None where insufficient
data exists for the lookback window.

Advanced indicators inspired by quantitative trading research:
- Divergence detection (RSI/MACD vs price) -- Wyckoff / Andrew Cardwell
- ADX trend strength -- Wilder 1978
- Accumulation/Distribution -- Marc Chaikin
- Mean reversion Z-score -- statistical arbitrage (DE Shaw, Two Sigma approach)
- Volume anomaly detection -- institutional flow analysis
- Ichimoku Cloud -- Goichi Hosoda, 1968
- Fibonacci swing levels -- auto-detected retracements
- Relative strength vs benchmark -- O'Neil CANSLIM / sector rotation
"""

from collections.abc import Sequence
from typing import Any, Optional, cast


# ---------------------------------------------------------------------------
# Moving Averages
# ---------------------------------------------------------------------------


def sma(values: list[float], period: int) -> list[Optional[float]]:
    """Simple Moving Average."""
    result: list[Optional[float]] = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1 : i + 1]
            result.append(round(sum(window) / period, 4))
    return result


def ema(values: list[float], period: int) -> list[Optional[float]]:
    """Exponential Moving Average."""
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    result: list[Optional[float]] = [None] * (period - 1)
    seed = sum(values[:period]) / period
    result.append(round(seed, 4))
    for i in range(period, len(values)):
        prev = result[-1]
        if prev is None:
            result.append(None)
            continue
        val = values[i] * k + prev * (1 - k)
        result.append(round(val, 4))
    return result


# ---------------------------------------------------------------------------
# RSI  (Wilder, 1978)
# ---------------------------------------------------------------------------


def rsi(closes: list[float], period: int = 14) -> list[Optional[float]]:
    """Relative Strength Index (0-100)."""
    if len(closes) < period + 1:
        return [None] * len(closes)

    result: list[Optional[float]] = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(round(100 - 100 / (1 + rs), 2))

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - 100 / (1 + rs), 2))

    return result


# ---------------------------------------------------------------------------
# MACD  (Appel, 1979)
# ---------------------------------------------------------------------------


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9
) -> dict[str, list[Optional[float]]]:
    """Returns {line, signal, histogram} lists."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    line: list[Optional[float]] = []
    for f, s in zip(ema_fast, ema_slow):
        if f is None or s is None:
            line.append(None)
        else:
            line.append(round(f - s, 4))

    non_none = [v for v in line if v is not None]
    sig = ema(non_none, signal_period) if len(non_none) >= signal_period else [None] * len(non_none)

    signal_full: list[Optional[float]] = []
    sig_idx = 0
    for v in line:
        if v is None:
            signal_full.append(None)
        else:
            if sig_idx < len(sig):
                signal_full.append(sig[sig_idx])
                sig_idx += 1
            else:
                signal_full.append(None)

    histogram: list[Optional[float]] = []
    for l_val, s_val in zip(line, signal_full):
        if l_val is None or s_val is None:
            histogram.append(None)
        else:
            histogram.append(round(l_val - s_val, 4))

    return {"line": line, "signal": signal_full, "histogram": histogram}


# ---------------------------------------------------------------------------
# Bollinger Bands  (Bollinger, 1980s)
# ---------------------------------------------------------------------------


def bollinger_bands(closes: list[float], period: int = 20, num_std: float = 2.0) -> dict[str, list[Optional[float]]]:
    """Returns {upper, middle, lower, pct_b} lists."""
    middle = sma(closes, period)
    upper: list[Optional[float]] = []
    lower: list[Optional[float]] = []
    pct_b: list[Optional[float]] = []

    for i in range(len(closes)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
            pct_b.append(None)
        else:
            window = closes[i - period + 1 : i + 1]
            mean: float = middle[i]  # type: ignore[assignment]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance**0.5
            u = round(mean + num_std * std, 4)
            l = round(mean - num_std * std, 4)
            upper.append(u)
            lower.append(l)
            if u != l:
                pct_b.append(round((closes[i] - l) / (u - l), 4))
            else:
                pct_b.append(0.5)

    return {"upper": upper, "middle": middle, "lower": lower, "pct_b": pct_b}


# ---------------------------------------------------------------------------
# Stochastic Oscillator  (Lane, 1950s)
# ---------------------------------------------------------------------------


def stochastic(
    highs: list[float], lows: list[float], closes: list[float], k_period: int = 14, d_period: int = 3
) -> dict[str, list[Optional[float]]]:
    """Returns {k, d} lists (0-100)."""
    k_vals: list[Optional[float]] = []
    for i in range(len(closes)):
        if i < k_period - 1:
            k_vals.append(None)
        else:
            h_window = highs[i - k_period + 1 : i + 1]
            l_window = lows[i - k_period + 1 : i + 1]
            hh = max(h_window)
            ll = min(l_window)
            if hh == ll:
                k_vals.append(50.0)
            else:
                k_vals.append(round((closes[i] - ll) / (hh - ll) * 100, 2))

    non_none_k = [v for v in k_vals if v is not None]
    d_raw = sma(non_none_k, d_period) if len(non_none_k) >= d_period else [None] * len(non_none_k)

    d_vals: list[Optional[float]] = []
    d_idx = 0
    for v in k_vals:
        if v is None:
            d_vals.append(None)
        else:
            if d_idx < len(d_raw):
                d_vals.append(d_raw[d_idx])
                d_idx += 1
            else:
                d_vals.append(None)

    return {"k": k_vals, "d": d_vals}


# ---------------------------------------------------------------------------
# ATR  (Wilder, 1978)
# ---------------------------------------------------------------------------


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    """Average True Range."""
    if len(closes) < 2:
        return [None] * len(closes)

    tr_vals = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_vals.append(tr)

    result: list[Optional[float]] = [None] * (period - 1)
    if len(tr_vals) >= period:
        first_atr = sum(tr_vals[:period]) / period
        result.append(round(first_atr, 4))
        for i in range(period, len(tr_vals)):
            prev = result[-1]
            if prev is None:
                result.append(None)
                continue
            val = (prev * (period - 1) + tr_vals[i]) / period
            result.append(round(val, 4))

    return result


# ---------------------------------------------------------------------------
# OBV  (Granville, 1963)
# ---------------------------------------------------------------------------


def obv(closes: list[float], volumes: list[float]) -> list[float]:
    """On-Balance Volume."""
    if not closes:
        return []
    result = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result.append(result[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(result[-1] - volumes[i])
        else:
            result.append(result[-1])
    return result


# ---------------------------------------------------------------------------
# ADX -- Average Directional Index (Wilder, 1978)
# Measures trend STRENGTH, not direction. ADX > 25 = trending, < 20 = ranging.
# ---------------------------------------------------------------------------


def adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> dict[str, list[Optional[float]]]:
    """
    Average Directional Index. Returns {adx, plus_di, minus_di}.
    ADX range: 0-100. >25 = trending, <20 = ranging.
    """
    n = len(closes)
    if n < period * 2 + 1:
        return {"adx": [None] * n, "plus_di": [None] * n, "minus_di": [None] * n}

    plus_di_out: list[Optional[float]] = [None] * n
    minus_di_out: list[Optional[float]] = [None] * n
    adx_out: list[Optional[float]] = [None] * n

    tr_list, pdm_list, mdm_list = [], [], []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        up = highs[i] - highs[i - 1]
        dn = lows[i - 1] - lows[i]
        tr_list.append(tr)
        pdm_list.append(up if up > dn and up > 0 else 0.0)
        mdm_list.append(dn if dn > up and dn > 0 else 0.0)

    # Wilder smoothing of TR, +DM, -DM
    atr14 = sum(tr_list[:period]) / period
    pdm14 = sum(pdm_list[:period]) / period
    mdm14 = sum(mdm_list[:period]) / period

    dx_list: list[float] = []
    for i in range(period - 1, len(tr_list)):
        if i == period - 1:
            s_tr, s_pdm, s_mdm = atr14, pdm14, mdm14
        else:
            s_tr = (s_tr * (period - 1) + tr_list[i]) / period
            s_pdm = (s_pdm * (period - 1) + pdm_list[i]) / period
            s_mdm = (s_mdm * (period - 1) + mdm_list[i]) / period

        pdi = 100 * s_pdm / s_tr if s_tr > 0 else 0
        mdi = 100 * s_mdm / s_tr if s_tr > 0 else 0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0

        out_idx = i + 1  # +1 because tr_list is offset by 1
        plus_di_out[out_idx] = round(pdi, 2)
        minus_di_out[out_idx] = round(mdi, 2)
        dx_list.append(dx)

    # ADX = Wilder-smoothed DX
    if len(dx_list) >= period:
        adx_val = sum(dx_list[:period]) / period
        adx_start = period + period  # first ADX position in output
        if adx_start < n:
            adx_out[adx_start] = round(adx_val, 2)
            for j in range(period, len(dx_list)):
                adx_val = (adx_val * (period - 1) + dx_list[j]) / period
                out_idx = j + period + 1
                if out_idx < n:
                    adx_out[out_idx] = round(adx_val, 2)

    return {"adx": adx_out, "plus_di": plus_di_out, "minus_di": minus_di_out}


# ---------------------------------------------------------------------------
# Divergence Detection (RSI & MACD vs Price)
# The most powerful predictive signal in technical analysis.
# Bullish divergence: price makes lower low but oscillator makes higher low
# Bearish divergence: price makes higher high but oscillator makes lower high
# ---------------------------------------------------------------------------


def _find_swing_points(data: "Sequence[Optional[float]]", window: int = 5) -> list[tuple[int, float, str]]:
    """Find local minima and maxima in a series."""
    points: list[tuple[int, float, str]] = []
    vals = [(i, v) for i, v in enumerate(data) if v is not None]
    if len(vals) < window * 2 + 1:
        return points
    for idx in range(window, len(vals) - window):
        i, v = vals[idx]
        left = [vals[j][1] for j in range(idx - window, idx)]
        right = [vals[j][1] for j in range(idx + 1, idx + window + 1)]
        if v <= min(left) and v <= min(right):
            points.append((i, v, "low"))
        if v >= max(left) and v >= max(right):
            points.append((i, v, "high"))
    return points


def detect_divergence(closes: list[float], oscillator: list[Optional[float]], lookback: int = 60) -> dict[str, Any]:
    """
    Detect bullish and bearish divergences between price and an oscillator.

    Returns {bullish_div, bearish_div, bull_strength, bear_strength,
             bull_detail, bear_detail}
    """
    result = {
        "bullish_div": False,
        "bearish_div": False,
        "bull_strength": 0,
        "bear_strength": 0,
        "bull_detail": "",
        "bear_detail": "",
    }

    n = len(closes)
    if n < lookback:
        return result

    start = max(0, n - lookback)
    price_slice = closes[start:]
    osc_slice = oscillator[start:]

    price_swings = _find_swing_points(price_slice, window=3)
    osc_swings = _find_swing_points(osc_slice, window=3)

    price_lows = [(s[0], s[1]) for s in price_swings if s[2] == "low"]
    price_highs = [(s[0], s[1]) for s in price_swings if s[2] == "high"]
    osc_lows = [(s[0], s[1]) for s in osc_swings if s[2] == "low"]
    osc_highs = [(s[0], s[1]) for s in osc_swings if s[2] == "high"]

    if len(price_lows) >= 2 and len(osc_lows) >= 2:
        pl1, pl2 = price_lows[-2], price_lows[-1]
        ol_candidates = [o for o in osc_lows if abs(o[0] - pl2[0]) <= 8]
        ol_prev_candidates = [o for o in osc_lows if abs(o[0] - pl1[0]) <= 8]

        if ol_candidates and ol_prev_candidates:
            ol2 = min(ol_candidates, key=lambda x: abs(x[0] - pl2[0]))
            ol1 = min(ol_prev_candidates, key=lambda x: abs(x[0] - pl1[0]))
            if pl2[1] < pl1[1] and ol2[1] > ol1[1]:
                price_drop = (pl1[1] - pl2[1]) / pl1[1] * 100
                osc_rise = ol2[1] - ol1[1]
                result["bullish_div"] = True
                result["bull_strength"] = min(round(price_drop * 10 + abs(osc_rise) * 2), 100)
                result["bull_detail"] = (
                    f"Bullish divergence: price fell {price_drop:.1f}% to new low "
                    f"but oscillator formed higher low -- reversal likely"
                )

    if len(price_highs) >= 2 and len(osc_highs) >= 2:
        ph1, ph2 = price_highs[-2], price_highs[-1]
        oh_candidates = [o for o in osc_highs if abs(o[0] - ph2[0]) <= 8]
        oh_prev_candidates = [o for o in osc_highs if abs(o[0] - ph1[0]) <= 8]

        if oh_candidates and oh_prev_candidates:
            oh2 = min(oh_candidates, key=lambda x: abs(x[0] - ph2[0]))
            oh1 = min(oh_prev_candidates, key=lambda x: abs(x[0] - ph1[0]))
            if ph2[1] > ph1[1] and oh2[1] < oh1[1]:
                price_rise = (ph2[1] - ph1[1]) / ph1[1] * 100
                osc_drop = oh1[1] - oh2[1]
                result["bearish_div"] = True
                result["bear_strength"] = min(round(price_rise * 10 + abs(osc_drop) * 2), 100)
                result["bear_detail"] = (
                    f"Bearish divergence: price rose {price_rise:.1f}% to new high "
                    f"but oscillator formed lower high -- potential reversal"
                )

    return result


# ---------------------------------------------------------------------------
# Accumulation/Distribution Line (Marc Chaikin)
# More sophisticated than OBV: uses close position within high-low range.
# ---------------------------------------------------------------------------


def accumulation_distribution(
    highs: list[float], lows: list[float], closes: list[float], volumes: list[float]
) -> list[float]:
    """Chaikin Accumulation/Distribution line."""
    if not closes:
        return []
    result = [0.0]
    for i in range(len(closes)):
        hl = highs[i] - lows[i]
        if hl == 0:
            mfm: float = 0
        else:
            mfm = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        mfv = mfm * volumes[i]
        if i == 0:
            result[0] = mfv
        else:
            result.append(result[-1] + mfv)
    return result


# ---------------------------------------------------------------------------
# Mean Reversion Z-Score (Statistical Arbitrage approach)
# How many standard deviations from the moving average?
# Extreme Z-scores (>2 or <-2) often precede mean reversion.
# ---------------------------------------------------------------------------


def zscore(closes: list[float], period: int = 50) -> list[Optional[float]]:
    """Z-score of price relative to its SMA. Values > 2 or < -2 are extreme."""
    result: list[Optional[float]] = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1 : i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance**0.5
            if std == 0:
                result.append(0)
            else:
                result.append(round((closes[i] - mean) / std, 3))
    return result


# ---------------------------------------------------------------------------
# Volume Anomaly Detection (Institutional Flow Analysis)
# Detects unusual volume patterns that indicate smart money activity.
# ---------------------------------------------------------------------------


def volume_anomaly(closes: list[float], volumes: list[float], period: int = 20) -> dict[str, Any]:
    """
    Detect institutional-grade volume anomalies.

    Returns {
        anomaly_score: 0-100 (how unusual recent volume is),
        accumulation: bool (unusual volume on up days = buying),
        distribution: bool (unusual volume on down days = selling),
        quiet_accumulation: bool (subtle steady buying without price spikes),
        detail: str
    }
    """
    result = {
        "anomaly_score": 0,
        "accumulation": False,
        "distribution": False,
        "quiet_accumulation": False,
        "detail": "Insufficient data",
    }
    n = len(closes)
    if n < period + 5 or len(volumes) < period + 5:
        return result

    avg_vol = sum(volumes[-period:]) / period
    if avg_vol == 0:
        return result

    vol_std = (sum((v - avg_vol) ** 2 for v in volumes[-period:]) / period) ** 0.5
    if vol_std == 0:
        vol_std = 1

    recent_5 = volumes[-5:]
    recent_closes = closes[-5:]
    prev_closes = closes[-6:-1]

    up_volume = sum(v for v, c, pc in zip(recent_5, recent_closes, prev_closes) if c > pc)
    down_volume = sum(v for v, c, pc in zip(recent_5, recent_closes, prev_closes) if c < pc)
    total_recent = sum(recent_5)

    vol_ratio = total_recent / (avg_vol * 5) if avg_vol > 0 else 1
    zscore_vol = (sum(recent_5) / 5 - avg_vol) / vol_std if vol_std > 0 else 0

    anomaly_score = min(int(abs(zscore_vol) * 25), 100)
    result["anomaly_score"] = anomaly_score

    if up_volume > down_volume * 2 and vol_ratio > 1.3:
        result["accumulation"] = True
        result["detail"] = (
            f"Institutional accumulation detected: {vol_ratio:.1f}x avg volume, "
            f"{int(up_volume / max(total_recent, 1) * 100)}% on up days"
        )
    elif down_volume > up_volume * 2 and vol_ratio > 1.3:
        result["distribution"] = True
        result["detail"] = (
            f"Distribution pattern: {vol_ratio:.1f}x avg volume, "
            f"{int(down_volume / max(total_recent, 1) * 100)}% on down days"
        )
    else:
        chaikin_slope = 0
        if n >= 10:
            ad = accumulation_distribution(
                closes[-10:] if len(closes) >= 10 else closes,
                closes[-10:] if len(closes) >= 10 else closes,
                closes[-10:] if len(closes) >= 10 else closes,
                volumes[-10:] if len(volumes) >= 10 else volumes,
            )
            # Wrong: should use actual highs/lows but we only have closes here
            # We'll recalculate in _analyze_stock with proper data
            pass

    # Quiet accumulation: price flat but OBV/A-D trending up
    price_change = abs(closes[-1] - closes[-period]) / closes[-period] * 100 if closes[-period] != 0 else 0
    vol_trend_up = sum(1 for i in range(-5, 0) if volumes[i] > avg_vol) >= 3

    if price_change < 3 and vol_trend_up and up_volume > down_volume * 1.2:
        result["quiet_accumulation"] = True
        if not result["accumulation"]:
            result["detail"] = (
                f"Quiet accumulation: price moved only {price_change:.1f}% "
                f"but volume consistently above average -- smart money positioning"
            )

    if result["detail"] == "Insufficient data":
        result["detail"] = f"Volume {vol_ratio:.1f}x average, no anomaly detected"

    return result


# ---------------------------------------------------------------------------
# Ichimoku Cloud (Goichi Hosoda, 1968)
# Provides support, resistance, trend, and momentum in one indicator.
# ---------------------------------------------------------------------------


def ichimoku(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    tenkan_p: int = 9,
    kijun_p: int = 26,
    senkou_b_p: int = 52,
) -> dict[str, list[Optional[float]]]:
    """
    Returns {tenkan, kijun, senkou_a, senkou_b, chikou}.
    senkou_a and senkou_b are shifted forward by kijun_p periods.
    """
    n = len(closes)

    def _midpoint(h: list[float], l: list[float], period: int, idx: int) -> Optional[float]:
        if idx < period - 1:
            return None
        seg_h = h[idx - period + 1 : idx + 1]
        seg_l = l[idx - period + 1 : idx + 1]
        return round((max(seg_h) + min(seg_l)) / 2, 4)

    tenkan = [_midpoint(highs, lows, tenkan_p, i) for i in range(n)]
    kijun = [_midpoint(highs, lows, kijun_p, i) for i in range(n)]

    senkou_a_raw: list[Optional[float]] = []
    for i in range(n):
        t_val = tenkan[i]
        k_val = kijun[i]
        if t_val is not None and k_val is not None:
            senkou_a_raw.append(round((t_val + k_val) / 2, 4))
        else:
            senkou_a_raw.append(None)
    senkou_a = [None] * kijun_p + senkou_a_raw[: n - kijun_p] if n > kijun_p else [None] * n

    senkou_b_raw = [_midpoint(highs, lows, senkou_b_p, i) for i in range(n)]
    senkou_b = [None] * kijun_p + senkou_b_raw[: n - kijun_p] if n > kijun_p else [None] * n

    chikou = closes[kijun_p:] + [None] * min(kijun_p, n)

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou[:n],
    }


def ichimoku_signal(closes: list[float], ichi: dict[str, list[Optional[float]]]) -> dict[str, Any]:
    """Interpret Ichimoku Cloud state. Returns {signal, strength, detail}."""
    n = len(closes)
    if n < 52:
        return {"signal": 0, "strength": 0, "detail": "Insufficient data for Ichimoku"}

    price = closes[-1]
    tenkan = _last_valid(ichi["tenkan"])
    kijun = _last_valid(ichi["kijun"])
    sa = _last_valid(ichi["senkou_a"])
    sb = _last_valid(ichi["senkou_b"])

    if tenkan is None or kijun is None or sa is None or sb is None:
        return {"signal": 0, "strength": 0, "detail": "Ichimoku data incomplete"}

    cloud_top = max(sa, sb)
    cloud_bottom = min(sa, sb)
    cloud_bullish = sa > sb

    signals = 0
    details = []

    if price > cloud_top:
        signals += 1
        details.append("price above cloud")
    elif price < cloud_bottom:
        signals -= 1
        details.append("price below cloud")
    else:
        details.append("price inside cloud (indecision)")

    if tenkan > kijun:
        signals += 1
        details.append("Tenkan above Kijun (bullish)")
    else:
        signals -= 1
        details.append("Tenkan below Kijun (bearish)")

    if cloud_bullish:
        signals += 1
        details.append("future cloud bullish")
    else:
        signals -= 1
        details.append("future cloud bearish")

    prev_tenkan = _second_last_valid(ichi["tenkan"])
    prev_kijun = _second_last_valid(ichi["kijun"])
    if prev_tenkan is not None and prev_kijun is not None:
        if prev_tenkan <= prev_kijun and tenkan > kijun:
            signals += 1
            details.append("TK cross (bullish)")
        elif prev_tenkan >= prev_kijun and tenkan < kijun:
            signals -= 1
            details.append("TK cross (bearish)")

    strength = min(abs(signals) * 25, 100)
    detail = f"Ichimoku: {', '.join(details)}"

    return {"signal": signals, "strength": strength, "detail": detail}


# ---------------------------------------------------------------------------
# Fibonacci Swing Levels (Auto-detected)
# ---------------------------------------------------------------------------


def fibonacci_levels(closes: list[float], lookback: int = 120) -> dict[str, Any]:
    """
    Auto-detect major swing high/low and compute Fibonacci retracement levels.
    Returns {swing_high, swing_low, levels: {0.236, 0.382, 0.5, 0.618, 0.786}}
    """
    n = len(closes)
    if n < 20:
        return {"swing_high": None, "swing_low": None, "levels": {}}

    window = closes[-min(lookback, n) :]
    swing_high = max(window)
    swing_low = min(window)
    diff = swing_high - swing_low

    if diff == 0:
        return {"swing_high": swing_high, "swing_low": swing_low, "levels": {}}

    current = closes[-1]
    in_uptrend = closes[-1] > closes[-min(lookback, n)]

    if in_uptrend:
        levels = {str(r): round(swing_high - diff * r, 2) for r in [0.236, 0.382, 0.5, 0.618, 0.786]}
    else:
        levels = {str(r): round(swing_low + diff * r, 2) for r in [0.236, 0.382, 0.5, 0.618, 0.786]}

    nearest_support = None
    nearest_resistance = None
    for _label, level in sorted(levels.items(), key=lambda x: x[1]):
        if level < current and (nearest_support is None or level > nearest_support):
            nearest_support = level
        if level > current and nearest_resistance is None:
            nearest_resistance = level

    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "levels": levels,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "current_position": round((current - swing_low) / diff, 3) if diff > 0 else 0.5,
    }


# ---------------------------------------------------------------------------
# Relative Strength vs Benchmark
# Compares stock performance to a benchmark (SPY) over multiple periods.
# Outperformance during market weakness = institutional quality.
# ---------------------------------------------------------------------------


def relative_strength(closes: list[float], benchmark_closes: list[float]) -> dict[str, float | bool | str | None]:
    """
    Compute relative strength metrics vs a benchmark.
    Both lists must be aligned by date and same length.
    """
    result: dict[str, float | bool | str | None] = {
        "rs_ratio": None,
        "rs_1m": None,
        "rs_3m": None,
        "outperforming": False,
        "detail": "",
    }

    n = min(len(closes), len(benchmark_closes))
    if n < 22:
        return result

    def _pct(data: list[float], periods: int) -> float:
        if len(data) < periods + 1:
            return 0
        return (data[-1] - data[-periods]) / data[-periods] * 100

    stock_1m = _pct(closes, 22)
    bench_1m = _pct(benchmark_closes, 22)
    rs_1m = round(stock_1m - bench_1m, 2)
    result["rs_1m"] = rs_1m

    rs_3m: float | None = None
    if n >= 66:
        stock_3m = _pct(closes, 66)
        bench_3m = _pct(benchmark_closes, 66)
        rs_3m = round(stock_3m - bench_3m, 2)
        result["rs_3m"] = rs_3m

    rs_line: list[float | None] = []
    for i in range(n):
        if benchmark_closes[i] != 0:
            rs_line.append(closes[i] / benchmark_closes[i])
        else:
            rs_line.append(None)

    if len(rs_line) >= 2:
        recent_rs = [v for v in rs_line[-22:] if v is not None]
        if len(recent_rs) >= 2:
            result["rs_ratio"] = round(recent_rs[-1] / recent_rs[0], 4)
            result["outperforming"] = recent_rs[-1] > recent_rs[0]

    parts: list[str] = []
    if rs_1m is not None:
        direction = "outperforming" if rs_1m > 0 else "underperforming"
        parts.append(f"1M: {direction} benchmark by {abs(rs_1m):.1f}%")
    if rs_3m is not None:
        direction = "outperforming" if rs_3m > 0 else "underperforming"
        parts.append(f"3M: {direction} by {abs(rs_3m):.1f}%")
    result["detail"] = "; ".join(parts) if parts else "RS data unavailable"

    return result


# ---------------------------------------------------------------------------
# Composite signal scoring
# ---------------------------------------------------------------------------


def _score_rsi(rsi_vals: list[Optional[float]]) -> tuple[float, str]:
    """Score RSI: -2 to +2."""
    v = _last_valid(rsi_vals)
    if v is None:
        return 0, "RSI data unavailable"
    if v < 25:
        return 2, f"RSI {v:.0f} -- heavily oversold, strong buy zone"
    if v < 35:
        return 1, f"RSI {v:.0f} -- oversold, potential buy"
    if v > 80:
        return -2, f"RSI {v:.0f} -- heavily overbought, strong sell zone"
    if v > 70:
        return -1, f"RSI {v:.0f} -- overbought, consider selling"
    return 0, f"RSI {v:.0f} -- neutral"


def _score_macd(macd_data: dict[str, list[Optional[float]]]) -> tuple[float, str]:
    """Score MACD crossover: -2 to +2."""
    line = macd_data["line"]
    sig = macd_data["signal"]
    hist = macd_data["histogram"]

    cur_l = _last_valid(line)
    cur_s = _last_valid(sig)
    cur_h = _last_valid(hist)

    if cur_l is None or cur_s is None or cur_h is None:
        return 0, "MACD data unavailable"

    prev_h = _second_last_valid(hist)
    bullish_cross = cur_l > cur_s and (prev_h is not None and prev_h <= 0 and cur_h > 0)
    bearish_cross = cur_l < cur_s and (prev_h is not None and prev_h >= 0 and cur_h < 0)

    if bullish_cross:
        return 2, "MACD bullish crossover -- strong buy signal"
    if bearish_cross:
        return -2, "MACD bearish crossover -- strong sell signal"
    if cur_l > cur_s and cur_h > 0:
        return 1, "MACD above signal line -- bullish momentum"
    if cur_l < cur_s and cur_h < 0:
        return -1, "MACD below signal line -- bearish momentum"
    return 0, "MACD neutral"


def _score_sma_cross(
    closes: list[float], sma50: list[Optional[float]], sma200: list[Optional[float]]
) -> tuple[float, str]:
    """Score SMA 50/200 position and crossovers."""
    price = closes[-1] if closes else None
    s50 = _last_valid(sma50)
    s200 = _last_valid(sma200)

    if price is None or s50 is None:
        return 0, "SMA data unavailable"

    if s200 is None:
        if price > s50:
            return 0.5, f"Price above SMA 50 (${s50:.0f})"
        return -0.5, f"Price below SMA 50 (${s50:.0f})"

    prev_s50 = _second_last_valid(sma50)
    prev_s200 = _second_last_valid(sma200)
    golden = prev_s50 is not None and prev_s200 is not None and prev_s50 <= prev_s200 and s50 > s200
    death = prev_s50 is not None and prev_s200 is not None and prev_s50 >= prev_s200 and s50 < s200

    if golden:
        return 2, "Golden Cross -- SMA 50 crossed above SMA 200"
    if death:
        return -2, "Death Cross -- SMA 50 crossed below SMA 200"
    if price > s50 > s200:
        return 1.5, f"Strong uptrend -- price above SMA 50 (${s50:.0f}) and 200 (${s200:.0f})"
    if price > s50:
        return 0.5, f"Price above SMA 50 but below SMA 200"
    if price < s50 < s200:
        return -1.5, f"Strong downtrend -- price below both SMAs"
    return -0.5, f"Price below SMA 50"


def _score_bollinger(pct_b_vals: list[Optional[float]]) -> tuple[float, str]:
    """Score Bollinger %B position."""
    v = _last_valid(pct_b_vals)
    if v is None:
        return 0, "Bollinger data unavailable"
    if v < 0.05:
        return 2, f"Bollinger %B {v:.2f} -- at lower band, strong buy"
    if v < 0.2:
        return 1, f"Bollinger %B {v:.2f} -- near lower band, potential buy"
    if v > 0.95:
        return -2, f"Bollinger %B {v:.2f} -- at upper band, strong sell"
    if v > 0.8:
        return -1, f"Bollinger %B {v:.2f} -- near upper band, consider selling"
    return 0, f"Bollinger %B {v:.2f} -- mid-range"


def _score_stochastic(stoch_data: dict[str, list[Optional[float]]]) -> tuple[float, str]:
    """Score Stochastic %K/%D."""
    k = _last_valid(stoch_data["k"])
    d = _last_valid(stoch_data["d"])
    if k is None:
        return 0, "Stochastic data unavailable"

    prev_k = _second_last_valid(stoch_data["k"])
    prev_d = _second_last_valid(stoch_data["d"])

    if k < 20 and d is not None and prev_k is not None and prev_d is not None:
        if prev_k <= prev_d and k > d:
            return 2, f"Stochastic bullish crossover in oversold zone (%K={k:.0f})"
    if k > 80 and d is not None and prev_k is not None and prev_d is not None:
        if prev_k >= prev_d and k < d:
            return -2, f"Stochastic bearish crossover in overbought zone (%K={k:.0f})"

    if k < 20:
        return 1, f"Stochastic %K={k:.0f} -- oversold"
    if k > 80:
        return -1, f"Stochastic %K={k:.0f} -- overbought"
    return 0, f"Stochastic %K={k:.0f} -- neutral"


def _score_obv(obv_vals: list[float], closes: list[float]) -> tuple[float, str]:
    """Score OBV trend vs price trend."""
    if len(obv_vals) < 20 or len(closes) < 20:
        return 0, "Insufficient volume data"

    obv_trend = obv_vals[-1] - obv_vals[-20]
    price_trend = closes[-1] - closes[-20]

    if price_trend > 0 and obv_trend > 0:
        return 1, "Volume confirms uptrend -- OBV rising with price"
    if price_trend < 0 and obv_trend < 0:
        return -1, "Volume confirms downtrend -- OBV falling with price"
    if price_trend > 0 and obv_trend < 0:
        return -1, "Bearish divergence -- price rising but volume declining"
    if price_trend < 0 and obv_trend > 0:
        return 1, "Bullish divergence -- price falling but volume accumulating"
    return 0, "Volume neutral"


def composite_score(
    rsi_vals: list[Optional[float]],
    macd_data: dict[str, list[Optional[float]]],
    closes: list[float],
    sma50: list[Optional[float]],
    sma200: list[Optional[float]],
    boll_pct_b: list[Optional[float]],
    stoch_data: dict[str, list[Optional[float]]],
    obv_vals: list[float],
    *,
    adx_data: Optional[dict[str, list[Optional[float]]]] = None,
    rsi_div: Optional[dict[str, Any]] = None,
    macd_div: Optional[dict[str, Any]] = None,
    vol_anomaly: Optional[dict[str, Any]] = None,
    ichimoku_sig: Optional[dict[str, Any]] = None,
    zscore_vals: Optional[list[Optional[float]]] = None,
    rs_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Advanced weighted composite of all indicators.

    The base score uses 6 classic indicators. Then advanced signals
    (divergences, ADX trend strength, volume anomalies, Ichimoku,
    relative strength, mean reversion) act as score modifiers that
    can boost or penalize the base score.

    Returns {score, raw_score, verdict, confidence, signals[], edge_signals[]}.
    """
    # --- Base indicator scoring (classic) ---
    weights = {
        "macd": 0.22,
        "rsi": 0.18,
        "sma": 0.18,
        "bollinger": 0.14,
        "stochastic": 0.10,
        "obv": 0.08,
        "advanced": 0.10,
    }

    rsi_s, rsi_d = _score_rsi(rsi_vals)
    macd_s, macd_d = _score_macd(macd_data)
    sma_s, sma_d = _score_sma_cross(closes, sma50, sma200)
    boll_s, boll_d = _score_bollinger(boll_pct_b)
    stoch_s, stoch_d = _score_stochastic(stoch_data)
    obv_s, obv_d = _score_obv(obv_vals, closes)

    base_raw = (
        macd_s * weights["macd"]
        + rsi_s * weights["rsi"]
        + sma_s * weights["sma"]
        + boll_s * weights["bollinger"]
        + stoch_s * weights["stochastic"]
        + obv_s * weights["obv"]
    )

    # --- Advanced signal modifiers ---
    advanced_score = 0.0
    edge_signals: list[dict[str, object]] = []

    # ADX: boost confidence when market is trending, penalize in chop
    adx_multiplier = 1.0
    if adx_data:
        adx_val = _last_valid(adx_data.get("adx", []))
        pdi = _last_valid(adx_data.get("plus_di", []))
        mdi = _last_valid(adx_data.get("minus_di", []))
        if adx_val is not None:
            if adx_val > 30:
                adx_multiplier = 1.25
                direction = "bullish" if (pdi or 0) > (mdi or 0) else "bearish"
                edge_signals.append(
                    {
                        "name": "ADX Trend",
                        "score": 1.5 if direction == "bullish" else -1.5,
                        "detail": f"Strong trend (ADX {adx_val:.0f}) -- {direction} directional movement",
                        "direction": direction,
                    }
                )
                advanced_score += 0.5 if direction == "bullish" else -0.5
            elif adx_val < 20:
                adx_multiplier = 0.75
                edge_signals.append(
                    {
                        "name": "ADX Trend",
                        "score": 0,
                        "detail": f"Weak trend (ADX {adx_val:.0f}) -- ranging market, signals less reliable",
                        "direction": "neutral",
                    }
                )

    # Divergences: THE most powerful predictive signal
    if rsi_div and rsi_div.get("bullish_div"):
        boost = min(rsi_div["bull_strength"] / 50, 1.5)
        advanced_score += boost
        edge_signals.append(
            {
                "name": "RSI Divergence",
                "score": boost,
                "detail": rsi_div["bull_detail"],
                "direction": "bullish",
            }
        )
    if rsi_div and rsi_div.get("bearish_div"):
        penalty = min(rsi_div["bear_strength"] / 50, 1.5)
        advanced_score -= penalty
        edge_signals.append(
            {
                "name": "RSI Divergence",
                "score": -penalty,
                "detail": rsi_div["bear_detail"],
                "direction": "bearish",
            }
        )

    if macd_div and macd_div.get("bullish_div"):
        boost = min(macd_div["bull_strength"] / 60, 1.2)
        advanced_score += boost
        edge_signals.append(
            {
                "name": "MACD Divergence",
                "score": boost,
                "detail": macd_div["bull_detail"],
                "direction": "bullish",
            }
        )
    if macd_div and macd_div.get("bearish_div"):
        penalty = min(macd_div["bear_strength"] / 60, 1.2)
        advanced_score -= penalty
        edge_signals.append(
            {
                "name": "MACD Divergence",
                "score": -penalty,
                "detail": macd_div["bear_detail"],
                "direction": "bearish",
            }
        )

    # Volume anomaly: institutional flow detection
    if vol_anomaly:
        if vol_anomaly.get("accumulation"):
            boost = min(vol_anomaly["anomaly_score"] / 60, 1.0)
            advanced_score += boost
            edge_signals.append(
                {
                    "name": "Inst. Accumulation",
                    "score": boost,
                    "detail": vol_anomaly["detail"],
                    "direction": "bullish",
                }
            )
        elif vol_anomaly.get("distribution"):
            penalty = min(vol_anomaly["anomaly_score"] / 60, 1.0)
            advanced_score -= penalty
            edge_signals.append(
                {
                    "name": "Inst. Distribution",
                    "score": -penalty,
                    "detail": vol_anomaly["detail"],
                    "direction": "bearish",
                }
            )
        if vol_anomaly.get("quiet_accumulation"):
            advanced_score += 0.6
            edge_signals.append(
                {
                    "name": "Quiet Accumulation",
                    "score": 0.6,
                    "detail": vol_anomaly["detail"],
                    "direction": "bullish",
                }
            )

    # Ichimoku Cloud
    if ichimoku_sig and ichimoku_sig.get("signal", 0) != 0:
        ichi_contrib = min(max(ichimoku_sig["signal"] * 0.4, -1.2), 1.2)
        advanced_score += ichi_contrib
        edge_signals.append(
            {
                "name": "Ichimoku",
                "score": ichi_contrib,
                "detail": ichimoku_sig["detail"],
                "direction": "bullish" if ichi_contrib > 0 else "bearish",
            }
        )

    # Mean reversion Z-score: extreme deviations
    if zscore_vals:
        z = _last_valid(zscore_vals)
        if z is not None:
            if z < -2.0:
                advanced_score += 0.8
                edge_signals.append(
                    {
                        "name": "Z-Score",
                        "score": 0.8,
                        "detail": f"Price {abs(z):.1f} std devs below mean -- extreme oversold, mean reversion likely",
                        "direction": "bullish",
                    }
                )
            elif z > 2.0:
                advanced_score -= 0.8
                edge_signals.append(
                    {
                        "name": "Z-Score",
                        "score": -0.8,
                        "detail": f"Price {z:.1f} std devs above mean -- extreme overbought, pullback likely",
                        "direction": "bearish",
                    }
                )

    # Relative strength vs benchmark
    if rs_data and rs_data.get("rs_1m") is not None:
        rs1 = rs_data["rs_1m"]
        rs3 = rs_data.get("rs_3m")
        if rs1 > 5 and (rs3 is None or rs3 > 3):
            advanced_score += 0.7
            edge_signals.append(
                {
                    "name": "Relative Strength",
                    "score": 0.7,
                    "detail": f"Outperforming benchmark: {rs_data['detail']}",
                    "direction": "bullish",
                }
            )
        elif rs1 < -5 and (rs3 is None or rs3 < -3):
            advanced_score -= 0.5
            edge_signals.append(
                {
                    "name": "Relative Strength",
                    "score": -0.5,
                    "detail": f"Underperforming benchmark: {rs_data['detail']}",
                    "direction": "bearish",
                }
            )

    # Combine base + advanced with ADX weighting
    raw = base_raw * adx_multiplier + advanced_score * weights["advanced"]

    normalized = round((raw + 2) / 4 * 100)
    normalized = max(0, min(100, normalized))

    if raw >= 1.2:
        verdict = "Strong Buy"
    elif raw >= 0.5:
        verdict = "Buy"
    elif raw > -0.5:
        verdict = "Neutral"
    elif raw > -1.2:
        verdict = "Sell"
    else:
        verdict = "Strong Sell"

    all_scores: list[float] = [rsi_s, macd_s, sma_s, boll_s, stoch_s, obv_s]
    all_scores += [float(cast(float, e["score"])) for e in edge_signals]
    bullish = sum(1 for s in all_scores if s > 0)
    total_sigs = len(all_scores) or 1
    confidence = round(bullish / total_sigs * 100)

    signals: list[dict[str, object]] = []
    for score_val, detail, name in [
        (rsi_s, rsi_d, "RSI"),
        (macd_s, macd_d, "MACD"),
        (sma_s, sma_d, "SMA"),
        (boll_s, boll_d, "Bollinger"),
        (stoch_s, stoch_d, "Stochastic"),
        (obv_s, obv_d, "Volume"),
    ]:
        direction = "bullish" if score_val > 0 else "bearish" if score_val < 0 else "neutral"
        signals.append({"name": name, "score": score_val, "detail": detail, "direction": direction})

    has_divergence = any("Divergence" in str(e["name"]) for e in edge_signals)
    has_accumulation = any("Accumulation" in str(e["name"]) for e in edge_signals)

    return {
        "score": normalized,
        "raw_score": round(raw, 3),
        "verdict": verdict,
        "confidence": confidence,
        "signals": signals,
        "edge_signals": edge_signals,
        "has_divergence": has_divergence,
        "has_institutional_signal": has_accumulation,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _last_valid(vals: list[Optional[float]]) -> Optional[float]:
    for v in reversed(vals):
        if v is not None:
            return float(v)
    return None


def _second_last_valid(vals: list[Optional[float]]) -> Optional[float]:
    found = 0
    for v in reversed(vals):
        if v is not None:
            found += 1
            if found == 2:
                return float(v)
    return None
