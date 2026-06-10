# ⚡ APEX ORACLE — AO-1.0
# Confluence Engine — Combines all signals
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

from loguru import logger
from core.signals   import generate_signal, prepare_dataframe
from core.patterns  import detect_patterns
from core.volatility import check_volatility

# ─────────────────────────────────────────────────
# WEIGHTS — How much each factor contributes
# ─────────────────────────────────────────────────

WEIGHTS = {
    "indicators": 40,
    "patterns":   25,
    "volatility": 15,
    "timeframe":  20,
}


# ─────────────────────────────────────────────────
# SCORING HELPERS
# ─────────────────────────────────────────────────

def score_indicators(signal: dict, direction: str) -> dict:
    indicators = signal.get("indicators", {})
    agreements = 0
    total      = 0

    for name, data in indicators.items():
        sig = data.get("signal", "NEUTRAL")
        if sig not in ("NEUTRAL", "SQUEEZE"):
            total += 1
            if sig == direction:
                agreements += 1

    score = (agreements / total * 100) if total > 0 else 0
    return {
        "score":      round(score, 1),
        "agreements": agreements,
        "total":      total,
        "details":    indicators,
    }


def score_pattern(pat_data: dict, direction: str) -> dict:
    pattern   = pat_data.get("pattern", "None")
    pat_dir   = pat_data.get("direction", "NEUTRAL")
    strength  = pat_data.get("strength", 0)

    if pattern == "None" or pat_dir == "NEUTRAL":
        return {"score": 50, "pattern": pattern, "strength": 0}

    if pat_dir == direction:
        score = 50 + (strength * 5)
    else:
        score = 50 - (strength * 5)

    return {
        "score":    min(100, max(0, score)),
        "pattern":  pattern,
        "strength": strength,
    }


def score_volatility(vol_data: dict) -> dict:
    level = vol_data.get("level", "MEDIUM")
    scores = {
        "LOW":     30,
        "MEDIUM":  80,
        "HIGH":    40,
        "EXTREME": 0,
    }
    return {
        "score": scores.get(level, 50),
        "level": level,
    }


def score_timeframes(candles_by_tf: dict, direction: str) -> dict:
    agreements = 0
    total      = 0

    for tf, candles in candles_by_tf.items():
        if tf == "5":
            continue
        if not candles or len(candles) < 20:
            continue
        sig = generate_signal(candles, "")
        if sig["direction"] != "SKIP":
            total += 1
            if sig["direction"] == direction:
                agreements += 1

    score = (agreements / total * 100) if total > 0 else 50
    return {
        "score":      round(score, 1),
        "agreements": agreements,
        "total":      total,
    }


# ─────────────────────────────────────────────────
# MASTER CONFLUENCE CALCULATOR
# ─────────────────────────────────────────────────

def calculate_confluence(
    candles_primary: list,
    candles_by_tf:   dict,
    pair:            str = "",
) -> dict:
    try:
        if not candles_primary or len(candles_primary) < 50:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     "Not enough candle data",
            }

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

        df         = prepare_dataframe(candles_primary)
        ind_score  = score_indicators(primary_signal, direction)
        pat_data   = detect_patterns(df)
        pat_score  = score_pattern(pat_data, direction)
        vol_data   = check_volatility(df, pair)
        vol_score  = score_volatility(vol_data)
        tf_score   = score_timeframes(candles_by_tf, direction)

        final_score = (
            (ind_score["score"] * WEIGHTS["indicators"] / 100) +
            (pat_score["score"] * WEIGHTS["patterns"]   / 100) +
            (vol_score["score"] * WEIGHTS["volatility"] / 100) +
            (tf_score["score"]  * WEIGHTS["timeframe"]  / 100)
        )
        final_score = round(final_score, 1)

        if ind_score["agreements"] >= 3:
            final_score = max(final_score, 75.0)

        if ind_score["agreements"] >= 3 and final_score >= 65:
            if not vol_data["tradeable"]:
                logger.warning(f"⚠️ Volatility flagged as non-tradeable, but overriding due to strong signal ({ind_score['agreements']}/5 agree, Score: {final_score}%).")

            if final_score >= 90:
                action     = "TRADE"
                stake_size = "FULL"
                reason     = f"🔥 Exceptional {direction} confluence!"
            elif final_score >= 75:
                action     = "TRADE"
                stake_size = "FULL"
                reason     = f"✅ Strong {direction} confluence"
            elif final_score >= 65:
                action     = "TRADE"
                stake_size = "HALF"
                reason     = f"⚡ Moderate {direction} — half stake"
            else:
                action     = "SKIP"
                stake_size = "SKIP"
                reason     = f"❌ Weak confluence ({final_score}%) — skipping"
        else:
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = f"❌ Weak confluence ({final_score}%) — skipping"

        if tf_score["total"] > 0 and tf_score["agreements"] == 0 and action == "TRADE":
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = "No timeframes agree — skipping"

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