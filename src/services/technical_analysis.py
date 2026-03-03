"""
Pure-math technical indicator computations on lists.

All functions take plain Python lists (close prices, high, low, volume)
and return lists of the same length, padded with None where insufficient
data exists for the lookback window.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Moving Averages
# ---------------------------------------------------------------------------

def sma(values: list[float], period: int) -> list[Optional[float]]:
    """Simple Moving Average."""
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            window = values[i - period + 1: i + 1]
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

def macd(closes: list[float], fast: int = 12, slow: int = 26,
         signal_period: int = 9) -> dict[str, list[Optional[float]]]:
    """Returns {line, signal, histogram} lists."""
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    line = []
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

    histogram = []
    for l_val, s_val in zip(line, signal_full):
        if l_val is None or s_val is None:
            histogram.append(None)
        else:
            histogram.append(round(l_val - s_val, 4))

    return {"line": line, "signal": signal_full, "histogram": histogram}


# ---------------------------------------------------------------------------
# Bollinger Bands  (Bollinger, 1980s)
# ---------------------------------------------------------------------------

def bollinger_bands(closes: list[float], period: int = 20,
                    num_std: float = 2.0) -> dict[str, list[Optional[float]]]:
    """Returns {upper, middle, lower, pct_b} lists."""
    middle = sma(closes, period)
    upper, lower, pct_b = [], [], []

    for i in range(len(closes)):
        if middle[i] is None:
            upper.append(None)
            lower.append(None)
            pct_b.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / period
            std = variance ** 0.5
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

def stochastic(highs: list[float], lows: list[float], closes: list[float],
               k_period: int = 14, d_period: int = 3
               ) -> dict[str, list[Optional[float]]]:
    """Returns {k, d} lists (0-100)."""
    k_vals: list[Optional[float]] = []
    for i in range(len(closes)):
        if i < k_period - 1:
            k_vals.append(None)
        else:
            h_window = highs[i - k_period + 1: i + 1]
            l_window = lows[i - k_period + 1: i + 1]
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

def atr(highs: list[float], lows: list[float], closes: list[float],
        period: int = 14) -> list[Optional[float]]:
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


def _score_macd(macd_data: dict) -> tuple[float, str]:
    """Score MACD crossover: -2 to +2."""
    line = macd_data["line"]
    sig = macd_data["signal"]
    hist = macd_data["histogram"]

    cur_l = _last_valid(line)
    cur_s = _last_valid(sig)
    cur_h = _last_valid(hist)

    if cur_l is None or cur_s is None:
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


def _score_sma_cross(closes: list[float], sma50: list[Optional[float]],
                     sma200: list[Optional[float]]) -> tuple[float, str]:
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


def _score_stochastic(stoch_data: dict) -> tuple[float, str]:
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
    rsi_vals, macd_data, closes, sma50, sma200,
    boll_pct_b, stoch_data, obv_vals
) -> dict:
    """
    Weighted composite of all indicators.
    Returns {score, verdict, confidence, signals[]}.
    """
    weights = {
        "macd": 0.25, "rsi": 0.20, "sma": 0.20,
        "bollinger": 0.15, "stochastic": 0.10, "obv": 0.10,
    }

    rsi_s, rsi_d = _score_rsi(rsi_vals)
    macd_s, macd_d = _score_macd(macd_data)
    sma_s, sma_d = _score_sma_cross(closes, sma50, sma200)
    boll_s, boll_d = _score_bollinger(boll_pct_b)
    stoch_s, stoch_d = _score_stochastic(stoch_data)
    obv_s, obv_d = _score_obv(obv_vals, closes)

    raw = (
        macd_s * weights["macd"] +
        rsi_s * weights["rsi"] +
        sma_s * weights["sma"] +
        boll_s * weights["bollinger"] +
        stoch_s * weights["stochastic"] +
        obv_s * weights["obv"]
    )

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

    bullish = sum(1 for s in [rsi_s, macd_s, sma_s, boll_s, stoch_s, obv_s] if s > 0)
    total = 6
    confidence = round(bullish / total * 100)

    signals = []
    for score_val, detail, name in [
        (rsi_s, rsi_d, "RSI"), (macd_s, macd_d, "MACD"),
        (sma_s, sma_d, "SMA"), (boll_s, boll_d, "Bollinger"),
        (stoch_s, stoch_d, "Stochastic"), (obv_s, obv_d, "Volume"),
    ]:
        direction = "bullish" if score_val > 0 else "bearish" if score_val < 0 else "neutral"
        signals.append({"name": name, "score": score_val, "detail": detail, "direction": direction})

    return {
        "score": normalized,
        "raw_score": round(raw, 3),
        "verdict": verdict,
        "confidence": confidence,
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_valid(vals: list) -> Optional[float]:
    for v in reversed(vals):
        if v is not None:
            return v
    return None


def _second_last_valid(vals: list) -> Optional[float]:
    found = 0
    for v in reversed(vals):
        if v is not None:
            found += 1
            if found == 2:
                return v
    return None
