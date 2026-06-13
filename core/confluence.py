# ⚡ APEX ORACLE — AO-2.0
# Confluence Engine — REBUILT
# Strategy: Mean Reversion Scoring for Synthetic Indices
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
#
# KEY INSIGHT: Deriv synthetic indices OSCILLATE. They do NOT trend.
# This engine bets on price snapping BACK from extremes.
# A trade only fires when score >= MIN_SCORE (8 out of 12 max).
# Fewer trades. Better trades. Higher win rate.
# ─────────────────────────────────────────────────

import numpy as np
import pandas as pd
from loguru import logger
import config

# ─────────────────────────────────────────────────
# SCORING THRESHOLDS — reads from config.py
# ─────────────────────────────────────────────────

MIN_SCORE           = config.MIN_SCORE           # 8 — reads from config
RSI_EXTREME_HIGH    = config.RSI_EXTREME_HIGH    # 78 — stricter overbought
RSI_STRONG_HIGH     = config.RSI_STRONG_HIGH     # 72
RSI_EXTREME_LOW     = config.RSI_EXTREME_LOW     # 22 — stricter oversold
RSI_STRONG_LOW      = config.RSI_STRONG_LOW      # 28
BB_TOUCH_THRESHOLD  = 0.98   # Price within 2% of BB band = touching it
ROC_PERIOD          = 5      # Rate of Change lookback period
ROC_FADE_THRESHOLD  = 0.0    # ROC crossing zero = momentum fading
COOLDOWN_PER_PAIR   = 120    # Seconds between trades on same pair


# ─────────────────────────────────────────────────
# INDICATOR CALCULATORS
# ─────────────────────────────────────────────────

