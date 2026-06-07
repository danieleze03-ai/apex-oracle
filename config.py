# ⚡ APEX ORACLE — AO-1.0
# Central Configuration File
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file (local dev)
load_dotenv()

# ─────────────────────────────────────────────────
# IDENTITY
# ─────────────────────────────────────────────────
BOT_NAME    = "APEX ORACLE"
VERSION     = "AO-1.0"
SYMBOL      = "⚡"
MOTTO       = "We Don't Predict. We Know."

# ─────────────────────────────────────────────────
# IQ OPTION CREDENTIALS
# ─────────────────────────────────────────────────
IQ_EMAIL    = os.getenv("IQ_OPTION_EMAIL")
IQ_PASSWORD = os.getenv("IQ_OPTION_PASSWORD")
TRADE_MODE  = os.getenv("TRADING_MODE", "PRACTICE")  # PRACTICE or REAL

# ─────────────────────────────────────────────────
# GROQ AI (FREE)
# ─────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama3-70b-8192"   # Best free model on Groq
GROQ_MAX_TOKENS = 500

# ─────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─────────────────────────────────────────────────
# SUPABASE DATABASE
# ─────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ─────────────────────────────────────────────────
# TRADING PAIRS
# ─────────────────────────────────────────────────
PRIMARY_PAIRS = [
    "EURUSD-OTC",   # Best liquid OTC pair
    "GBPUSD-OTC",   # Strong trends
]

MARKET_HOURS_PAIRS = [
    "EURUSD",       # Real market hours only
    "GBPUSD",       # Real market hours only
]

BACKUP_PAIRS = [
    "GBPJPY-OTC",
    "EURGBP-OTC",
    "USDJPY-OTC",
]

ALL_PAIRS = PRIMARY_PAIRS + MARKET_HOURS_PAIRS + BACKUP_PAIRS

# Max pairs running simultaneously
MAX_ACTIVE_PAIRS = 2

# ─────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":    1,    # 1min  - entry timing
    "primary":  5,    # 5min  - signal source (PRIMARY)
    "confirm":  15,   # 15min - trend confirmation
    "bias":     60,   # 1hr   - overall bias
}

# Expiry time in seconds
EXPIRY_SECONDS = 300   # 5 minutes

# Signal validity (how long before signal is dead)
SIGNAL_VALIDITY_CANDLES = 2        # 2 candles = 10 minutes on 5min chart
SIGNAL_VALIDITY_SECONDS = 600      # 10 minutes

# ─────────────────────────────────────────────────
# TECHNICAL INDICATORS SETTINGS
# ─────────────────────────────────────────────────
RSI_PERIOD      = 14
RSI_OVERSOLD    = 30
RSI_OVERBOUGHT  = 70
RSI_NEUTRAL_LOW = 45
RSI_NEUTRAL_HIGH= 55

MACD_FAST       = 12
MACD_SLOW       = 26
MACD_SIGNAL     = 9

BB_PERIOD       = 20
BB_STD          = 2

EMA_FAST        = 9
EMA_SLOW        = 21

ATR_PERIOD      = 14

# Minimum candles needed for indicator calculation
MIN_CANDLES     = 100

# ─────────────────────────────────────────────────
# SIGNAL CONFLUENCE SCORING
# ─────────────────────────────────────────────────
# Minimum indicators that must agree (out of 5)
MIN_INDICATORS_AGREE    = 4

# Minimum timeframes that must agree (out of 4)
MIN_TIMEFRAMES_AGREE    = 3

# Confidence thresholds
CONFIDENCE = {
    "full_trade":   95,   # 4/4 TF agree → full stake
    "half_trade":   75,   # 3/4 TF agree → half stake
    "skip":         50,   # 2/4 TF agree → skip
    "minimum":      int(os.getenv("MIN_CONFIDENCE", 75)),
}

# Groq AI minimum confidence to execute
GROQ_MIN_CONFIDENCE = 80

