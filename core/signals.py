# ⚡ APEX ORACLE — AO-1.0
# Signal Engine — Technical Indicators
# RSI, MACD, Bollinger Bands, EMA, Volume
# Built manually for Python 3.14 compatibility
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import numpy as np
import pandas as pd
from loguru import logger

# ─────────────────────────────────────────────────
# DATA PREPARATION
# ─────────────────────────────────────────────────

def prepare_dataframe(candles: list) -> pd.DataFrame:
    """Convert raw candle list to DataFrame"""
    try:
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").reset_index(drop=True)
        df[["open","high","low","close","volume"]] = \
            df[["open","high","low","close","volume"]].astype(float)
        return df
    except Exception as e:
        logger.error(f"❌ Failed to prepare dataframe: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────
# RSI — Relative Strength Index
# ─────────────────────────────────────────────────

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate RSI
    < 30 = Oversold  → CALL signal
    > 70 = Overbought → PUT signal
    45-55 = Neutral  → SKIP
    """
    try:
        delta  = df["close"].diff()
        gain   = delta.where(delta > 0, 0.0)
        loss   = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.error(f"❌ RSI calculation error: {e}")
        return pd.Series()


def get_rsi_signal(rsi_value: float) -> str:
    """Get trading signal from RSI value"""
    if rsi_value < 30:
        return "CALL"
    elif rsi_value > 70:
        return "PUT"
    elif 45 <= rsi_value <= 55:
        return "NEUTRAL"
    else:
        return "WEAK"


# ─────────────────────────────────────────────────
# MACD — Moving Average Convergence Divergence
# ─────────────────────────────────────────────────

def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> dict:
    """
    Calculate MACD
    MACD crosses above signal → CALL
    MACD crosses below signal → PUT
    """
    try:
        ema_fast   = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow   = df["close"].ewm(span=slow, adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line= macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line
        return {
            "macd":      macd_line,
            "signal":    signal_line,
            "histogram": histogram,
        }
    except Exception as e:
        logger.error(f"❌ MACD calculation error: {e}")
        return {}


def get_macd_signal(macd_data: dict) -> str:
    """Get trading signal from MACD"""
    try:
        macd   = macd_data["macd"]
        signal = macd_data["signal"]
        hist   = macd_data["histogram"]

        # Current and previous values
        macd_curr = macd.iloc[-1]
        macd_prev = macd.iloc[-2]
        sig_curr  = signal.iloc[-1]
        sig_prev  = signal.iloc[-2]
        hist_curr = hist.iloc[-1]

        # Crossover detection
        if macd_prev < sig_prev and macd_curr > sig_curr:
            return "CALL"  # MACD crossed above signal
        elif macd_prev > sig_prev and macd_curr < sig_curr:
            return "PUT"   # MACD crossed below signal
        elif macd_curr > sig_curr and hist_curr > 0:
            return "CALL"  # MACD above signal (bullish)
        elif macd_curr < sig_curr and hist_curr < 0:
            return "PUT"   # MACD below signal (bearish)
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ MACD signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# BOLLINGER BANDS
# ─────────────────────────────────────────────────

def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std: float = 2.0
) -> dict:
    """
    Calculate Bollinger Bands
    Price touches lower band → CALL
    Price touches upper band → PUT
    Squeeze = low volatility → SKIP
    """
    try:
        sma   = df["close"].rolling(window=period).mean()
        stdev = df["close"].rolling(window=period).std()
        upper = sma + (stdev * std)
        lower = sma - (stdev * std)
        width = (upper - lower) / sma * 100
        return {
            "upper":  upper,
            "middle": sma,
            "lower":  lower,
            "width":  width,
        }
    except Exception as e:
        logger.error(f"❌ Bollinger Bands error: {e}")
        return {}


def get_bb_signal(bb_data: dict, df: pd.DataFrame) -> str:
    """Get trading signal from Bollinger Bands"""
    try:
        close = df["close"].iloc[-1]
        upper = bb_data["upper"].iloc[-1]
        lower = bb_data["lower"].iloc[-1]
        width = bb_data["width"].iloc[-1]

        # Squeeze = skip (low volatility)
        if width < 0.5:
            return "SQUEEZE"

        # Price at bands
        if close <= lower:
            return "CALL"   # Oversold at lower band
        elif close >= upper:
            return "PUT"    # Overbought at upper band
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ BB signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# EMA CROSS — Exponential Moving Average
# ─────────────────────────────────────────────────

def calculate_ema(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> dict:
    """
    Calculate EMA Cross
    Fast EMA crosses above slow → CALL
    Fast EMA crosses below slow → PUT
    """
    try:
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        return {
            "fast": ema_fast,
            "slow": ema_slow,
        }
    except Exception as e:
        logger.error(f"❌ EMA calculation error: {e}")
        return {}


def get_ema_signal(ema_data: dict) -> str:
    """Get trading signal from EMA Cross"""
    try:
        fast_curr = ema_data["fast"].iloc[-1]
        fast_prev = ema_data["fast"].iloc[-2]
        slow_curr = ema_data["slow"].iloc[-1]
        slow_prev = ema_data["slow"].iloc[-2]

        # Crossover
        if fast_prev < slow_prev and fast_curr > slow_curr:
            return "CALL"   # Golden cross
        elif fast_prev > slow_prev and fast_curr < slow_curr:
            return "PUT"    # Death cross
        elif fast_curr > slow_curr:
            return "CALL"   # Fast above slow = bullish
        elif fast_curr < slow_curr:
            return "PUT"    # Fast below slow = bearish
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ EMA signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# VOLUME ANALYSIS
# ─────────────────────────────────────────────────

def get_volume_signal(df: pd.DataFrame, period: int = 20) -> str:
    """
    Analyze volume for confirmation
    Volume spike + direction = confirmation
    Low volume = skip
    """
    try:
        avg_volume  = df["volume"].rolling(window=period).mean().iloc[-1]
        curr_volume = df["volume"].iloc[-1]
        curr_close  = df["close"].iloc[-1]
        prev_close  = df["close"].iloc[-2]

        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1

        # Low volume = weak signal
        if volume_ratio < 0.5:
            return "LOW"

        # High volume spike
        if volume_ratio > 1.5:
            if curr_close > prev_close:
                return "CALL"   # Volume spike + up = bullish
            else:
                return "PUT"    # Volume spike + down = bearish

        return "NEUTRAL"

    except Exception as e:
        logger.error(f"❌ Volume analysis error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# ATR — Average True Range (Volatility)
# ─────────────────────────────────────────────────

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR for volatility measurement"""
    try:
        high  = df["high"]
        low   = df["low"]
        close = df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return atr
    except Exception as e:
        logger.error(f"❌ ATR calculation error: {e}")
        return pd.Series()


# ─────────────────────────────────────────────────
# MASTER SIGNAL GENERATOR
# ─────────────────────────────────────────────────

def generate_signal(candles: list, pair: str = "") -> dict:
    """
    Generate complete trading signal from candle data

    Returns:
    {
        "direction":    "CALL" / "PUT" / "SKIP",
        "confidence":   85.0,
        "indicators":   {...},
        "agreement":    4,
        "reason":       "4/5 indicators agree CALL"
    }
    """
    try:
        if len(candles) < 50:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "reason":     "Not enough candles"
            }

        df = prepare_dataframe(candles)
        if df.empty:
            return {"direction": "SKIP", "confidence": 0, "reason": "Empty dataframe"}

        # ── Calculate all indicators ──────────────
        rsi      = calculate_rsi(df)
        macd     = calculate_macd(df)
        bb       = calculate_bollinger_bands(df)
        ema      = calculate_ema(df)

        rsi_val  = rsi.iloc[-1] if not rsi.empty else 50

        # ── Get signals ───────────────────────────
        rsi_sig  = get_rsi_signal(rsi_val)
        macd_sig = get_macd_signal(macd)
        bb_sig   = get_bb_signal(bb, df)
        ema_sig  = get_ema_signal(ema)
        vol_sig  = get_volume_signal(df)

        signals = [rsi_sig, macd_sig, bb_sig, ema_sig, vol_sig]
        logger.debug(f"📊 {pair} Signals: RSI={rsi_sig} MACD={macd_sig} BB={bb_sig} EMA={ema_sig} VOL={vol_sig}")

        # ── Count agreements ──────────────────────
        calls = signals.count("CALL")
        puts  = signals.count("PUT")

        # ── Determine direction ───────────────────
        if calls >= 4:
            direction  = "CALL"
            agreement  = calls
            confidence = 75 + (calls * 5)
        elif puts >= 4:
            direction  = "PUT"
            agreement  = puts
            confidence = 75 + (puts * 5)
        elif calls == 3:
            direction  = "CALL"
            agreement  = calls
            confidence = 65
        elif puts == 3:
            direction  = "PUT"
            agreement  = puts
            confidence = 65
        else:
            direction  = "SKIP"
            agreement  = 0
            confidence = 0

        # Skip squeeze
        if bb_sig == "SQUEEZE":
            direction  = "SKIP"
            confidence = 0

        # Skip low volume
        if vol_sig == "LOW" and confidence > 0:
            confidence -= 15

        result = {
            "direction":  direction,
            "confidence": min(confidence, 95),
            "agreement":  agreement,
            "indicators": {
                "rsi":     {"value": round(rsi_val, 2), "signal": rsi_sig},
                "macd":    {"signal": macd_sig},
                "bb":      {"signal": bb_sig},
                "ema":     {"signal": ema_sig},
                "volume":  {"signal": vol_sig},
            },
            "reason": f"{agreement}/5 indicators agree {direction}",
        }

        logger.info(f"⚡ {pair} Signal: {direction} | Confidence: {confidence}% | {agreement}/5 agree")
        return result

    except Exception as e:
        logger.error(f"❌ Signal generation error: {e}")
        return {"direction": "SKIP", "confidence": 0, "reason": str(e)}


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Signal Engine Test")
    print("─" * 45)

    # Generate fake candles for testing
    import random
    fake_candles = []
    price = 1.1000
    for i in range(100):
        change = random.uniform(-0.0010, 0.0010)
        open_  = price
        close  = price + change
        high   = max(open_, close) + random.uniform(0, 0.0005)
        low    = min(open_, close) - random.uniform(0, 0.0005)
        fake_candles.append({
            "timestamp": i * 300,
            "open":      round(open_, 5),
            "high":      round(high,  5),
            "low":       round(low,   5),
            "close":     round(close, 5),
            "volume":    random.randint(100, 1000),
        })
        price = close

    signal = generate_signal(fake_candles, "EURUSD-OTC")
    print(f"\nSignal:     {signal['direction']}")
    print(f"Confidence: {signal['confidence']}%")
    print(f"Agreement:  {signal['agreement']}/5")
    print(f"Reason:     {signal['reason']}")
    print(f"\nIndicators:")
    for name, data in signal["indicators"].items():
        print(f"  {name.upper()}: {data}")