# ⚡ APEX ORACLE — AO-1.0
# Confluence Scorer — The Final Judge
# Combines ALL signals into one confidence score
# Only trades with score >= 75/100
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import pandas as pd
from loguru import logger
from core.signals    import generate_signal, prepare_dataframe
from core.patterns   import detect_patterns
from core.volatility import check_volatility


# ─────────────────────────────────────────────────
# SCORING WEIGHTS
# ─────────────────────────────────────────────────

WEIGHTS = {
    "indicators": 35,   # RSI, MACD, BB, EMA, StochRSI
    "patterns":   25,   # Candlestick patterns
    "volatility": 20,   # Volatility check
    "timeframe":  20,   # Multi-timeframe agreement
}

# Minimum score to execute a trade
MIN_CONFIDENCE = 75


# ─────────────────────────────────────────────────
# TIMEFRAME SCORER
# ─────────────────────────────────────────────────

def score_timeframes(candles_by_tf: dict, direction: str) -> dict:
    """
    Check how many timeframes agree with signal direction

    candles_by_tf = {
        "1":  [...],
        "5":  [...],
        "15": [...],
        "60": [...],
    }
    """
    try:
        agreements = 0
        total      = 0
        details    = {}

        for tf, candles in candles_by_tf.items():
            if not candles or len(candles) < 20:
                continue

            signal = generate_signal(candles)
            total += 1
            agrees = signal["direction"] == direction

            if agrees:
                agreements += 1

            details[f"{tf}min"] = {
                "direction":  signal["direction"],
                "agrees":     agrees,
                "confidence": signal["confidence"],
            }

        score = (agreements / total * 100) if total > 0 else 0

        return {
            "agreements": agreements,
            "total":      total,
            "score":      round(score, 1),
            "details":    details,
        }

    except Exception as e:
        logger.error(f"❌ Timeframe scoring error: {e}")
        return {"agreements": 0, "total": 0, "score": 0, "details": {}}


# ─────────────────────────────────────────────────
# INDICATOR SCORER
# ─────────────────────────────────────────────────

def score_indicators(signal: dict, direction: str) -> dict:
    """Score indicator agreement with direction"""
    try:
        indicators = signal.get("indicators", {})
        agreements = 0
        total      = len(indicators)
        details    = {}

        for name, data in indicators.items():
            sig    = data.get("signal", "NEUTRAL")
            agrees = sig == direction
            if agrees:
                agreements += 1
            details[name] = {"signal": sig, "agrees": agrees}

        score = (agreements / total * 100) if total > 0 else 0

        return {
            "agreements": agreements,
            "total":      total,
            "score":      round(score, 1),
            "details":    details,
        }

    except Exception as e:
        logger.error(f"❌ Indicator scoring error: {e}")
        return {"agreements": 0, "total": 5, "score": 0, "details": {}}


# ─────────────────────────────────────────────────
# PATTERN SCORER
# ─────────────────────────────────────────────────

def score_pattern(pattern: dict, direction: str) -> dict:
    """Score candlestick pattern alignment"""
    try:
        pat_dir  = pattern.get("direction", "NEUTRAL")
        strength = pattern.get("strength",  0)
        pat_name = pattern.get("pattern",   "None")

        if pat_dir == direction:
            score  = (strength / 10) * 100
            agrees = True
        elif pat_dir == "NEUTRAL" or pat_name == "None":
            score  = 50
            agrees = False
        else:
            score  = 0
            agrees = False

        return {
            "pattern":  pat_name,
            "agrees":   agrees,
            "score":    round(score, 1),
            "strength": strength,
        }

    except Exception as e:
        logger.error(f"❌ Pattern scoring error: {e}")
        return {"pattern": "None", "agrees": False, "score": 50, "strength": 0}


# ─────────────────────────────────────────────────
# VOLATILITY SCORER
# ─────────────────────────────────────────────────

def score_volatility(volatility: dict) -> dict:
    """Score volatility conditions"""
    try:
        level     = volatility.get("level",     "UNKNOWN")
        tradeable = volatility.get("tradeable", False)

        if level == "MEDIUM" and tradeable:
            score = 100
        elif level == "LOW":
            score = 30
        elif level == "HIGH":
            score = 20
        elif level == "EXTREME":
            score = 0
        else:
            score = 50

        return {
            "level":     level,
            "tradeable": tradeable,
            "score":     score,
        }

    except Exception as e:
        logger.error(f"❌ Volatility scoring error: {e}")
        return {"level": "UNKNOWN", "tradeable": False, "score": 0}


# ─────────────────────────────────────────────────
# MASTER CONFLUENCE SCORER
# ─────────────────────────────────────────────────