# ─────────────────────────────────────────────────
# VOLATILITY THERMOMETER
# ─────────────────────────────────────────────────
VOLATILITY_LEVELS = {
    "low":      0.0003,   # Below this = skip (no movement)
    "medium":   0.0015,   # Between low and high = TRADE ✅
    "high":     0.003,    # Above this = skip
    "extreme":  0.006,    # Above this = EMERGENCY SHUTDOWN
}

# Wick ratio threshold (large wick = rejection)
WICK_BODY_RATIO_MIN = 1.5   # wick > 1.5x body = rejection signal

# ─────────────────────────────────────────────────
# RISK MANAGEMENT
# ─────────────────────────────────────────────────
STAKE_PERCENT           = float(os.getenv("STAKE_PERCENT", 1.5))
MAX_DAILY_TRADES        = int(os.getenv("MAX_DAILY_TRADES", 15))
MAX_CONSECUTIVE_LOSSES  = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
DAILY_LOSS_LIMIT        = float(os.getenv("DAILY_LOSS_LIMIT", 5))
WEEKLY_LOSS_LIMIT       = 10.0     # % - bot pauses for the week
CONSECUTIVE_LOSS_PAUSE  = 3600     # Seconds (1 hour) to pause after max losses
WIN_STREAK_REDUCE       = 5        # After 5 wins, reduce stake by 20%

# Kelly Criterion safety factor
KELLY_SAFETY_FACTOR     = 0.25     # Use only 25% of full Kelly

# ─────────────────────────────────────────────────
# PRICE MANIPULATION GUARD
# ─────────────────────────────────────────────────
MAX_PRICE_DIFFERENCE    = 0.0005   # 0.5 pips max difference IQ vs Yahoo

# ─────────────────────────────────────────────────
# SESSION TIMES (WAT = UTC+1)
# ─────────────────────────────────────────────────
TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")

TRADING_SESSIONS = {
    "london_open":  {"start": "08:00", "end": "10:00"},
    "overlap":      {"start": "14:00", "end": "17:00"},   # 🔥 BEST
    "ny_close":     {"start": "19:00", "end": "21:00"},
}

# Block trading this many minutes before/after news
NEWS_BLOCK_MINUTES = 30

# ─────────────────────────────────────────────────
# SERVER (RENDER KEEP-ALIVE)
# ─────────────────────────────────────────────────
PORT = int(os.getenv("PORT", 10000))

# ─────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE    = "logs/apex_oracle.log"
LOG_ROTATION= "1 day"
LOG_RETENTION = "7 days"

# ─────────────────────────────────────────────────
# GOOGLE DRIVE BACKUP
# ─────────────────────────────────────────────────
GDRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# ─────────────────────────────────────────────────
# VALIDATION — Check all critical vars are set
# ─────────────────────────────────────────────────
def validate_config():
    """Check all required environment variables are set"""
    required = {
        "IQ_OPTION_EMAIL":    IQ_EMAIL,
        "IQ_OPTION_PASSWORD": IQ_PASSWORD,
        "GROQ_API_KEY":       GROQ_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID":   TELEGRAM_CHAT_ID,
        "SUPABASE_URL":       SUPABASE_URL,
        "SUPABASE_KEY":       SUPABASE_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        for key in missing:
            logger.error(f"❌ Missing environment variable: {key}")
        raise EnvironmentError(
            f"⚡ APEX ORACLE cannot start. Missing: {', '.join(missing)}"
        )
    logger.success("✅ All environment variables loaded successfully")
    return True


if __name__ == "__main__":
    # Quick config check
    print(f"\n{SYMBOL} {BOT_NAME} v{VERSION}")
    print(f"'{MOTTO}'")
    print(f"\nTrading Mode:  {TRADE_MODE}")
    print(f"Primary Pairs: {PRIMARY_PAIRS}")
    print(f"Timeframes:    {TIMEFRAMES}")
    print(f"Stake:         {STAKE_PERCENT}% per trade")
    print(f"Max Trades:    {MAX_DAILY_TRADES}/day")
    print(f"Min Confidence:{CONFIDENCE['minimum']}/100")
