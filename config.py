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
# DERIV CREDENTIALS
# ─────────────────────────────────────────────────
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")
TRADE_MODE      = os.getenv("TRADING_MODE", "PRACTICE")

# ─────────────────────────────────────────────────
# GROQ AI (FREE)
# ─────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = "llama3-70b-8192"
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
# TRADING PAIRS — SYNTHETIC ONLY
# ─────────────────────────────────────────────────
SYNTHETIC_PAIRS = [
    "V75",
    "V50",
    "V25",
    "V10",
    "V100",
]

# Max pairs running simultaneously
MAX_ACTIVE_PAIRS = 2

# ─────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":    1,
    "primary":  5,
    "confirm":  15,
    "bias":     60,
}

EXPIRY_SECONDS = 300
SIGNAL_VALIDITY_CANDLES = 2
SIGNAL_VALIDITY_SECONDS = 600

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

MIN_CANDLES     = 100

# ─────────────────────────────────────────────────
# SIGNAL CONFLUENCE SCORING
# ─────────────────────────────────────────────────
# Minimum indicators that must agree (out of 5)
MIN_INDICATORS_AGREE    = 3  # 🔧 Updated from 4 to 3

# Minimum timeframes that must agree (out of 4)
MIN_TIMEFRAMES_AGREE    = 3

CONFIDENCE = {
    "full_trade":   95,
    "half_trade":   75,
    "skip":         50,
    "minimum":      int(os.getenv("MIN_CONFIDENCE", 75)),
}

GROQ_MIN_CONFIDENCE = 80

# ─────────────────────────────────────────────────
# VOLATILITY THERMOMETER — SYNTHETIC
# ─────────────────────────────────────────────────
VOLATILITY_LEVELS = {
    "low":      1.0,    # 🔧 Increased from 0.10
    "medium":   5.0,    # 🔧 Increased from 0.50
    "high":     20.0,   # 🔧 Increased from 1.50
    "extreme":  50.0,   # 🔧 Increased from 3.00
}

WICK_BODY_RATIO_MIN = 1.5

# ─────────────────────────────────────────────────
# RISK MANAGEMENT
# ─────────────────────────────────────────────────
STAKE_PERCENT           = float(os.getenv("STAKE_PERCENT", 1.5))
MAX_DAILY_TRADES        = int(os.getenv("MAX_DAILY_TRADES", 15))
MAX_CONSECUTIVE_LOSSES  = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
DAILY_LOSS_LIMIT        = float(os.getenv("DAILY_LOSS_LIMIT", 5))
WEEKLY_LOSS_LIMIT       = 10.0
CONSECUTIVE_LOSS_PAUSE  = 3600
WIN_STREAK_REDUCE       = 5
KELLY_SAFETY_FACTOR     = 0.25

# ─────────────────────────────────────────────────
# PRICE MANIPULATION GUARD
# ─────────────────────────────────────────────────
MAX_PRICE_DIFFERENCE    = 0.0005

# ─────────────────────────────────────────────────
# SESSION TIMES — REMOVED (SYNTHETIC 24/7)
# ─────────────────────────────────────────────────
TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")
TRADING_SESSIONS = {}
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
# VALIDATION
# ─────────────────────────────────────────────────
def validate_config():
    """Check all required environment variables are set"""
    required = {
        "DERIV_API_TOKEN":    DERIV_API_TOKEN,
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
    print(f"\n{SYMBOL} {BOT_NAME} v{VERSION}")
    print(f"'{MOTTO}'")
    print(f"\nTrading Mode:  {TRADE_MODE}")
    print(f"Primary Pairs: {SYNTHETIC_PAIRS}")
    print(f"Timeframes:    {TIMEFRAMES}")
    print(f"Stake:         {STAKE_PERCENT}% per trade")
    print(f"Max Trades:    {MAX_DAILY_TRADES}/day")
    print(f"Min Confidence:{CONFIDENCE['minimum']}/100")