def calculate_confluence(
    candles_primary: list,
    candles_by_tf:   dict,
    pair:            str = "",
) -> dict:
    """
    Master confluence calculator

    Combines:
    → Indicator signals    (35%)
    → Candlestick patterns (25%)
    → Volatility check     (20%)
    → Timeframe agreement  (20%)

    Trade thresholds:
    >= 75 → TRADE FULL stake
    70-74 → TRADE HALF stake
    < 70  → SKIP

    Returns:
    {
        "direction":  "CALL" / "PUT" / "SKIP",
        "confidence": 85.5,
        "action":     "TRADE" / "SKIP",
        "stake_size": "FULL" / "HALF" / "SKIP",
        "breakdown":  {...},
        "reason":     "Strong CALL confluence"
    }
    """
    try:
        if not candles_primary or len(candles_primary) < 50:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     "Not enough candle data",
            }

        # ── Step 1: Generate primary signal ──────
        primary_signal = generate_signal(candles_primary, pair)
        direction      = primary_signal["direction"]

        if direction == "SKIP":
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     primary_signal.get("reason", "No signal"),
            }

        # ── Step 2: Score each component ─────────
        df         = prepare_dataframe(candles_primary)
        ind_score  = score_indicators(primary_signal, direction)
        pat_data   = detect_patterns(df)
        pat_score  = score_pattern(pat_data, direction)
        vol_data   = check_volatility(df, pair)
        vol_score  = score_volatility(vol_data)
        tf_score   = score_timeframes(candles_by_tf, direction)

        # ── Step 3: Calculate weighted score ─────
        final_score = (
            (ind_score["score"] * WEIGHTS["indicators"] / 100) +
            (pat_score["score"] * WEIGHTS["patterns"]   / 100) +
            (vol_score["score"] * WEIGHTS["volatility"] / 100) +
            (tf_score["score"]  * WEIGHTS["timeframe"]  / 100)
        )
        final_score = round(final_score, 1)

        # ── Step 4: Volatility override ───────────
        if not vol_data["tradeable"]:
            return {
                "direction":  "SKIP",
                "confidence": final_score,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     vol_data["reason"],
                "breakdown": {
                    "indicators": ind_score,
                    "pattern":    pat_score,
                    "volatility": vol_score,
                    "timeframes": tf_score,
                },
            }

        # ── Step 5: Determine action ──────────────
        if final_score >= 90:
            action     = "TRADE"
            stake_size = "FULL"
            reason     = f"🔥 Exceptional {direction} confluence!"
        elif final_score >= 75:
            action     = "TRADE"
            stake_size = "FULL"
            reason     = f"✅ Strong {direction} confluence"
        elif final_score >= 70:
            action     = "TRADE"
            stake_size = "HALF"
            reason     = f"⚡ Moderate {direction} — half stake"
        else:
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = f"❌ Weak confluence ({final_score}%) — skipping"

        # ── Step 6: Timeframe override ────────────
        if tf_score["agreements"] < 2 and action == "TRADE":
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = "Timeframes don't agree — skipping"

        result = {
            "direction":  direction,
            "confidence": final_score,
            "action":     action,
            "stake_size": stake_size,
            "reason":     reason,
            "pattern":    pat_data["pattern"],
            "breakdown": {
                "indicators": ind_score,
                "pattern":    pat_score,
                "volatility": vol_score,
                "timeframes": tf_score,
            },
        }

        emoji = "🚀" if action == "TRADE" else "⏸️"
        logger.info(
            f"{emoji} {pair} Confluence: {direction} | "
            f"Score: {final_score}% | Action: {action} | "
            f"Pattern: {pat_data['pattern']}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Confluence calculation error: {e}")
        return {
            "direction":  "SKIP",
            "confidence": 0,
            "action":     "SKIP",
            "stake_size": "SKIP",
            "reason":     str(e),
        }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Confluence Scorer Test")
    print("─" * 45)

    import random

    def make_candles(n=100):
        p = 1.1000
        result = []
        for i in range(n):
            change = random.uniform(-0.0008, 0.0008)
            o = p
            c = p + change
            h = max(o, c) + random.uniform(0, 0.0003)
            l = min(o, c) - random.uniform(0, 0.0003)
            result.append({
                "timestamp": i * 300,
                "open": o, "high": h,
                "low":  l, "close": c,
            })
            p = c
        return result

    primary = make_candles(100)
    tf_data = {
        "1":  make_candles(100),
        "5":  primary,
        "15": make_candles(100),
        "60": make_candles(100),
    }

    result = calculate_confluence(primary, tf_data, "V75")

    print(f"\nDirection:  {result['direction']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Action:     {result['action']}")
    print(f"Stake Size: {result['stake_size']}")
    print(f"Pattern:    {result['pattern']}")
    print(f"Reason:     {result['reason']}")
    print(f"\nBreakdown:")
    for k, v in result["breakdown"].items():
        print(f"  {k}: score={v.get('score', 0)}%")