def _calc_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Calculate RSI from close prices array"""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 2)


def _calc_bb(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> dict:
    """Calculate Bollinger Bands"""
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
    """Rate of Change — detects momentum fading"""
    if len(closes) < period + 1:
        return 0.0
    prev  = closes[-(period + 1)]
    curr  = closes[-1]
    if prev == 0:
        return 0.0
    return round(float((curr - prev) / prev), 6)


def _detect_direction_flip(closes: np.ndarray, lookback: int = 3) -> str:
    """
    Detect if price just reversed direction.
    Returns "UP_FLIP", "DOWN_FLIP", or "NONE"
    """
    if len(closes) < lookback + 1:
        return "NONE"
    recent = closes[-(lookback + 1):]
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
    """
    Check if current price is near a local high or low.
    Returns "HIGH", "LOW", or "NONE"
    """
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
) -> int:
    """
    Score a given direction (CALL=RISE or PUT=FALL).
    Maximum possible score = 12.
    Minimum to trade = 8 (from config).

    Scoring rules (mean reversion on synthetics):
    ─────────────────────────────────────────────
    RSI extreme:         +3 pts   (strongest signal)
    RSI strong:          +2 pts
    BB band touch:       +3 pts   (second strongest)
    BB band near:        +1 pt
    Momentum fading ROC: +2 pts
    Direction flip:      +2 pts   (confirmation)
    Local price extreme: +1 pt    (bonus)
    ─────────────────────────────────────────────
    """
    score = 0
    breakdown = {}

    if direction == "CALL":
        # ── RSI oversold ───────────────────────────
        if rsi <= RSI_EXTREME_LOW:
            score += 3
            breakdown["rsi"] = f"+3 (RSI={rsi} extreme oversold)"
        elif rsi <= RSI_STRONG_LOW:
            score += 2
            breakdown["rsi"] = f"+2 (RSI={rsi} oversold)"
        else:
            breakdown["rsi"] = f"0 (RSI={rsi} not oversold)"

        # ── BB lower band touch ────────────────────
        if bb["lower"] > 0:
            if price <= bb["lower"] * (2 - BB_TOUCH_THRESHOLD):
                score += 3
                breakdown["bb"] = "+3 (price at lower BB)"
            elif price <= bb["middle"]:
                score += 1
                breakdown["bb"] = "+1 (price below BB midline)"
            else:
                breakdown["bb"] = "0 (price above BB midline)"

        # ── Momentum ROC building upward ───────────
        if roc > ROC_FADE_THRESHOLD:
            score += 2
            breakdown["roc"] = f"+2 (ROC={roc:.4f} building upward)"
        else:
            breakdown["roc"] = f"0 (ROC={roc:.4f} not building)"

        # ── Direction flip to up ───────────────────
        if flip == "UP_FLIP":
            score += 2
            breakdown["flip"] = "+2 (price just reversed UP)"
        else:
            breakdown["flip"] = f"0 (no up flip, flip={flip})"

        # ── Local low extreme ──────────────────────
        if extreme == "LOW":
            score += 1
            breakdown["extreme"] = "+1 (at local price low)"
        else:
            breakdown["extreme"] = "0"

    elif direction == "PUT":
        # ── RSI overbought ─────────────────────────
        if rsi >= RSI_EXTREME_HIGH:
            score += 3
            breakdown["rsi"] = f"+3 (RSI={rsi} extreme overbought)"
        elif rsi >= RSI_STRONG_HIGH:
            score += 2
            breakdown["rsi"] = f"+2 (RSI={rsi} overbought)"
        else:
            breakdown["rsi"] = f"0 (RSI={rsi} not overbought)"

        # ── BB upper band touch ────────────────────
        if bb["upper"] > 0:
            if price >= bb["upper"] * BB_TOUCH_THRESHOLD:
                score += 3
                breakdown["bb"] = "+3 (price at upper BB)"
            elif price >= bb["middle"]:
                score += 1
                breakdown["bb"] = "+1 (price above BB midline)"
            else:
                breakdown["bb"] = "0 (price below BB midline)"

        # ── Momentum ROC fading downward ───────────
        if roc < ROC_FADE_THRESHOLD:
            score += 2
            breakdown["roc"] = f"+2 (ROC={roc:.4f} fading downward)"
        else:
            breakdown["roc"] = f"0 (ROC={roc:.4f} not fading)"

        # ── Direction flip to down ─────────────────
        if flip == "DOWN_FLIP":
            score += 2
            breakdown["flip"] = "+2 (price just reversed DOWN)"
        else:
            breakdown["flip"] = f"0 (no down flip, flip={flip})"

        # ── Local high extreme ─────────────────────
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
    Mean Reversion Confluence Engine for Deriv Synthetics.
    Only fires on score >= 8/12 — no weak signals allowed.
    """
    try:
        # ── Minimum data guard ─────────────────────
        if not candles_primary or len(candles_primary) < 30:
            return _skip("Not enough candle data (need 30+)")

        # ── Extract close prices ───────────────────
        closes = np.array([
            float(c.get("close", c.get("Close", 0)))
            for c in candles_primary
            if c.get("close", c.get("Close", 0)) != 0
        ])

        if len(closes) < 25:
            return _skip("Not enough valid close prices")

        price = float(closes[-1])

        # ── Calculate indicators ───────────────────
        rsi     = _calc_rsi(closes, period=14)
        bb      = _calc_bb(closes, period=20, std_dev=2.0)
        roc     = _calc_roc(closes, period=ROC_PERIOD)
        flip    = _detect_direction_flip(closes, lookback=3)
        extreme = _is_local_extreme(closes, lookback=15)

        # ── Score both directions independently ────
        call_score, call_breakdown = _score_direction(
            "CALL", rsi, bb, price, roc, flip, extreme
        )
        put_score, put_breakdown = _score_direction(
            "PUT", rsi, bb, price, roc, flip, extreme
        )

        # ── Pick winner ────────────────────────────
        if call_score > put_score:
            direction = "CALL"
            score     = call_score
            breakdown = call_breakdown
        elif put_score > call_score:
            direction = "PUT"
            score     = put_score
            breakdown = put_breakdown
        else:
            logger.debug(f"⏭️ {pair} — tied score CALL={call_score} PUT={put_score}")
            return _skip("No clear directional edge (tied scores)")

        # ── Score must beat opposing by at least 2 pts
        opposing = put_score if direction == "CALL" else call_score
        if (score - opposing) < 2:
            return _skip(
                f"Score margin too small ({direction}={score} vs opp={opposing}) — no edge"
            )

        # ── Minimum score gate — 8/12 required ────
        if score < MIN_SCORE:
            return _skip(
                f"Score {score}/12 below minimum {MIN_SCORE} — skipping"
            )

        # ── Determine stake size ───────────────────
        if score >= 10:
            stake_size = "FULL"
            label      = "🔥 EXCEPTIONAL"
        elif score >= 8:
            stake_size = "FULL"
            label      = "✅ GOOD"
        else:
            return _skip(f"Score {score}/12 below minimum {MIN_SCORE} — skipping")

        reason = (
            f"{label} {direction} signal | "
            f"Score: {score}/12 | "
            f"RSI={rsi} | BB={'touched' if score >= 8 else 'near'} | "
            f"ROC={roc:.4f} | Flip={flip}"
        )

        logger.info(
            f"🎯 {pair} | {direction} | Score={score}/12 | "
            f"RSI={rsi} | Flip={flip} | Extreme={extreme}"
        )

        confidence_pct = round((score / 12) * 100, 1)

        return {
            "direction":  direction,
            "confidence": confidence_pct,
            "score":      score,
            "action":     "TRADE",
            "stake_size": stake_size,
            "reason":     reason,
            "pattern":    "MEAN_REVERSION",
            "breakdown": {
                "call_score":  call_score,
                "put_score":   put_score,
                "indicators":  {
                    "agreements": score,
                    "details": {
                        "rsi":     {"value": rsi, "signal": breakdown.get("rsi", "")},
                        "bb":      {"value": price, "signal": breakdown.get("bb", "")},
                        "roc":     {"value": roc, "signal": breakdown.get("roc", "")},
                        "flip":    {"value": flip, "signal": breakdown.get("flip", "")},
                        "extreme": {"value": extreme, "signal": breakdown.get("extreme", "")},
                    }
                },
                "pattern":    {"strength": score},
                "volatility": {"level": "MEDIUM"},
                "timeframes": {"agreements": 1, "total": 1},
            },
        }

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