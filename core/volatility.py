# ⚡ APEX ORACLE — AO-1.0
# Volatility Thermometer
# Measures market volatility before every trade
# LOW = skip | MEDIUM = trade | HIGH = skip | EXTREME = shutdown
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import pandas as pd
import numpy as np
from loguru import logger


# ─────────────────────────────────────────────────
# VOLATILITY LEVELS
# ─────────────────────────────────────────────────

VOLATILITY_LEVELS = {
    "low":     0.0003,   # Below this = skip (no movement)
    "medium":  0.0015,   # Between low and high = TRADE ✅
    "high":    0.0030,   # Above this = skip (unpredictable)
    "extreme": 0.0060,   # Above this = EMERGENCY SHUTDOWN
}


# ─────────────────────────────────────────────────
# ATR CALCULATION
# ─────────────────────────────────────────────────

def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate Average True Range
    Best measure of market volatility
    """
    try:
        high       = df["high"]
        low        = df["low"]
        close      = df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return float(atr.iloc[-1])

    except Exception as e:
        logger.error(f"❌ ATR calculation error: {e}")
        return 0.0


# ─────────────────────────────────────────────────
# WICK ANALYSIS
# ─────────────────────────────────────────────────

def analyze_wicks(df: pd.DataFrame) -> dict:
    """
    Analyze candle body vs wick ratio
    Large wick = rejection signal
    Small body = indecision = skip
    """
    try:
        candle    = df.iloc[-1]
        body      = abs(candle["close"] - candle["open"])
        upper     = candle["high"] - max(candle["close"], candle["open"])
        lower     = min(candle["close"], candle["open"]) - candle["low"]
        total_rng = candle["high"] - candle["low"]

        if total_rng == 0:
            return {"type": "NEUTRAL", "body_ratio": 0, "wick_ratio": 0}

        body_ratio = body / total_rng
        wick_ratio = (upper + lower) / total_rng

        # Large wick = price rejection
        if wick_ratio > 0.7:
            wick_type = "REJECTION"
        # Small body = indecision
        elif body_ratio < 0.2:
            wick_type = "INDECISION"
        # Strong body = momentum
        elif body_ratio > 0.7:
            wick_type = "MOMENTUM"
        else:
            wick_type = "NORMAL"

        return {
            "type":       wick_type,
            "body_ratio": round(body_ratio, 3),
            "wick_ratio": round(wick_ratio, 3),
            "upper_wick": round(upper, 5),
            "lower_wick": round(lower, 5),
        }

    except Exception as e:
        logger.error(f"❌ Wick analysis error: {e}")
        return {"type": "NEUTRAL", "body_ratio": 0, "wick_ratio": 0}


# ─────────────────────────────────────────────────
# MOMENTUM ANALYSIS
# ─────────────────────────────────────────────────

def analyze_momentum(df: pd.DataFrame, period: int = 5) -> dict:
    """
    Check for consecutive same-color candles
    Strong momentum = trend continuation signal
    """
    try:
        recent = df.tail(period)
        bulls  = sum(1 for _, c in recent.iterrows() if c["close"] > c["open"])
        bears  = sum(1 for _, c in recent.iterrows() if c["close"] < c["open"])

        if bulls == period:
            return {"direction": "BULLISH", "strength": "STRONG", "count": bulls}
        elif bears == period:
            return {"direction": "BEARISH", "strength": "STRONG", "count": bears}
        elif bulls >= period - 1:
            return {"direction": "BULLISH", "strength": "MODERATE", "count": bulls}
        elif bears >= period - 1:
            return {"direction": "BEARISH", "strength": "MODERATE", "count": bears}
        else:
            return {"direction": "MIXED", "strength": "WEAK", "count": 0}

    except Exception as e:
        logger.error(f"❌ Momentum analysis error: {e}")
        return {"direction": "MIXED", "strength": "WEAK", "count": 0}


# ─────────────────────────────────────────────────
# PRICE SPEED ANALYSIS
# ─────────────────────────────────────────────────

def analyze_price_speed(df: pd.DataFrame, period: int = 10) -> dict:
    """
    How fast is price moving?
    Too fast = dangerous
    Too slow = no opportunity
    """
    try:
        recent  = df.tail(period)
        changes = recent["close"].pct_change().abs()
        avg_spd = float(changes.mean())
        max_spd = float(changes.max())

        if avg_spd < 0.0001:
            speed = "VERY_SLOW"
        elif avg_spd < 0.0003:
            speed = "SLOW"
        elif avg_spd < 0.0008:
            speed = "NORMAL"
        elif avg_spd < 0.0015:
            speed = "FAST"
        else:
            speed = "VERY_FAST"

        return {
            "speed":     speed,
            "avg_move":  round(avg_spd, 6),
            "max_move":  round(max_spd, 6),
        }

    except Exception as e:
        logger.error(f"❌ Price speed error: {e}")
        return {"speed": "NORMAL", "avg_move": 0, "max_move": 0}


# ─────────────────────────────────────────────────
# BOLLINGER BAND WIDTH (Squeeze Detection)
# ─────────────────────────────────────────────────

def detect_squeeze(df: pd.DataFrame, period: int = 20) -> dict:
    """
    Bollinger Band squeeze = low volatility incoming explosion
    Wide bands = high volatility
    """
    try:
        sma   = df["close"].rolling(window=period).mean()
        std   = df["close"].rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = ((upper - lower) / sma * 100).iloc[-1]

        if width < 0.3:
            squeeze = "TIGHT_SQUEEZE"    # Very low volatility
        elif width < 0.8:
            squeeze = "SQUEEZE"          # Low volatility
        elif width < 2.0:
            squeeze = "NORMAL"           # Good to trade
        elif width < 4.0:
            squeeze = "EXPANDING"        # Increasing volatility
        else:
            squeeze = "WIDE"             # High volatility skip

        return {
            "state": squeeze,
            "width": round(float(width), 4),
        }

    except Exception as e:
        logger.error(f"❌ Squeeze detection error: {e}")
        return {"state": "NORMAL", "width": 0}


# ─────────────────────────────────────────────────
# MASTER VOLATILITY CHECK
# ─────────────────────────────────────────────────

def check_volatility(df: pd.DataFrame, pair: str = "") -> dict:
    """
    Master volatility check — run before every trade

    Returns:
    {
        "level":      "MEDIUM",
        "tradeable":  True,
        "atr":        0.0008,
        "action":     "TRADE",
        "reason":     "Volatility is perfect for trading",
        "details":    {...}
    }
    """
    try:
        if len(df) < 20:
            return {
                "level":     "UNKNOWN",
                "tradeable": False,
                "action":    "SKIP",
                "reason":    "Not enough data",
            }

        # Calculate all volatility measures
        atr      = calculate_atr(df)
        wicks    = analyze_wicks(df)
        momentum = analyze_momentum(df)
        speed    = analyze_price_speed(df)
        squeeze  = detect_squeeze(df)

        # ── Determine volatility level ────────────
        if atr >= VOLATILITY_LEVELS["extreme"]:
            level     = "EXTREME"
            tradeable = False
            action    = "SHUTDOWN"
            reason    = "🚨 EXTREME volatility! Emergency shutdown!"

        elif atr >= VOLATILITY_LEVELS["high"]:
            level     = "HIGH"
            tradeable = False
            action    = "SKIP"
            reason    = "Volatility too high — unpredictable market"

        elif atr <= VOLATILITY_LEVELS["low"]:
            level     = "LOW"
            tradeable = False
            action    = "SKIP"
            reason    = "Volatility too low — no market movement"

        else:
            level     = "MEDIUM"
            tradeable = True
            action    = "TRADE"
            reason    = "✅ Volatility is perfect for trading"

        # ── Override checks ───────────────────────
        # Skip on tight squeeze
        if squeeze["state"] in ["TIGHT_SQUEEZE", "SQUEEZE"] and tradeable:
            tradeable = False
            action    = "SKIP"
            reason    = "Bollinger squeeze — waiting for breakout"

        # Skip on indecision candles
        if wicks["type"] == "INDECISION" and tradeable:
            tradeable = False
            action    = "SKIP"
            reason    = "Indecision candle — no clear direction"

        # Skip on very fast price movement
        if speed["speed"] == "VERY_FAST" and tradeable:
            tradeable = False
            action    = "SKIP"
            reason    = "Price moving too fast — high risk"

        result = {
            "level":     level,
            "tradeable": tradeable,
            "atr":       round(atr, 6),
            "action":    action,
            "reason":    reason,
            "details": {
                "wicks":    wicks,
                "momentum": momentum,
                "speed":    speed,
                "squeeze":  squeeze,
            }
        }

        # Log result
        emoji = "✅" if tradeable else "⏸️"
        logger.info(f"{emoji} {pair} Volatility: {level} | ATR: {atr:.6f} | {action}")

        return result

    except Exception as e:
        logger.error(f"❌ Volatility check error: {e}")
        return {
            "level":     "UNKNOWN",
            "tradeable": False,
            "action":    "SKIP",
            "reason":    str(e),
        }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Volatility Thermometer Test")
    print("─" * 45)

    import random
    price = 1.1000
    candles = []
    for i in range(50):
        change = random.uniform(-0.0008, 0.0008)
        open_  = price
        close  = price + change
        high   = max(open_, close) + random.uniform(0, 0.0003)
        low    = min(open_, close) - random.uniform(0, 0.0003)
        candles.append({
            "open": open_, "high": high,
            "low": low,    "close": close,
            "volume": random.randint(100, 500)
        })
        price = close

    df     = pd.DataFrame(candles)
    result = check_volatility(df, "EURUSD-OTC")

    print(f"\nLevel:     {result['level']}")
    print(f"Tradeable: {result['tradeable']}")
    print(f"Action:    {result['action']}")
    print(f"Reason:    {result['reason']}")
    print(f"ATR:       {result['atr']}")
    print(f"\nDetails:")
    print(f"  Wicks:    {result['details']['wicks']}")
    print(f"  Momentum: {result['details']['momentum']}")
    print(f"  Speed:    {result['details']['speed']}")
    print(f"  Squeeze:  {result['details']['squeeze']}")