# ⚡ APEX ORACLE — AO-2.4
# Confluence Engine — REBUILT
# Strategy: Mean Reversion Scoring for Synthetic Indices
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
#
# KEY INSIGHT: Deriv synthetic indices OSCILLATE. They do NOT trend.
# This engine bets on price snapping BACK from extremes.
#
# SCORE GATES (AO-2.4):
#   score >= 9  → TRADE  (real money, 75%+ confidence)
#   score 7-8   → PHANTOM (shadow log only, no real money)
#   score < 7   → SKIP
# ─────────────────────────────────────────────────

import numpy as np
import pandas as pd
from loguru import logger
import config

# ─────────────────────────────────────────────────
# SCORING THRESHOLDS
# ─────────────────────────────────────────────────

MIN_SCORE           = config.MIN_SCORE           # 9 — live trade
PHANTOM_MIN_SCORE   = config.PHANTOM_MIN_SCORE   # 7 — shadow only
RSI_EXTREME_HIGH    = config.RSI_EXTREME_HIGH    # 78
RSI_STRONG_HIGH     = config.RSI_STRONG_HIGH     # 72
RSI_EXTREME_LOW     = config.RSI_EXTREME_LOW     # 22
RSI_STRONG_LOW      = config.RSI_STRONG_LOW      # 28
BB_TOUCH_THRESHOLD  = 0.98
ROC_PERIOD          = 5
ROC_FADE_THRESHOLD  = 0.0
COOLDOWN_PER_PAIR   = 120


# ─────────────────────────────────────────────────
# INDICATOR CALCULATORS
# ─────────────────────────────────────────────────

def _calc_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas   = np.diff(closes)
    gains    = np.where(deltas > 0, deltas, 0.0)
    losses   = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 2)


def _calc_bb(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> dict:
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0}
    window = closes[-period:]
    middle = float(np.mean(window))
    std    = float(np.std(window))
    return {
        "upper":  round(middle + std_dev * std, 6),
        "middle": round(middle, 6),
        "lower":  round(middle - std_dev * std, 6),
    }


def _calc_roc(closes: np.ndarray, period: int = 5) -> float:
    if len(closes) < period + 1:
        return 0.0
    prev = closes[-(period + 1)]
    curr = closes[-1]
    if prev == 0:
        return 0.0
    return round(float((curr - prev) / prev), 6)


def _detect_direction_flip(closes: np.ndarray, lookback: int = 3) -> str:
    if len(closes) < lookback + 1:
        return "NONE"
    recent      = closes[-(lookback + 1):]
    was_falling = recent[-2] < recent[-3] if len(recent) >= 3 else False
    now_rising  = recent[-1] > recent[-2]
    if was_falling and now_rising:
        return "UP_FLIP"
    was_rising  = recent[-2] > recent[-3] if len(recent) >= 3 else False
    now_falling = recent[-1] < recent[-2]
    if was_rising and now_falling:
        return "DOWN_FLIP"
    return "NONE"


def _is_local_extreme(closes: np.ndarray, lookback: int = 10) -> str:
    if len(closes) < lookback:
        return "NONE"
    window  = closes[-lookback:]
    current = closes[-1]
    high    = np.max(window)
    low     = np.min(window)
    spread  = high - low
    if spread == 0:
        return "NONE"
    if current >= high - (spread * 0.15):
        return "HIGH"
    if current <= low + (spread * 0.15):
        return "LOW"
    return "NONE"


# ─────────────────────────────────────────────────
# CORE SCORING ENGINE
# ─────────────────────────────────────────────────

def _score_direction(
    direction: str,
    rsi:       float,
    bb:        dict,
    price:     float,
    roc:       float,
    flip:      str,
    extreme:   str,
) -> tuple:
    """
    Score a direction for mean reversion.
    Max = 12 points.

    RSI extreme:         +3
    RSI strong:          +2
    BB band touch:       +3
    BB band near mid:    +1
    ROC fading:          +2
    Direction flip:      +2
    Local extreme:       +1
    """
    score     = 0
    breakdown = {}

    if direction == "CALL":
        if rsi <= RSI_EXTREME_LOW:
            score += 3
            breakdown["rsi"] = f"+3 (RSI={rsi} extreme oversold)"
        elif rsi <= RSI_STRONG_LOW:
            score += 2
            breakdown["rsi"] = f"+2 (RSI={rsi} oversold)"
        else:
            breakdown["rsi"] = f"0 (RSI={rsi} not oversold)"

        if bb["lower"] > 0:
            if price <= bb["lower"] * (2 - BB_TOUCH_THRESHOLD):
                score += 3
                breakdown["bb"] = "+3 (price at lower BB)"
            elif price <= bb["middle"]:
                score += 1
                breakdown["bb"] = "+1 (price below BB midline)"
            else:
                breakdown["bb"] = "0 (price above BB midline)"

        if roc > ROC_FADE_THRESHOLD:
            score += 2
            breakdown["roc"] = f"+2 (ROC={roc:.4f} building upward)"
        else:
            breakdown["roc"] = f"0 (ROC={roc:.4f} not building)"

        if flip == "UP_FLIP":
            score += 2
            breakdown["flip"] = "+2 (price just reversed UP)"
        else:
            breakdown["flip"] = f"0 (no up flip, flip={flip})"

        if extreme == "LOW":
            score += 1
            breakdown["extreme"] = "+1 (at local price low)"
        else:
            breakdown["extreme"] = "0"

    elif direction == "PUT":
        if rsi >= RSI_EXTREME_HIGH:
            score += 3
            breakdown["rsi"] = f"+3 (RSI={rsi} extreme overbought)"
        elif rsi >= RSI_STRONG_HIGH:
            score += 2
            breakdown["rsi"] = f"+2 (RSI={rsi} overbought)"
        else:
            breakdown["rsi"] = f"0 (RSI={rsi} not overbought)"

        if bb["upper"] > 0:
            if price >= bb["upper"] * BB_TOUCH_THRESHOLD:
                score += 3
                breakdown["bb"] = "+3 (price at upper BB)"
            elif price >= bb["middle"]:
                score += 1
                breakdown["bb"] = "+1 (price above BB midline)"
            else:
                breakdown["bb"] = "0 (price below BB midline)"

        if roc < ROC_FADE_THRESHOLD:
            score += 2
            breakdown["roc"] = f"+2 (ROC={roc:.4f} fading downward)"
        else:
            breakdown["roc"] = f"0 (ROC={roc:.4f} not fading)"

        if flip == "DOWN_FLIP":
            score += 2
            breakdown["flip"] = "+2 (price just reversed DOWN)"
        else:
            breakdown["flip"] = f"0 (no down flip, flip={flip})"

        if extreme == "HIGH":
            score += 1
            breakdown["extreme"] = "+1 (at local price high)"
        else:
            breakdown["extreme"] = "0"

    return score, breakdown


