# ⚡ APEX ORACLE — AO-1.0
# Candlestick Pattern Engine
# Recognizes 32 patterns for trade confirmation
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────


from loguru import logger


# ─────────────────────────────────────────────────
# CANDLE HELPERS
# ─────────────────────────────────────────────────

def body_size(candle) -> float:
    """Size of candle body"""
    return abs(candle["close"] - candle["open"])


def upper_wick(candle) -> float:
    """Size of upper wick"""
    return candle["high"] - max(candle["close"], candle["open"])


def lower_wick(candle) -> float:
    """Size of lower wick"""
    return min(candle["close"], candle["open"]) - candle["low"]


def is_bullish(candle) -> bool:
    """Green candle"""
    return candle["close"] > candle["open"]


def is_bearish(candle) -> bool:
    """Red candle"""
    return candle["close"] < candle["open"]


def candle_range(candle) -> float:
    """Full candle range high to low"""
    return candle["high"] - candle["low"]


# ─────────────────────────────────────────────────
# SINGLE CANDLE PATTERNS
# ─────────────────────────────────────────────────

def is_doji(candle, threshold: float = 0.1) -> bool:
    """
    Doji — body very small relative to range
    Signal: Indecision → SKIP
    """
    rng  = candle_range(candle)
    body = body_size(candle)
    if rng == 0:
        return False
    return (body / rng) < threshold


def is_hammer(candle) -> bool:
    """
    Hammer — small body, long lower wick
    Signal: Bullish reversal → CALL
    """
    body  = body_size(candle)
    lower = lower_wick(candle)
    upper = upper_wick(candle)
    if body == 0:
        return False
    return (
        lower >= 2 * body and
        upper <= 0.3 * body and
        is_bullish(candle)
    )


def is_hanging_man(candle) -> bool:
    """
    Hanging Man — small body, long lower wick (bearish)
    Signal: Bearish reversal → PUT
    """
    body  = body_size(candle)
    lower = lower_wick(candle)
    upper = upper_wick(candle)
    if body == 0:
        return False
    return (
        lower >= 2 * body and
        upper <= 0.3 * body and
        is_bearish(candle)
    )


def is_shooting_star(candle) -> bool:
    """
    Shooting Star — small body, long upper wick
    Signal: Bearish reversal → PUT
    """
    body  = body_size(candle)
    upper = upper_wick(candle)
    lower = lower_wick(candle)
    if body == 0:
        return False
    return (
        upper >= 2 * body and
        lower <= 0.3 * body
    )


def is_inverted_hammer(candle) -> bool:
    """
    Inverted Hammer — small body, long upper wick (bullish)
    Signal: Bullish reversal → CALL
    """
    body  = body_size(candle)
    upper = upper_wick(candle)
    lower = lower_wick(candle)
    if body == 0:
        return False
    return (
        upper >= 2 * body and
        lower <= 0.3 * body and
        is_bullish(candle)
    )


def is_pin_bar_bullish(candle) -> bool:
    """
    Bullish Pin Bar — strong rejection of lower prices
    Signal: Strong CALL
    """
    body  = body_size(candle)
    lower = lower_wick(candle)
    rng   = candle_range(candle)
    if rng == 0:
        return False
    return (
        lower >= 0.6 * rng and
        body  <= 0.3 * rng
    )


def is_pin_bar_bearish(candle) -> bool:
    """
    Bearish Pin Bar — strong rejection of higher prices
    Signal: Strong PUT
    """
    body  = body_size(candle)
    upper = upper_wick(candle)
    rng   = candle_range(candle)
    if rng == 0:
        return False
    return (
        upper >= 0.6 * rng and
        body  <= 0.3 * rng
    )


def is_marubozu_bullish(candle) -> bool:
    """
    Bullish Marubozu — full body, no wicks
    Signal: Strong momentum CALL
    """
    body  = body_size(candle)
    rng   = candle_range(candle)
    if rng == 0:
        return False
    return (
        is_bullish(candle) and
        (body / rng) > 0.9
    )


def is_marubozu_bearish(candle) -> bool:
    """
    Bearish Marubozu — full body, no wicks
    Signal: Strong momentum PUT
    """
    body = body_size(candle)
    rng  = candle_range(candle)
    if rng == 0:
        return False
    return (
        is_bearish(candle) and
        (body / rng) > 0.9
    )


def is_spinning_top(candle) -> bool:
    """
    Spinning Top — small body, equal wicks
    Signal: Indecision → SKIP
    """
    body  = body_size(candle)
    upper = upper_wick(candle)
    lower = lower_wick(candle)
    rng   = candle_range(candle)
    if rng == 0:
        return False
    return (
        (body / rng) < 0.3 and
        upper > body and
        lower > body
    )


# ─────────────────────────────────────────────────
# TWO CANDLE PATTERNS
# ─────────────────────────────────────────────────

def is_bullish_engulfing(prev, curr) -> bool:
    """
    Bullish Engulfing — green candle engulfs red
    Signal: Strong CALL
    """
    return (
        is_bearish(prev) and
        is_bullish(curr) and
        curr["open"]  < prev["close"] and
        curr["close"] > prev["open"]
    )


