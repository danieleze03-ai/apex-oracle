# ⚡ APEX ORACLE — AO-1.0
# Signal Engine — Technical Indicators
# RSI, MACD, Bollinger Bands, EMA, Stochastic RSI
# Built manually for Python 3.11 compatibility
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

from loguru import logger
from loguru import logger


# ─────────────────────────────────────────────────
# DATA PREPARATION
# ─────────────────────────────────────────────────

def prepare_dataframe(candles: list):
    """Convert raw candle list to DataFrame"""
    try:
        import pandas as pd
        df = pd.DataFrame(candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").reset_index(drop=True)
        df[["open","high","low","close"]] = \
            df[["open","high","low","close"]].astype(float)
        return df
    except Exception as e:
        logger.error(f"❌ Failed to prepare dataframe: {e}")
        import pandas as pd
        return pd.DataFrame()


# ─────────────────────────────────────────────────
# RSI — Relative Strength Index
# ─────────────────────────────────────────────────

def calculate_rsi(df, period: int = 14):
    """
    Calculate RSI
    < 35 = Oversold  → CALL signal
    > 65 = Overbought → PUT signal
    45-55 = Neutral  → NEUTRAL
    """
    try:
        import pandas as pd
        delta    = df["close"].diff()
        gain     = delta.where(delta > 0, 0.0)
        loss     = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs       = avg_gain / avg_loss
        rsi      = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.error(f"❌ RSI calculation error: {e}")
        import pandas as pd
        return pd.Series()


def get_rsi_signal(rsi_value: float) -> str:
    """Get trading signal from RSI value"""
    if rsi_value < 35:
        return "CALL"
    elif rsi_value > 65:
        return "PUT"
    elif rsi_value < 45:
        return "CALL"    # Leaning oversold
    elif rsi_value > 55:
        return "PUT"     # Leaning overbought
    else:
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# MACD — Moving Average Convergence Divergence
# ─────────────────────────────────────────────────

def calculate_macd(df, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    Calculate MACD
    MACD crosses above signal → CALL
    MACD crosses below signal → PUT
    """
    try:
        ema_fast    = df["close"].ewm(span=fast,   adjust=False).mean()
        ema_slow    = df["close"].ewm(span=slow,   adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line
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

        macd_curr = macd.iloc[-1]
        macd_prev = macd.iloc[-2]
        sig_curr  = signal.iloc[-1]
        sig_prev  = signal.iloc[-2]
        hist_curr = hist.iloc[-1]

        if macd_prev < sig_prev and macd_curr > sig_curr:
            return "CALL"
        elif macd_prev > sig_prev and macd_curr < sig_curr:
            return "PUT"
        elif macd_curr > sig_curr and hist_curr > 0:
            return "CALL"
        elif macd_curr < sig_curr and hist_curr < 0:
            return "PUT"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ MACD signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# BOLLINGER BANDS
# ─────────────────────────────────────────────────

def calculate_bollinger_bands(df, period: int = 20, std: float = 2.0) -> dict:
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


def get_bb_signal(bb_data: dict, df) -> str:
    """Get trading signal from Bollinger Bands"""
    try:
        close = df["close"].iloc[-1]
        upper = bb_data["upper"].iloc[-1]
        lower = bb_data["lower"].iloc[-1]
        width = bb_data["width"].iloc[-1]

        if width < 0.5:
            return "SQUEEZE"
        if close <= lower:
            return "CALL"
        elif close >= upper:
            return "PUT"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ BB signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# EMA CROSS — Exponential Moving Average
# ─────────────────────────────────────────────────

def calculate_ema(df, fast: int = 9, slow: int = 21) -> dict:
    """
    Calculate EMA Cross
    Fast EMA crosses above slow → CALL
    Fast EMA crosses below slow → PUT
    """
    try:
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        return {"fast": ema_fast, "slow": ema_slow}
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

        if fast_prev < slow_prev and fast_curr > slow_curr:
            return "CALL"
        elif fast_prev > slow_prev and fast_curr < slow_curr:
            return "PUT"
        elif fast_curr > slow_curr:
            return "CALL"
        elif fast_curr < slow_curr:
            return "PUT"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ EMA signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# STOCHASTIC RSI
# ─────────────────────────────────────────────────

def calculate_stoch_rsi(
    df,
    rsi_period:   int = 14,
    stoch_period: int = 14,
    smooth_k:     int = 3,
    smooth_d:     int = 3,
) -> dict:
    """
    Calculate Stochastic RSI
    %K < 20 = Oversold  → CALL
    %K > 80 = Overbought → PUT
    """
    try:
        delta    = df["close"].diff()
        gain     = delta.where(delta > 0, 0.0)
        loss     = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        avg_loss = loss.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        rs       = avg_gain / avg_loss
        rsi      = 100 - (100 / (1 + rs))

        rsi_min  = rsi.rolling(window=stoch_period).min()
        rsi_max  = rsi.rolling(window=stoch_period).max()
        stoch    = (rsi - rsi_min) / (rsi_max - rsi_min) * 100

        k_line   = stoch.rolling(window=smooth_k).mean()
        d_line   = k_line.rolling(window=smooth_d).mean()

        return {"k": k_line, "d": d_line}
    except Exception as e:
        logger.error(f"❌ Stoch RSI calculation error: {e}")
        return {}


def get_stoch_rsi_signal(stoch_data: dict) -> str:
    try:
        k_curr = stoch_data["k"].iloc[-1]
        k_prev = stoch_data["k"].iloc[-2]
        d_curr = stoch_data["d"].iloc[-1]
        d_prev = stoch_data["d"].iloc[-2]

        if k_curr < 20 and k_prev < d_prev and k_curr > d_curr:
            return "CALL"
        elif k_curr > 80 and k_prev > d_prev and k_curr < d_curr:
            return "PUT"
        elif k_curr < 20:
            return "CALL"
        elif k_curr > 80:
            return "PUT"
        else:
            return "NEUTRAL"
    except Exception as e:
        logger.error(f"❌ Stoch RSI signal error: {e}")
        return "NEUTRAL"


# ─────────────────────────────────────────────────
# ATR — Average True Range
# ─────────────────────────────────────────────────

def calculate_atr(df, period: int = 14):
    """Calculate ATR for volatility measurement"""
    try:
        import pandas as pd
        high       = df["high"]
        low        = df["low"]
        close      = df["close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()
        return atr
    except Exception as e:
        logger.error(f"❌ ATR calculation error: {e}")
        import pandas as pd
        return pd.Series()


# ─────────────────────────────────────────────────
# MASTER SIGNAL GENERATOR
# ─────────────────────────────────────────────────

def generate_signal(candles: list, pair: str = "") -> dict:
    """
    Generate complete trading signal from candle data
    5 Indicators — minimum 3/5 must agree to trade.
    """
    try:
        if len(candles) < 50:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "reason":     "Not enough candles",
            }

        df = prepare_dataframe(candles)
        if df.empty:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "reason":     "Empty dataframe",
            }

        rsi       = calculate_rsi(df)
        macd      = calculate_macd(df)
        bb        = calculate_bollinger_bands(df)
        ema       = calculate_ema(df)
        stoch_rsi = calculate_stoch_rsi(df)

        rsi_val   = rsi.iloc[-1] if not rsi.empty else 50

        rsi_sig   = get_rsi_signal(rsi_val)
        macd_sig  = get_macd_signal(macd)
        bb_sig    = get_bb_signal(bb, df)
        ema_sig   = get_ema_signal(ema)
        stoch_sig = get_stoch_rsi_signal(stoch_rsi)

        signals = [rsi_sig, macd_sig, bb_sig, ema_sig, stoch_sig]

        logger.debug(
            f"📊 {pair} Signals: "
            f"RSI={rsi_sig} MACD={macd_sig} "
            f"BB={bb_sig} EMA={ema_sig} STOCHRSI={stoch_sig}"
        )

        calls = signals.count("CALL")
        puts  = signals.count("PUT")

        if calls >= 4:
            direction  = "CALL"
            agreement  = calls
            confidence = 90
        elif calls == 3:
            direction  = "CALL"
            agreement  = calls
            confidence = 75
        elif puts >= 4:
            direction  = "PUT"
            agreement  = puts
            confidence = 90
        elif puts == 3:
            direction  = "PUT"
            agreement  = puts
            confidence = 75
        else:
            direction  = "SKIP"
            agreement  = 0
            confidence = 0

        if bb_sig == "SQUEEZE":
            direction  = "SKIP"
            confidence = 0

        result = {
            "direction":  direction,
            "confidence": min(confidence, 95),
            "agreement":  agreement,
            "indicators": {
                "rsi":      {"value": round(rsi_val, 2), "signal": rsi_sig},
                "macd":     {"signal": macd_sig},
                "bb":       {"signal": bb_sig},
                "ema":      {"signal": ema_sig},
                "stochrsi": {"signal": stoch_sig},
            },
            "reason": f"{agreement}/5 indicators agree {direction}",
        }

        logger.info(
            f"⚡ {pair} Signal: {direction} | "
            f"Confidence: {confidence}% | {agreement}/5 agree"
        )
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
        })
        price = close

    signal = generate_signal(fake_candles, "V75")
    print(f"\nSignal:     {signal['direction']}")
    print(f"Confidence: {signal['confidence']}%")
    print(f"Agreement:  {signal['agreement']}/5")
    print(f"Reason:     {signal['reason']}")
    print(f"\nIndicators:")
    for name, data in signal["indicators"].items():
        print(f"  {name.upper()}: {data}")
