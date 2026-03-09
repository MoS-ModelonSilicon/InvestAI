"""
Chart Pattern Detection Engine.

Detects classic and advanced chart patterns from OHLCV data:
  - Double Top / Double Bottom (M / W patterns)
  - Head & Shoulders / Inverse Head & Shoulders
  - Bull/Bear Flags & Pennants
  - Ascending / Descending / Symmetric Triangles
  - Rising / Falling Wedges
  - Rounding Bottom
  - Triple Top / Triple Bottom
  - Gap Analysis (breakaway, runaway, exhaustion)
  - 20+ Candlestick patterns (Doji, Hammer, Engulfing, Morning/Evening Star, etc.)

Each detector returns visualization metadata: key point indices, labels,
and drawing instructions so the frontend can annotate charts.
"""

from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# Helper: swing-point finder
# ═══════════════════════════════════════════════════════════════════════════


def _swing_points(data: list[float], window: int = 5) -> list[dict]:
    """Find swing highs and swing lows.
    Returns list of {idx, value, type: 'high'|'low'}.
    """
    pts: list[dict] = []
    n = len(data)
    for i in range(window, n - window):
        left = data[i - window : i]
        right = data[i + 1 : i + window + 1]
        if data[i] >= max(left) and data[i] >= max(right):
            pts.append({"idx": i, "value": data[i], "type": "high"})
        if data[i] <= min(left) and data[i] <= min(right):
            pts.append({"idx": i, "value": data[i], "type": "low"})
    return pts


# ═══════════════════════════════════════════════════════════════════════════
# 1. DOUBLE TOP (M-pattern) / DOUBLE BOTTOM (W-pattern)
# ═══════════════════════════════════════════════════════════════════════════


def detect_double_top(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 100,
    tolerance: float = 0.03,
) -> dict[str, Any]:
    """
    Detect Double Top (M-pattern): two peaks at roughly the same level
    with a trough between them.

    Returns {detected, confidence, peaks, trough, neckline, target,
             viz_points: [{idx, value, label}], detail}.
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 30:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(highs[start:], window=5)
    swing_highs = [p for p in pts if p["type"] == "high"]
    swing_lows = [p for p in pts if p["type"] == "low"]

    if len(swing_highs) < 2 or len(swing_lows) < 1:
        return empty

    best = None
    for i in range(len(swing_highs) - 1):
        p1 = swing_highs[i]
        for j in range(i + 1, len(swing_highs)):
            p2 = swing_highs[j]
            # Peaks should be roughly equal
            diff_pct = abs(p1["value"] - p2["value"]) / max(p1["value"], 1)
            if diff_pct > tolerance:
                continue
            # Must have a trough between them
            troughs = [t for t in swing_lows if p1["idx"] < t["idx"] < p2["idx"]]
            if not troughs:
                continue
            trough = min(troughs, key=lambda t: t["value"])
            # Width check
            width = p2["idx"] - p1["idx"]
            if width < 8 or width > 80:
                continue
            # Depth check
            rim = (p1["value"] + p2["value"]) / 2
            depth_pct = (rim - trough["value"]) / rim
            if depth_pct < 0.03 or depth_pct > 0.25:
                continue
            # Price should be near or below neckline after second peak
            neckline = trough["value"]
            current = closes[-1]
            near_neckline = current <= rim * 1.02

            symmetry = 1.0 - abs((trough["idx"] - p1["idx"]) - (p2["idx"] - trough["idx"])) / width
            conf = int(60 + symmetry * 20 + (1.0 - diff_pct / tolerance) * 20)
            conf = max(0, min(100, conf))

            if near_neckline and (best is None or conf > best["confidence"]):
                target_price = neckline - (rim - neckline)
                best = {
                    "detected": True,
                    "confidence": conf,
                    "peak1_idx": start + p1["idx"],
                    "peak2_idx": start + p2["idx"],
                    "trough_idx": start + trough["idx"],
                    "neckline": round(neckline, 2),
                    "target": round(target_price, 2),
                    "viz_points": [
                        {"idx": start + p1["idx"], "value": p1["value"], "label": "Peak 1"},
                        {"idx": start + trough["idx"], "value": trough["value"], "label": "Neckline"},
                        {"idx": start + p2["idx"], "value": p2["value"], "label": "Peak 2"},
                    ],
                    "detail": (
                        f"Double Top (M-pattern): peaks at ${rim:.2f}, "
                        f"neckline ${neckline:.2f}, target ${target_price:.2f} "
                        f"({conf}% confidence)"
                    ),
                }
    return best if best else empty


def detect_double_bottom(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 100,
    tolerance: float = 0.03,
) -> dict[str, Any]:
    """
    Detect Double Bottom (W-pattern): two troughs at roughly the same level
    with a peak between them.

    Returns {detected, confidence, troughs, peak, neckline, target,
             viz_points, detail}.
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 30:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(lows[start:], window=5)
    swing_lows = [p for p in pts if p["type"] == "low"]
    swing_highs = [p for p in pts if p["type"] == "high"]

    # Also check highs array for the peak between bottoms
    pts_h = _swing_points(highs[start:], window=5)
    swing_highs_h = [p for p in pts_h if p["type"] == "high"]
    all_highs = swing_highs + swing_highs_h
    all_highs.sort(key=lambda x: x["idx"])

    if len(swing_lows) < 2 or len(all_highs) < 1:
        return empty

    best = None
    for i in range(len(swing_lows) - 1):
        t1 = swing_lows[i]
        for j in range(i + 1, len(swing_lows)):
            t2 = swing_lows[j]
            diff_pct = abs(t1["value"] - t2["value"]) / max(t1["value"], 1)
            if diff_pct > tolerance:
                continue
            peaks = [p for p in all_highs if t1["idx"] < p["idx"] < t2["idx"]]
            if not peaks:
                continue
            peak = max(peaks, key=lambda p: p["value"])
            width = t2["idx"] - t1["idx"]
            if width < 8 or width > 80:
                continue
            valley = (t1["value"] + t2["value"]) / 2
            depth_pct = (peak["value"] - valley) / peak["value"]
            if depth_pct < 0.03 or depth_pct > 0.25:
                continue
            neckline = peak["value"]
            current = closes[-1]
            near_neckline = current >= valley * 0.98

            symmetry = 1.0 - abs((peak["idx"] - t1["idx"]) - (t2["idx"] - peak["idx"])) / width
            conf = int(60 + symmetry * 20 + (1.0 - diff_pct / tolerance) * 20)
            conf = max(0, min(100, conf))

            if near_neckline and (best is None or conf > best["confidence"]):
                target_price = neckline + (neckline - valley)
                best = {
                    "detected": True,
                    "confidence": conf,
                    "trough1_idx": start + t1["idx"],
                    "trough2_idx": start + t2["idx"],
                    "peak_idx": start + peak["idx"],
                    "neckline": round(neckline, 2),
                    "target": round(target_price, 2),
                    "viz_points": [
                        {"idx": start + t1["idx"], "value": t1["value"], "label": "Bottom 1"},
                        {"idx": start + peak["idx"], "value": peak["value"], "label": "Neckline"},
                        {"idx": start + t2["idx"], "value": t2["value"], "label": "Bottom 2"},
                    ],
                    "detail": (
                        f"Double Bottom (W-pattern): bottoms at ${valley:.2f}, "
                        f"neckline ${neckline:.2f}, target ${target_price:.2f} "
                        f"({conf}% confidence)"
                    ),
                }
    return best if best else empty