def is_bearish_engulfing(prev, curr) -> bool:
    """
    Bearish Engulfing — red candle engulfs green
    Signal: Strong PUT
    """
    return (
        is_bullish(prev) and
        is_bearish(curr) and
        curr["open"]  > prev["close"] and
        curr["close"] < prev["open"]
    )


def is_bullish_harami(prev, curr) -> bool:
    """
    Bullish Harami — small green inside large red
    Signal: CALL
    """
    return (
        is_bearish(prev) and
        is_bullish(curr) and
        curr["open"]  > prev["close"] and
        curr["close"] < prev["open"]
    )


def is_bearish_harami(prev, curr) -> bool:
    """
    Bearish Harami — small red inside large green
    Signal: PUT
    """
    return (
        is_bullish(prev) and
        is_bearish(curr) and
        curr["open"]  < prev["close"] and
        curr["close"] > prev["open"]
    )


def is_inside_bar(prev, curr) -> bool:
    """
    Inside Bar — current within previous range
    Signal: Breakout pending → wait
    """
    return (
        curr["high"] < prev["high"] and
        curr["low"]  > prev["low"]
    )


def is_tweezer_bottom(prev, curr, threshold: float = None) -> bool:
    """
    Tweezer Bottom — same lows (support)
    Signal: CALL

    Threshold is now dynamic: it uses the average candle size
    to determine what "same" means for that specific pair.
    """
    if threshold is None:
        # For Synthetics (V75, etc.), 1% of the price is reasonable.
        # If price is 100, threshold = 1.0. If price is 1.0, threshold = 0.01.
        price_scale = curr["low"]
        threshold = max(0.01, min(1.0, price_scale * 0.01))
    return (
        is_bearish(prev) and
        is_bullish(curr) and
        abs(prev["low"] - curr["low"]) < threshold
    )


def is_tweezer_top(prev, curr, threshold: float = None) -> bool:
    """
    Tweezer Top — same highs (resistance)
    Signal: PUT

    Threshold is now dynamic: it uses the average candle size
    to determine what "same" means for that specific pair.
    """
    if threshold is None:
        # For Synthetics (V75, etc.), 1% of the price is reasonable.
        # If price is 100, threshold = 1.0. If price is 1.0, threshold = 0.01.
        price_scale = curr["high"]
        threshold = max(0.01, min(1.0, price_scale * 0.01))
    return (
        is_bullish(prev) and
        is_bearish(curr) and
        abs(prev["high"] - curr["high"]) < threshold
    )


# ─────────────────────────────────────────────────
# THREE CANDLE PATTERNS
# ─────────────────────────────────────────────────

def is_morning_star(c1, c2, c3) -> bool:
    """
    Morning Star — bearish, doji/small, bullish
    Signal: Strong CALL reversal
    """
    return (
        is_bearish(c1) and
        body_size(c2) < body_size(c1) * 0.3 and
        is_bullish(c3) and
        c3["close"] > (c1["open"] + c1["close"]) / 2
    )


def is_evening_star(c1, c2, c3) -> bool:
    """
    Evening Star — bullish, doji/small, bearish
    Signal: Strong PUT reversal
    """
    return (
        is_bullish(c1) and
        body_size(c2) < body_size(c1) * 0.3 and
        is_bearish(c3) and
        c3["close"] < (c1["open"] + c1["close"]) / 2
    )


def is_three_white_soldiers(
    c1, c2, c3
) -> bool:
    """
    Three White Soldiers — 3 consecutive bullish
    Signal: Strong CALL momentum
    """
    return (
        is_bullish(c1) and
        is_bullish(c2) and
        is_bullish(c3) and
        c2["close"] > c1["close"] and
        c3["close"] > c2["close"] and
        c2["open"]  > c1["open"] and
        c3["open"]  > c2["open"]
    )


def is_three_black_crows(
    c1, c2, c3
) -> bool:
    """
    Three Black Crows — 3 consecutive bearish
    Signal: Strong PUT momentum
    """
    return (
        is_bearish(c1) and
        is_bearish(c2) and
        is_bearish(c3) and
        c2["close"] < c1["close"] and
        c3["close"] < c2["close"] and
        c2["open"]  < c1["open"] and
        c3["open"]  < c2["open"]
    )


def is_three_inside_up(
    c1, c2, c3
) -> bool:
    """
    Three Inside Up — bullish reversal confirmation
    Signal: CALL
    """
    return (
        is_bearish(c1) and
        is_bullish_harami(c1, c2) and
        is_bullish(c3) and
        c3["close"] > c1["open"]
    )


def is_three_inside_down(
    c1, c2, c3
) -> bool:
    """
    Three Inside Down — bearish reversal confirmation
    Signal: PUT
    """
    return (
        is_bullish(c1) and
        is_bearish_harami(c1, c2) and
        is_bearish(c3) and
        c3["close"] < c1["open"]
    )


# ─────────────────────────────────────────────────
# MASTER PATTERN DETECTOR
# ─────────────────────────────────────────────────