# ─────────────────────────────────────────────────
# MAIN CONFLUENCE CALCULATOR
# ─────────────────────────────────────────────────

def calculate_confluence(
    candles_primary: list,
    candles_by_tf:   dict,
    pair:            str = "",
) -> dict:
    """
    Mean Reversion Confluence Engine — AO-2.4

    Returns action = "TRADE" only for score >= 9 (live money).
    Returns action = "PHANTOM" for score 7-8 (shadow log only).
    Returns action = "SKIP" for score < 7.
    """
    try:
        if not candles_primary or len(candles_primary) < 30:
            return _skip("Not enough candle data (need 30+)")

        closes = np.array([
            float(c.get("close", c.get("Close", 0)))
            for c in candles_primary
            if c.get("close", c.get("Close", 0)) != 0
        ])

        if len(closes) < 25:
            return _skip("Not enough valid close prices")

        price   = float(closes[-1])
        rsi     = _calc_rsi(closes, period=14)
        bb      = _calc_bb(closes, period=20, std_dev=2.0)
        roc     = _calc_roc(closes, period=ROC_PERIOD)
        flip    = _detect_direction_flip(closes, lookback=3)
        extreme = _is_local_extreme(closes, lookback=15)

        call_score, call_breakdown = _score_direction(
            "CALL", rsi, bb, price, roc, flip, extreme
        )
        put_score, put_breakdown = _score_direction(
            "PUT", rsi, bb, price, roc, flip, extreme
        )

        if call_score > put_score:
            direction = "CALL"
            score     = call_score
            breakdown = call_breakdown
        elif put_score > call_score:
            direction = "PUT"
            score     = put_score
            breakdown = put_breakdown
        else:
            return _skip("No clear directional edge (tied scores)")

        opposing = put_score if direction == "CALL" else call_score
        if (score - opposing) < 2:
            return _skip(
                f"Score margin too small ({direction}={score} vs opp={opposing})"
            )

        # ── Below phantom threshold — hard skip ────
        if score < PHANTOM_MIN_SCORE:
            return _skip(f"Score {score}/12 below minimum {PHANTOM_MIN_SCORE} — skipping")

        logger.info(
            f"🎯 {pair} | {direction} | Score={score}/12 | "
            f"RSI={rsi} | Flip={flip} | Extreme={extreme}"
        )

        confidence_pct = round((score / 12) * 100, 1)

        base_result = {
            "direction":  direction,
            "confidence": confidence_pct,
            "score":      score,
            "stake_size": "FULL",
            "reason":     (
                f"{direction} signal | Score: {score}/12 | "
                f"RSI={rsi} | ROC={roc:.4f} | Flip={flip}"
            ),
            "pattern":    "MEAN_REVERSION",
            "breakdown": {
                "call_score": call_score,
                "put_score":  put_score,
                "indicators": {
                    "agreements": score,
                    "details": {
                        "rsi":     {"value": rsi,     "signal": breakdown.get("rsi", "")},
                        "bb":      {"value": price,   "signal": breakdown.get("bb", "")},
                        "roc":     {"value": roc,     "signal": breakdown.get("roc", "")},
                        "flip":    {"value": flip,    "signal": breakdown.get("flip", "")},
                        "extreme": {"value": extreme, "signal": breakdown.get("extreme", "")},
                    }
                },
                "pattern":    {"strength": score},
                "volatility": {"level": "MEDIUM"},
                "timeframes": {"agreements": 1, "total": 1},
            },
        }

        # ── Score 7-8: phantom only, no real trade ─
        if score < MIN_SCORE:
            logger.info(
                f"👻 {pair} | Score={score}/12 — PHANTOM only "
                f"(need {MIN_SCORE}+ for live trade)"
            )
            base_result["action"] = "PHANTOM"
            return base_result

        # ── Score 9+: approve for live trade ──────
        base_result["action"] = "TRADE"
        return base_result

    except Exception as e:
        import traceback
        logger.error(f"❌ Confluence error on {pair}: {e}")
        logger.error(traceback.format_exc())
        return _skip(str(e))


# ─────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────

def _skip(reason: str) -> dict:
    return {
        "direction":  "SKIP",
        "confidence": 0,
        "score":      0,
        "action":     "SKIP",
        "stake_size": "SKIP",
        "reason":     reason,
        "pattern":    "None",
        "breakdown":  {},
    }