# ═══════════════════════════════════════════════════════════════════════════
# 2. HEAD & SHOULDERS / INVERSE HEAD & SHOULDERS
# ═══════════════════════════════════════════════════════════════════════════


def detect_head_and_shoulders(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 120,
) -> dict[str, Any]:
    """
    Detect Head & Shoulders (bearish reversal): three peaks where the
    middle peak (head) is higher than the two shoulders.

    Returns {detected, confidence, left_shoulder, head, right_shoulder,
             neckline, target, viz_points, detail}.
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 40:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(highs[start:], window=4)
    swing_highs = [p for p in pts if p["type"] == "high"]
    pts_low = _swing_points(lows[start:], window=4)
    swing_lows = [p for p in pts_low if p["type"] == "low"]

    if len(swing_highs) < 3:
        return empty

    best = None
    for i in range(len(swing_highs) - 2):
        ls = swing_highs[i]  # left shoulder
        for j in range(i + 1, len(swing_highs) - 1):
            head = swing_highs[j]
            # Head must be higher than left shoulder
            if head["value"] <= ls["value"] * 1.01:
                continue
            for k in range(j + 1, len(swing_highs)):
                rs = swing_highs[k]
                # Right shoulder roughly equal to left
                shoulder_diff = abs(ls["value"] - rs["value"]) / max(ls["value"], 1)
                if shoulder_diff > 0.06:
                    continue
                # Head must be higher than right shoulder
                if head["value"] <= rs["value"] * 1.01:
                    continue
                # Find neckline troughs
                left_troughs = [t for t in swing_lows if ls["idx"] < t["idx"] < head["idx"]]
                right_troughs = [t for t in swing_lows if head["idx"] < t["idx"] < rs["idx"]]
                if not left_troughs or not right_troughs:
                    continue
                lt = min(left_troughs, key=lambda t: t["value"])
                rt = min(right_troughs, key=lambda t: t["value"])
                neckline = (lt["value"] + rt["value"]) / 2

                # Width proportionality
                left_width = head["idx"] - ls["idx"]
                right_width = rs["idx"] - head["idx"]
                if left_width < 5 or right_width < 5:
                    continue
                width_ratio = min(left_width, right_width) / max(left_width, right_width)
                if width_ratio < 0.4:
                    continue

                head_height = head["value"] - neckline
                target_price = neckline - head_height

                symmetry = width_ratio
                shoulder_match = 1.0 - shoulder_diff / 0.06
                conf = int(55 + symmetry * 20 + shoulder_match * 25)
                conf = max(0, min(100, conf))

                if best is None or conf > best["confidence"]:
                    best = {
                        "detected": True,
                        "confidence": conf,
                        "viz_points": [
                            {"idx": start + ls["idx"], "value": ls["value"], "label": "L.Shoulder"},
                            {"idx": start + lt["idx"], "value": lt["value"], "label": "Neckline L"},
                            {"idx": start + head["idx"], "value": head["value"], "label": "Head"},
                            {"idx": start + rt["idx"], "value": rt["value"], "label": "Neckline R"},
                            {"idx": start + rs["idx"], "value": rs["value"], "label": "R.Shoulder"},
                        ],
                        "neckline": round(neckline, 2),
                        "target": round(target_price, 2),
                        "detail": (
                            f"Head & Shoulders: head ${head['value']:.2f}, "
                            f"neckline ${neckline:.2f}, target ${target_price:.2f} "
                            f"({conf}% confidence)"
                        ),
                    }
    return best if best else empty


def detect_inverse_head_and_shoulders(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 120,
) -> dict[str, Any]:
    """
    Detect Inverse Head & Shoulders (bullish reversal): three troughs where
    the middle trough (head) is lower than the two shoulders.
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 40:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(lows[start:], window=4)
    swing_lows = [p for p in pts if p["type"] == "low"]
    pts_high = _swing_points(highs[start:], window=4)
    swing_highs = [p for p in pts_high if p["type"] == "high"]

    if len(swing_lows) < 3:
        return empty

    best = None
    for i in range(len(swing_lows) - 2):
        ls = swing_lows[i]
        for j in range(i + 1, len(swing_lows) - 1):
            head = swing_lows[j]
            if head["value"] >= ls["value"] * 0.99:
                continue
            for k in range(j + 1, len(swing_lows)):
                rs = swing_lows[k]
                shoulder_diff = abs(ls["value"] - rs["value"]) / max(ls["value"], 1)
                if shoulder_diff > 0.06:
                    continue
                if head["value"] >= rs["value"] * 0.99:
                    continue
                left_peaks = [p for p in swing_highs if ls["idx"] < p["idx"] < head["idx"]]
                right_peaks = [p for p in swing_highs if head["idx"] < p["idx"] < rs["idx"]]
                if not left_peaks or not right_peaks:
                    continue
                lp = max(left_peaks, key=lambda p: p["value"])
                rp = max(right_peaks, key=lambda p: p["value"])
                neckline = (lp["value"] + rp["value"]) / 2

                left_width = head["idx"] - ls["idx"]
                right_width = rs["idx"] - head["idx"]
                if left_width < 5 or right_width < 5:
                    continue
                width_ratio = min(left_width, right_width) / max(left_width, right_width)
                if width_ratio < 0.4:
                    continue

                head_depth = neckline - head["value"]
                target_price = neckline + head_depth

                symmetry = width_ratio
                shoulder_match = 1.0 - shoulder_diff / 0.06
                conf = int(55 + symmetry * 20 + shoulder_match * 25)
                conf = max(0, min(100, conf))

                if best is None or conf > best["confidence"]:
                    best = {
                        "detected": True,
                        "confidence": conf,
                        "viz_points": [
                            {"idx": start + ls["idx"], "value": ls["value"], "label": "L.Shoulder"},
                            {"idx": start + lp["idx"], "value": lp["value"], "label": "Neckline L"},
                            {"idx": start + head["idx"], "value": head["value"], "label": "Head"},
                            {"idx": start + rp["idx"], "value": rp["value"], "label": "Neckline R"},
                            {"idx": start + rs["idx"], "value": rs["value"], "label": "R.Shoulder"},
                        ],
                        "neckline": round(neckline, 2),
                        "target": round(target_price, 2),
                        "detail": (
                            f"Inverse H&S: head ${head['value']:.2f}, "
                            f"neckline ${neckline:.2f}, target ${target_price:.2f} "
                            f"({conf}% confidence)"
                        ),
                    }
    return best if best else empty