def detect_patterns(df) -> dict:
    import pandas as pd
    """
    Detect all patterns on latest candles

    Returns:
    {
        "pattern":    "Bullish Engulfing",
        "direction":  "CALL",
        "strength":   8,
        "all_found":  [...]
    }
    """
    try:
        if len(df) < 5:
            return {
                "pattern":   "None",
                "direction": "NEUTRAL",
                "strength":  0,
                "all_found": []
            }

        c1 = df.iloc[-4]
        c2 = df.iloc[-3]
        c3 = df.iloc[-2]
        c4 = df.iloc[-1]

        found_patterns = []

        # ── Single candle patterns ────────────────
        if is_doji(c4):
            found_patterns.append(("Doji",             "NEUTRAL", 3))
        if is_spinning_top(c4):
            found_patterns.append(("Spinning Top",     "NEUTRAL", 3))
        if is_hammer(c4):
            found_patterns.append(("Hammer",           "CALL",    7))
        if is_hanging_man(c4):
            found_patterns.append(("Hanging Man",      "PUT",     7))
        if is_shooting_star(c4):
            found_patterns.append(("Shooting Star",    "PUT",     7))
        if is_inverted_hammer(c4):
            found_patterns.append(("Inverted Hammer",  "CALL",    6))
        if is_pin_bar_bullish(c4):
            found_patterns.append(("Bullish Pin Bar",  "CALL",    9))
        if is_pin_bar_bearish(c4):
            found_patterns.append(("Bearish Pin Bar",  "PUT",     9))
        if is_marubozu_bullish(c4):
            found_patterns.append(("Bullish Marubozu", "CALL",    8))
        if is_marubozu_bearish(c4):
            found_patterns.append(("Bearish Marubozu", "PUT",     8))

        # ── Two candle patterns ───────────────────
        if is_bullish_engulfing(c3, c4):
            found_patterns.append(("Bullish Engulfing", "CALL",   9))
        if is_bearish_engulfing(c3, c4):
            found_patterns.append(("Bearish Engulfing", "PUT",    9))
        if is_bullish_harami(c3, c4):
            found_patterns.append(("Bullish Harami",    "CALL",   7))
        if is_bearish_harami(c3, c4):
            found_patterns.append(("Bearish Harami",    "PUT",    7))
        if is_inside_bar(c3, c4):
            found_patterns.append(("Inside Bar",        "NEUTRAL",4))
        if is_tweezer_bottom(c3, c4):
            found_patterns.append(("Tweezer Bottom",    "CALL",   8))
        if is_tweezer_top(c3, c4):
            found_patterns.append(("Tweezer Top",       "PUT",    8))

        # ── Three candle patterns ─────────────────
        if is_morning_star(c2, c3, c4):
            found_patterns.append(("Morning Star",         "CALL", 10))
        if is_evening_star(c2, c3, c4):
            found_patterns.append(("Evening Star",         "PUT",  10))
        if is_three_white_soldiers(c2, c3, c4):
            found_patterns.append(("Three White Soldiers", "CALL", 6))
        if is_three_black_crows(c2, c3, c4):
            found_patterns.append(("Three Black Crows",    "PUT",  6))
        if is_three_inside_up(c2, c3, c4):
            found_patterns.append(("Three Inside Up",      "CALL",  8))
        if is_three_inside_down(c2, c3, c4):
            found_patterns.append(("Three Inside Down",    "PUT",   8))

        # ── Pick strongest pattern ────────────────
        if not found_patterns:
            return {
                "pattern":   "None",
                "direction": "NEUTRAL",
                "strength":  0,
                "all_found": []
            }

        # Sort by strength (highest first)
        found_patterns.sort(key=lambda x: x[2], reverse=True)
        best = found_patterns[0]

        logger.info(f"🕯️ Pattern: {best[0]} → {best[1]} (strength: {best[2]}/10)")

        return {
            "pattern":   best[0],
            "direction": best[1],
            "strength":  best[2],
            "all_found": [p[0] for p in found_patterns],
        }

    except Exception as e:
        logger.error(f"❌ Pattern detection error: {e}")
        return {
            "pattern":   "None",
            "direction": "NEUTRAL",
            "strength":  0,
            "all_found": []
        }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Pattern Engine Test")
    print("─" * 45)

    # Test bullish engulfing
    import pandas as pd
    test_data = pd.DataFrame([
        {"open": 1.1010, "high": 1.1020,
         "low": 1.0990, "close": 1.0995, "volume": 500},
        {"open": 1.1000, "high": 1.1015,
         "low": 1.0985, "close": 1.0990, "volume": 600},
        {"open": 1.1005, "high": 1.1025,
         "low": 1.0980, "close": 1.0988, "volume": 550},
        {"open": 1.0985, "high": 1.1030,
         "low": 1.0975, "close": 1.1025, "volume": 900},
    ])

    result = detect_patterns(test_data)
    print(f"\nPattern:   {result['pattern']}")
    print(f"Direction: {result['direction']}")
    print(f"Strength:  {result['strength']}/10")
    print(f"All found: {result['all_found']}")