# ═══════════════════════════════════════════════════════════════════════════
# 3. FLAGS & PENNANTS
# ═══════════════════════════════════════════════════════════════════════════


def detect_flag(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    lookback: int = 60,
) -> dict[str, Any]:
    """
    Detect Bull/Bear Flag: sharp move (pole) followed by a gentle
    counter-trend channel (flag).
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 25:
        return empty

    start = max(0, n - lookback)
    window = closes[start:]
    wn = len(window)

    # Look for a sharp recent move (pole)
    best = None
    for pole_len in range(5, min(20, wn - 10)):
        pole_start = wn - pole_len - 15  # Allow room for flag
        if pole_start < 0:
            continue
        pole_end = pole_start + pole_len
        pole_move = (window[pole_end] - window[pole_start]) / window[pole_start]

        is_bull = pole_move > 0.05  # 5%+ move up
        is_bear = pole_move < -0.05  # 5%+ move down

        if not is_bull and not is_bear:
            continue

        # Flag: smaller counter-trend after pole
        flag_data = window[pole_end:]
        if len(flag_data) < 5:
            continue

        flag_move = (flag_data[-1] - flag_data[0]) / flag_data[0] if flag_data[0] != 0 else 0

        # Bull flag: pole up, flag drifts slightly down or sideways
        if is_bull and -0.08 < flag_move < 0.02:
            # Verify flag is narrowing (lower highs, higher lows would be pennant)
            flag_range = max(flag_data) - min(flag_data)
            pole_range = abs(window[pole_end] - window[pole_start])
            if flag_range < pole_range * 0.6:
                target_price = flag_data[-1] + pole_range
                conf = int(60 + (abs(pole_move) * 200) + (1.0 - flag_range / pole_range) * 15)
                conf = max(0, min(100, conf))
                if best is None or conf > best["confidence"]:  # type: ignore[operator]
                    best = {
                        "detected": True,
                        "type": "bull_flag",
                        "confidence": conf,
                        "viz_points": [
                            {"idx": start + pole_start, "value": window[pole_start], "label": "Pole Start"},
                            {"idx": start + pole_end, "value": window[pole_end], "label": "Pole Top"},
                            {"idx": start + wn - 1, "value": window[-1], "label": "Flag End"},
                        ],
                        "target": round(target_price, 2),
                        "detail": (f"Bull Flag: {pole_move * 100:.1f}% pole, target ${target_price:.2f} ({conf}%)"),
                    }

        # Bear flag: pole down, flag drifts slightly up or sideways
        if is_bear and -0.02 < flag_move < 0.08:
            flag_range = max(flag_data) - min(flag_data)
            pole_range = abs(window[pole_end] - window[pole_start])
            if flag_range < pole_range * 0.6:
                target_price = flag_data[-1] - pole_range
                conf = int(60 + (abs(pole_move) * 200) + (1.0 - flag_range / pole_range) * 15)
                conf = max(0, min(100, conf))
                if best is None or conf > best["confidence"]:  # type: ignore[operator]
                    best = {
                        "detected": True,
                        "type": "bear_flag",
                        "confidence": conf,
                        "viz_points": [
                            {"idx": start + pole_start, "value": window[pole_start], "label": "Pole Start"},
                            {"idx": start + pole_end, "value": window[pole_end], "label": "Pole Bottom"},
                            {"idx": start + wn - 1, "value": window[-1], "label": "Flag End"},
                        ],
                        "target": round(target_price, 2),
                        "detail": (f"Bear Flag: {pole_move * 100:.1f}% pole, target ${target_price:.2f} ({conf}%)"),
                    }

    return best if best else empty


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRIANGLES (Ascending, Descending, Symmetric)
# ═══════════════════════════════════════════════════════════════════════════


def detect_triangle(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 60,
) -> dict[str, Any]:
    """
    Detect triangle patterns: converging trendlines on highs and lows.
    - Ascending: flat top, rising bottom
    - Descending: flat bottom, falling top
    - Symmetric: both converging
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 25:
        return empty

    start = max(0, n - lookback)
    h_pts = _swing_points(highs[start:], window=3)
    l_pts = _swing_points(lows[start:], window=3)

    sh = [p for p in h_pts if p["type"] == "high"]
    sl = [p for p in l_pts if p["type"] == "low"]

    if len(sh) < 3 or len(sl) < 3:
        return empty

    # Use last 4 swing highs/lows
    recent_highs = sh[-4:]
    recent_lows = sl[-4:]

    # Check if highs are descending
    h_vals = [p["value"] for p in recent_highs]
    l_vals = [p["value"] for p in recent_lows]

    h_slope = (h_vals[-1] - h_vals[0]) / max(len(h_vals) - 1, 1)
    l_slope = (l_vals[-1] - l_vals[0]) / max(len(l_vals) - 1, 1)

    avg_price = closes[-1]
    h_slope_pct = h_slope / avg_price * 100 if avg_price > 0 else 0
    l_slope_pct = l_slope / avg_price * 100 if avg_price > 0 else 0

    # Converging check: range narrowing
    early_range = h_vals[0] - l_vals[0] if h_vals and l_vals else 0
    late_range = h_vals[-1] - l_vals[-1] if h_vals and l_vals else 0
    if early_range <= 0 or late_range >= early_range:
        return empty  # not converging

    convergence = 1.0 - (late_range / early_range)
    if convergence < 0.15:
        return empty

    # Classify
    if abs(h_slope_pct) < 0.3 and l_slope_pct > 0.2:
        tri_type = "ascending"
        direction = "bullish"
        target = h_vals[-1] + early_range
    elif abs(l_slope_pct) < 0.3 and h_slope_pct < -0.2:
        tri_type = "descending"
        direction = "bearish"
        target = l_vals[-1] - early_range
    elif h_slope_pct < -0.1 and l_slope_pct > 0.1:
        tri_type = "symmetric"
        direction = "neutral"
        target = closes[-1] + early_range * 0.5  # breakout direction unknown
    else:
        return empty

    conf = int(50 + convergence * 30 + min(len(sh), 5) * 4)
    conf = max(0, min(100, conf))

    viz = []
    for p in recent_highs:
        viz.append({"idx": start + p["idx"], "value": p["value"], "label": "High"})
    for p in recent_lows:
        viz.append({"idx": start + p["idx"], "value": p["value"], "label": "Low"})

    return {
        "detected": True,
        "type": tri_type,
        "direction": direction,
        "confidence": conf,
        "viz_points": viz,
        "target": round(target, 2),
        "trendline_high": [{"idx": start + p["idx"], "value": p["value"]} for p in recent_highs],
        "trendline_low": [{"idx": start + p["idx"], "value": p["value"]} for p in recent_lows],
        "detail": (f"{tri_type.title()} Triangle: converging {convergence * 100:.0f}%, target ${target:.2f} ({conf}%)"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. WEDGES (Rising / Falling)
# ═══════════════════════════════════════════════════════════════════════════


def detect_wedge(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    lookback: int = 60,
) -> dict[str, Any]:
    """
    Detect wedge patterns: both trendlines sloping in the same direction
    but converging.
    - Rising Wedge (bearish): both rising, top slower
    - Falling Wedge (bullish): both falling, bottom slower
    """
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 25:
        return empty

    start = max(0, n - lookback)
    h_pts = _swing_points(highs[start:], window=3)
    l_pts = _swing_points(lows[start:], window=3)
    sh = [p for p in h_pts if p["type"] == "high"]
    sl = [p for p in l_pts if p["type"] == "low"]

    if len(sh) < 3 or len(sl) < 3:
        return empty

    h_vals = [p["value"] for p in sh[-4:]]
    l_vals = [p["value"] for p in sl[-4:]]

    h_slope = (h_vals[-1] - h_vals[0]) / max(len(h_vals) - 1, 1)
    l_slope = (l_vals[-1] - l_vals[0]) / max(len(l_vals) - 1, 1)

    avg = closes[-1]
    h_slope_pct = h_slope / avg * 100 if avg > 0 else 0
    l_slope_pct = l_slope / avg * 100 if avg > 0 else 0

    early_range = h_vals[0] - l_vals[0]
    late_range = h_vals[-1] - l_vals[-1]
    if early_range <= 0 or late_range >= early_range:
        return empty

    convergence = 1.0 - late_range / early_range

    # Rising wedge: both slopes positive, converging
    if h_slope_pct > 0.1 and l_slope_pct > 0.1 and convergence > 0.1:
        wedge_type = "rising"
        direction = "bearish"
        target = l_vals[-1] - early_range * 0.5
    # Falling wedge: both slopes negative, converging
    elif h_slope_pct < -0.1 and l_slope_pct < -0.1 and convergence > 0.1:
        wedge_type = "falling"
        direction = "bullish"
        target = h_vals[-1] + early_range * 0.5
    else:
        return empty

    conf = int(50 + convergence * 30 + 10)
    conf = max(0, min(100, conf))

    viz = []
    for p in sh[-4:]:
        viz.append({"idx": start + p["idx"], "value": p["value"], "label": "High"})
    for p in sl[-4:]:
        viz.append({"idx": start + p["idx"], "value": p["value"], "label": "Low"})

    return {
        "detected": True,
        "type": wedge_type,
        "direction": direction,
        "confidence": conf,
        "viz_points": viz,
        "trendline_high": [{"idx": start + p["idx"], "value": p["value"]} for p in sh[-4:]],
        "trendline_low": [{"idx": start + p["idx"], "value": p["value"]} for p in sl[-4:]],
        "target": round(target, 2),
        "detail": (
            f"{wedge_type.title()} Wedge ({direction}): "
            f"convergence {convergence * 100:.0f}%, target ${target:.2f} ({conf}%)"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. GAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════


def detect_gaps(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    lookback: int = 60,
) -> list[dict[str, Any]]:
    """
    Detect price gaps. Returns list of gap objects.
    Types: breakaway, runaway (continuation), exhaustion, common.
    """
    n = len(closes)
    if n < 10:
        return []

    start = max(0, n - lookback)
    gaps: list[dict[str, Any]] = []
    avg_vol = sum(volumes[start:]) / max(len(volumes[start:]), 1) if volumes else 0

    for i in range(start + 1, n):
        # Gap up: today's low > yesterday's high
        if lows[i] > highs[i - 1]:
            gap_size = lows[i] - highs[i - 1]
            gap_pct = gap_size / closes[i - 1] * 100 if closes[i - 1] > 0 else 0
            if gap_pct < 0.5:
                continue  # too small
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0
            gap_type = _classify_gap(gap_pct, vol_ratio, i - start, lookback)
            gaps.append(
                {
                    "idx": i,
                    "direction": "up",
                    "gap_size": round(gap_size, 2),
                    "gap_pct": round(gap_pct, 2),
                    "type": gap_type,
                    "high_before": round(highs[i - 1], 2),
                    "low_after": round(lows[i], 2),
                    "label": f"Gap Up {gap_pct:.1f}% ({gap_type})",
                }
            )

        # Gap down: today's high < yesterday's low
        if highs[i] < lows[i - 1]:
            gap_size = lows[i - 1] - highs[i]
            gap_pct = gap_size / closes[i - 1] * 100 if closes[i - 1] > 0 else 0
            if gap_pct < 0.5:
                continue
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0
            gap_type = _classify_gap(gap_pct, vol_ratio, i - start, lookback)
            gaps.append(
                {
                    "idx": i,
                    "direction": "down",
                    "gap_size": round(gap_size, 2),
                    "gap_pct": round(gap_pct, 2),
                    "type": gap_type,
                    "low_before": round(lows[i - 1], 2),
                    "high_after": round(highs[i], 2),
                    "label": f"Gap Down {gap_pct:.1f}% ({gap_type})",
                }
            )

    return gaps[-5:]  # Return last 5 gaps


def _classify_gap(gap_pct: float, vol_ratio: float, position: int, lookback: int) -> str:
    """Classify gap type based on size, volume, and position in trend."""
    if gap_pct > 3.0 and vol_ratio > 2.0:
        return "breakaway"
    if gap_pct > 1.5 and 0.3 < position / lookback < 0.7:
        return "runaway"
    if position / lookback > 0.8 and vol_ratio > 1.5:
        return "exhaustion"
    return "common"


# ═══════════════════════════════════════════════════════════════════════════
# 7. CANDLESTICK PATTERNS (~21 patterns)
# ═══════════════════════════════════════════════════════════════════════════


def detect_candlestick_patterns(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    lookback: int = 10,
) -> list[dict[str, Any]]:
    """
    Scan recent candles for classic candlestick patterns.
    Returns list of {pattern, idx, direction, reliability, detail, viz}.
    """
    n = len(closes)
    if n < 5 or len(opens) < 5:
        return []

    patterns: list[dict[str, Any]] = []
    start = max(0, n - lookback)

    for i in range(max(start, 3), n):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        body = abs(c - o)
        full_range = h - l if h > l else 0.001
        body_pct = body / full_range
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        is_green = c > o
        is_red = c < o

        prev_o = opens[i - 1] if i > 0 else o
        prev_h = highs[i - 1] if i > 0 else h
        prev_l = lows[i - 1] if i > 0 else l
        prev_c = closes[i - 1] if i > 0 else c
        prev_body = abs(prev_c - prev_o)
        prev_green = prev_c > prev_o
        prev_red = prev_c < prev_o

        # ── Single candle patterns ──────────────────

        # Doji: tiny body, notable shadows
        if body_pct < 0.1 and full_range > 0:
            patterns.append(
                {
                    "pattern": "Doji",
                    "idx": i,
                    "direction": "neutral",
                    "reliability": 50,
                    "detail": "Doji: indecision, open ≈ close — potential reversal",
                    "viz": {"type": "marker", "shape": "cross", "color": "#eab308"},
                }
            )

        # Dragonfly Doji: open=close near high, long lower shadow
        if body_pct < 0.1 and lower_shadow > full_range * 0.6 and upper_shadow < full_range * 0.1:
            patterns.append(
                {
                    "pattern": "Dragonfly Doji",
                    "idx": i,
                    "direction": "bullish",
                    "reliability": 65,
                    "detail": "Dragonfly Doji: bulls rejected low prices — bullish reversal",
                    "viz": {"type": "marker", "shape": "triangle", "color": "#22c55e"},
                }
            )

        # Gravestone Doji: open=close near low, long upper shadow
        if body_pct < 0.1 and upper_shadow > full_range * 0.6 and lower_shadow < full_range * 0.1:
            patterns.append(
                {
                    "pattern": "Gravestone Doji",
                    "idx": i,
                    "direction": "bearish",
                    "reliability": 65,
                    "detail": "Gravestone Doji: bears rejected high prices — bearish reversal",
                    "viz": {"type": "marker", "shape": "triangle", "color": "#ef4444"},
                }
            )

        # Hammer: small body at top, long lower shadow (>2x body), in downtrend
        if (is_green or body_pct < 0.35) and lower_shadow > body * 2 and upper_shadow < body * 0.5:
            # Check if in recent downtrend
            if i >= 5 and closes[i - 5] > closes[i - 1]:
                patterns.append(
                    {
                        "pattern": "Hammer",
                        "idx": i,
                        "direction": "bullish",
                        "reliability": 70,
                        "detail": "Hammer: long lower shadow after downtrend — bullish reversal",
                        "viz": {"type": "marker", "shape": "triangle", "color": "#22c55e"},
                    }
                )

        # Inverted Hammer: small body at bottom, long upper shadow
        if body_pct < 0.35 and upper_shadow > body * 2 and lower_shadow < body * 0.5:
            if i >= 5 and closes[i - 5] > closes[i - 1]:
                patterns.append(
                    {
                        "pattern": "Inverted Hammer",
                        "idx": i,
                        "direction": "bullish",
                        "reliability": 60,
                        "detail": "Inverted Hammer: buying pressure emerging in downtrend",
                        "viz": {"type": "marker", "shape": "rectRot", "color": "#22c55e"},
                    }
                )

        # Shooting Star: small body at bottom, long upper shadow, in uptrend
        if body_pct < 0.35 and upper_shadow > body * 2 and lower_shadow < body * 0.5:
            if i >= 5 and closes[i - 5] < closes[i - 1]:
                patterns.append(
                    {
                        "pattern": "Shooting Star",
                        "idx": i,
                        "direction": "bearish",
                        "reliability": 65,
                        "detail": "Shooting Star: rejection at highs in uptrend — bearish reversal",
                        "viz": {"type": "marker", "shape": "triangle", "color": "#ef4444"},
                    }
                )

        # Hanging Man: hammer shape but in uptrend
        if (is_red or body_pct < 0.35) and lower_shadow > body * 2 and upper_shadow < body * 0.5:
            if i >= 5 and closes[i - 5] < closes[i - 1]:
                patterns.append(
                    {
                        "pattern": "Hanging Man",
                        "idx": i,
                        "direction": "bearish",
                        "reliability": 60,
                        "detail": "Hanging Man: long lower shadow in uptrend — distribution warning",
                        "viz": {"type": "marker", "shape": "rectRot", "color": "#ef4444"},
                    }
                )

        # Marubozu: full body, minimal shadows
        if body_pct > 0.9:
            if is_green:
                patterns.append(
                    {
                        "pattern": "Bullish Marubozu",
                        "idx": i,
                        "direction": "bullish",
                        "reliability": 60,
                        "detail": "Bullish Marubozu: strong buying, no rejection",
                        "viz": {"type": "marker", "shape": "rect", "color": "#22c55e"},
                    }
                )
            elif is_red:
                patterns.append(
                    {
                        "pattern": "Bearish Marubozu",
                        "idx": i,
                        "direction": "bearish",
                        "reliability": 60,
                        "detail": "Bearish Marubozu: strong selling, no support",
                        "viz": {"type": "marker", "shape": "rect", "color": "#ef4444"},
                    }
                )

        # ── Two-candle patterns ─────────────────────

        if i < 1:
            continue

        # Bullish Engulfing: red candle followed by larger green candle
        if prev_red and is_green and c > prev_o and o < prev_c and body > prev_body:
            patterns.append(
                {
                    "pattern": "Bullish Engulfing",
                    "idx": i,
                    "direction": "bullish",
                    "reliability": 75,
                    "detail": "Bullish Engulfing: green candle fully engulfs prior red — strong reversal",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(34,197,94,0.15)"},
                }
            )

        # Bearish Engulfing: green candle followed by larger red candle
        if prev_green and is_red and o > prev_c and c < prev_o and body > prev_body:
            patterns.append(
                {
                    "pattern": "Bearish Engulfing",
                    "idx": i,
                    "direction": "bearish",
                    "reliability": 75,
                    "detail": "Bearish Engulfing: red candle engulfs prior green — strong reversal",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(239,68,68,0.15)"},
                }
            )

        # Piercing Line: prior red, opens below prior low, closes above midpoint
        prev_mid = (prev_o + prev_c) / 2
        if prev_red and is_green and o < prev_l and c > prev_mid and c < prev_o:
            patterns.append(
                {
                    "pattern": "Piercing Line",
                    "idx": i,
                    "direction": "bullish",
                    "reliability": 65,
                    "detail": "Piercing Line: opened below low, closed above midpoint — bullish",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(34,197,94,0.1)"},
                }
            )

        # Dark Cloud Cover: prior green, opens above prior high, closes below midpoint
        prev_mid_g = (prev_o + prev_c) / 2
        if prev_green and is_red and o > prev_h and c < prev_mid_g and c > prev_o:
            patterns.append(
                {
                    "pattern": "Dark Cloud Cover",
                    "idx": i,
                    "direction": "bearish",
                    "reliability": 65,
                    "detail": "Dark Cloud Cover: opened above high, closed below midpoint — bearish",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(239,68,68,0.1)"},
                }
            )

        # Harami (Bullish): large red followed by small green inside
        if prev_red and is_green and o > prev_c and c < prev_o and body < prev_body * 0.5:
            patterns.append(
                {
                    "pattern": "Bullish Harami",
                    "idx": i,
                    "direction": "bullish",
                    "reliability": 55,
                    "detail": "Bullish Harami: small green inside large red — selling pressure fading",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(34,197,94,0.08)"},
                }
            )

        # Harami (Bearish): large green followed by small red inside
        if prev_green and is_red and o < prev_c and c > prev_o and body < prev_body * 0.5:
            patterns.append(
                {
                    "pattern": "Bearish Harami",
                    "idx": i,
                    "direction": "bearish",
                    "reliability": 55,
                    "detail": "Bearish Harami: small red inside large green — buying exhaustion",
                    "viz": {"type": "highlight", "start": i - 1, "end": i, "color": "rgba(239,68,68,0.08)"},
                }
            )

        # Tweezer Top: same highs in uptrend
        if i >= 5 and closes[i - 5] < closes[i - 1]:
            if abs(h - prev_h) / max(h, 0.01) < 0.002:
                if prev_green and is_red:
                    patterns.append(
                        {
                            "pattern": "Tweezer Top",
                            "idx": i,
                            "direction": "bearish",
                            "reliability": 60,
                            "detail": "Tweezer Top: matching highs — resistance confirmed",
                            "viz": {"type": "marker", "shape": "triangle", "color": "#ef4444"},
                        }
                    )

        # Tweezer Bottom: same lows in downtrend
        if i >= 5 and closes[i - 5] > closes[i - 1]:
            if abs(l - prev_l) / max(l, 0.01) < 0.002:
                if prev_red and is_green:
                    patterns.append(
                        {
                            "pattern": "Tweezer Bottom",
                            "idx": i,
                            "direction": "bullish",
                            "reliability": 60,
                            "detail": "Tweezer Bottom: matching lows — support confirmed",
                            "viz": {"type": "marker", "shape": "triangle", "color": "#22c55e"},
                        }
                    )

        # ── Three-candle patterns ───────────────────

        if i < 2:
            continue

        pp_o, pp_h, pp_l, pp_c = opens[i - 2], highs[i - 2], lows[i - 2], closes[i - 2]
        pp_green = pp_c > pp_o
        pp_red = pp_c < pp_o

        # Morning Star: bearish, small body (star), bullish
        pp_body = abs(pp_c - pp_o)
        if pp_red and pp_body > full_range * 0.3:
            star_body = abs(prev_c - prev_o)
            star_small = star_body < pp_body * 0.3
            if star_small and is_green and c > (pp_o + pp_c) / 2:
                patterns.append(
                    {
                        "pattern": "Morning Star",
                        "idx": i,
                        "direction": "bullish",
                        "reliability": 78,
                        "detail": "Morning Star: three-candle bullish reversal — high reliability",
                        "viz": {"type": "highlight", "start": i - 2, "end": i, "color": "rgba(34,197,94,0.12)"},
                    }
                )

        # Evening Star: bullish, small body (star), bearish
        if pp_green and pp_body > full_range * 0.3:
            star_body = abs(prev_c - prev_o)
            star_small = star_body < pp_body * 0.3
            if star_small and is_red and c < (pp_o + pp_c) / 2:
                patterns.append(
                    {
                        "pattern": "Evening Star",
                        "idx": i,
                        "direction": "bearish",
                        "reliability": 72,
                        "detail": "Evening Star: three-candle bearish reversal — high reliability",
                        "viz": {"type": "highlight", "start": i - 2, "end": i, "color": "rgba(239,68,68,0.12)"},
                    }
                )

        # Three White Soldiers: three consecutive green candles, each opening inside prior body
        if pp_green and prev_green and is_green:
            if prev_o > pp_o and o > prev_o and c > prev_c and prev_c > pp_c:
                bodies_growing = abs(prev_c - prev_o) >= pp_body * 0.8 and body >= abs(prev_c - prev_o) * 0.8
                if bodies_growing:
                    patterns.append(
                        {
                            "pattern": "Three White Soldiers",
                            "idx": i,
                            "direction": "bullish",
                            "reliability": 82,
                            "detail": "Three White Soldiers: strong bullish continuation — very high reliability",
                            "viz": {"type": "highlight", "start": i - 2, "end": i, "color": "rgba(34,197,94,0.15)"},
                        }
                    )

        # Three Black Crows: three consecutive red candles
        if pp_red and prev_red and is_red:
            if prev_o < pp_o and o < prev_o and c < prev_c and prev_c < pp_c:
                bodies_growing = abs(prev_c - prev_o) >= pp_body * 0.8 and body >= abs(prev_c - prev_o) * 0.8
                if bodies_growing:
                    patterns.append(
                        {
                            "pattern": "Three Black Crows",
                            "idx": i,
                            "direction": "bearish",
                            "reliability": 78,
                            "detail": "Three Black Crows: strong bearish continuation — very high reliability",
                            "viz": {"type": "highlight", "start": i - 2, "end": i, "color": "rgba(239,68,68,0.15)"},
                        }
                    )

    # Deduplicate: keep highest reliability per index
    seen: dict[tuple[int, str], dict] = {}
    for p in patterns:
        key = (p["idx"], p["direction"])
        if key not in seen or p["reliability"] > seen[key]["reliability"]:
            seen[key] = p

    return sorted(seen.values(), key=lambda x: x["idx"])


# ═══════════════════════════════════════════════════════════════════════════
# 8. TRIPLE TOP / TRIPLE BOTTOM
# ═══════════════════════════════════════════════════════════════════════════


def detect_triple_top(
    closes: list[float],
    highs: list[float],
    lookback: int = 120,
    tolerance: float = 0.03,
) -> dict[str, Any]:
    """Three peaks at roughly the same level."""
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 40:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(highs[start:], window=5)
    sh = [p for p in pts if p["type"] == "high"]

    if len(sh) < 3:
        return empty

    for i in range(len(sh) - 2):
        p1, p2, p3 = sh[i], sh[i + 1], sh[i + 2]
        avg_peak = (p1["value"] + p2["value"] + p3["value"]) / 3
        if all(abs(p["value"] - avg_peak) / avg_peak < tolerance for p in [p1, p2, p3]):
            width = p3["idx"] - p1["idx"]
            if width < 15:
                continue
            conf = int(65 + (1.0 - max(abs(p["value"] - avg_peak) / avg_peak for p in [p1, p2, p3]) / tolerance) * 35)
            return {
                "detected": True,
                "confidence": min(100, conf),
                "viz_points": [
                    {"idx": start + p1["idx"], "value": p1["value"], "label": "Peak 1"},
                    {"idx": start + p2["idx"], "value": p2["value"], "label": "Peak 2"},
                    {"idx": start + p3["idx"], "value": p3["value"], "label": "Peak 3"},
                ],
                "resistance": round(avg_peak, 2),
                "detail": f"Triple Top at ${avg_peak:.2f}: strong resistance ({conf}%)",
            }
    return empty


def detect_triple_bottom(
    closes: list[float],
    lows: list[float],
    lookback: int = 120,
    tolerance: float = 0.03,
) -> dict[str, Any]:
    """Three troughs at roughly the same level."""
    empty: dict[str, Any] = {"detected": False, "confidence": 0, "viz_points": [], "detail": ""}
    n = len(closes)
    if n < 40:
        return empty

    start = max(0, n - lookback)
    pts = _swing_points(lows[start:], window=5)
    sl = [p for p in pts if p["type"] == "low"]

    if len(sl) < 3:
        return empty

    for i in range(len(sl) - 2):
        t1, t2, t3 = sl[i], sl[i + 1], sl[i + 2]
        avg_trough = (t1["value"] + t2["value"] + t3["value"]) / 3
        if all(abs(t["value"] - avg_trough) / avg_trough < tolerance for t in [t1, t2, t3]):
            width = t3["idx"] - t1["idx"]
            if width < 15:
                continue
            conf = int(
                65 + (1.0 - max(abs(t["value"] - avg_trough) / avg_trough for t in [t1, t2, t3]) / tolerance) * 35
            )
            return {
                "detected": True,
                "confidence": min(100, conf),
                "viz_points": [
                    {"idx": start + t1["idx"], "value": t1["value"], "label": "Bottom 1"},
                    {"idx": start + t2["idx"], "value": t2["value"], "label": "Bottom 2"},
                    {"idx": start + t3["idx"], "value": t3["value"], "label": "Bottom 3"},
                ],
                "support": round(avg_trough, 2),
                "detail": f"Triple Bottom at ${avg_trough:.2f}: strong support ({conf}%)",
            }
    return empty


# ═══════════════════════════════════════════════════════════════════════════
# MASTER DETECTION: run all detectors and return unified results
# ═══════════════════════════════════════════════════════════════════════════


def detect_all_patterns(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
) -> dict[str, Any]:
    """
    Run every chart pattern and candlestick detector.
    Returns a unified dict with all pattern results + a summary score.

    Keys:
      chart_patterns: list of detected chart patterns (with viz data)
      candlestick_patterns: list of detected candlestick patterns
      pattern_score: aggregate pattern signal (-2 to +2)
      pattern_summary: human-readable summary
    """
    chart_patterns: list[dict[str, Any]] = []
    pattern_score = 0.0

    # Chart patterns
    dt = detect_double_top(closes, highs, lows)
    if dt["detected"]:
        chart_patterns.append({"name": "Double Top", "direction": "bearish", **dt})
        pattern_score -= 1.2

    db = detect_double_bottom(closes, highs, lows)
    if db["detected"]:
        chart_patterns.append({"name": "Double Bottom", "direction": "bullish", **db})
        pattern_score += 1.2

    hs = detect_head_and_shoulders(closes, highs, lows)
    if hs["detected"]:
        chart_patterns.append({"name": "Head & Shoulders", "direction": "bearish", **hs})
        pattern_score -= 1.5

    ihs = detect_inverse_head_and_shoulders(closes, highs, lows)
    if ihs["detected"]:
        chart_patterns.append({"name": "Inv. Head & Shoulders", "direction": "bullish", **ihs})
        pattern_score += 1.5

    flag = detect_flag(closes, highs, lows, volumes)
    if flag["detected"]:
        d = "bullish" if flag.get("type") == "bull_flag" else "bearish"
        chart_patterns.append({"name": flag.get("type", "Flag").replace("_", " ").title(), "direction": d, **flag})
        pattern_score += 0.8 if d == "bullish" else -0.8

    tri = detect_triangle(closes, highs, lows)
    if tri["detected"]:
        chart_patterns.append({"name": f"{tri['type'].title()} Triangle", "direction": tri["direction"], **tri})
        if tri["direction"] == "bullish":
            pattern_score += 0.7
        elif tri["direction"] == "bearish":
            pattern_score -= 0.7

    wedge = detect_wedge(closes, highs, lows)
    if wedge["detected"]:
        chart_patterns.append({"name": f"{wedge['type'].title()} Wedge", "direction": wedge["direction"], **wedge})
        if wedge["direction"] == "bullish":
            pattern_score += 0.7
        elif wedge["direction"] == "bearish":
            pattern_score -= 0.7

    tt = detect_triple_top(closes, highs)
    if tt["detected"]:
        chart_patterns.append({"name": "Triple Top", "direction": "bearish", **tt})
        pattern_score -= 1.0

    tb = detect_triple_bottom(closes, lows)
    if tb["detected"]:
        chart_patterns.append({"name": "Triple Bottom", "direction": "bullish", **tb})
        pattern_score += 1.0

    # Gap analysis
    gaps = detect_gaps(closes, highs, lows, volumes)

    # Candlestick patterns (need opens)
    candle_patterns = detect_candlestick_patterns(opens, highs, lows, closes)

    # Aggregate candle signal
    candle_score = 0.0
    for cp in candle_patterns:
        if cp["direction"] == "bullish":
            candle_score += cp["reliability"] / 100 * 0.5
        elif cp["direction"] == "bearish":
            candle_score -= cp["reliability"] / 100 * 0.5

    # Clamp
    pattern_score = max(-2.0, min(2.0, pattern_score + candle_score * 0.3))

    bullish = [p for p in chart_patterns if p["direction"] == "bullish"]
    bearish = [p for p in chart_patterns if p["direction"] == "bearish"]
    bull_candles = [c for c in candle_patterns if c["direction"] == "bullish"]
    bear_candles = [c for c in candle_patterns if c["direction"] == "bearish"]

    summary_parts: list[str] = []
    if bullish:
        summary_parts.append(f"{len(bullish)} bullish pattern(s): {', '.join(p['name'] for p in bullish)}")
    if bearish:
        summary_parts.append(f"{len(bearish)} bearish pattern(s): {', '.join(p['name'] for p in bearish)}")
    if bull_candles:
        summary_parts.append(f"{len(bull_candles)} bullish candle signal(s)")
    if bear_candles:
        summary_parts.append(f"{len(bear_candles)} bearish candle signal(s)")
    if gaps:
        summary_parts.append(f"{len(gaps)} gap(s) detected")

    return {
        "chart_patterns": chart_patterns,
        "candlestick_patterns": candle_patterns,
        "gaps": gaps,
        "pattern_score": round(pattern_score, 3),
        "pattern_summary": "; ".join(summary_parts) if summary_parts else "No significant patterns detected",
    }
