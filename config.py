# ⚡ APEX ORACLE — AO-2.0
# Central Configuration — REBUILT
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ─────────────────────────────────────────────────
# IDENTITY
# ─────────────────────────────────────────────────
BOT_NAME = "APEX ORACLE"
VERSION  = "AO-2.0"
SYMBOL   = "⚡"
MOTTO    = "We Don't Predict. We Know."

# ─────────────────────────────────────────────────
# DERIV CREDENTIALS
# ─────────────────────────────────────────────────
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")
TRADE_MODE      = os.getenv("TRADING_MODE", "PRACTICE")

# ─────────────────────────────────────────────────
# GROQ AI — DISABLED in AO-2.0
# Kept in env for potential future use
# ─────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL      = "llama3-70b-8192"
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
# TRADING PAIRS — AO-2.0 STRICT MODE
# V50, V75, V100 REMOVED — too noisy
# V25 and V10 ONLY — most controlled oscillation
# ─────────────────────────────────────────────────
SYNTHETIC_PAIRS = [
    "V25",    # Primary — most reliable mean reversion
    "V10",    # Primary — most controlled oscillation
]

MAX_ACTIVE_PAIRS = 1           # Only 1 trade at a time
PRIMARY_PAIRS    = ["V25", "V10"]
SECONDARY_PAIRS  = []          # Disabled
V75_MIN_SCORE    = 999         # Effectively disabled

# ─────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":   1,
    "primary": 5,
}

# ─────────────────────────────────────────────────
# EXPIRY — AO-2.0 STRICT MODE
# 3-min default: filters out 1-min noise
# 5-min high confidence: lets winners run longer
# ─────────────────────────────────────────────────
EXPIRY_DEFAULT   = 3    # minutes — was 1
EXPIRY_HIGH_CONF = 5    # minutes — was 3 (score >= 10)
EXPIRY_SECONDS   = 180  # updated for backward compat

# ─────────────────────────────────────────────────
# SIGNAL ENGINE — AO-2.0 STRICT SCORING SYSTEM
# Only "screaming" signals pass now
# ─────────────────────────────────────────────────
MIN_SCORE        = 8         # sweet spot — blocks weak 7/12, allows strong signals
RSI_PERIOD       = 14
RSI_EXTREME_HIGH = 78        # was 75 — stricter overbought
RSI_STRONG_HIGH  = 72
RSI_EXTREME_LOW  = 22        # was 25 — stricter oversold
RSI_STRONG_LOW   = 28
BB_PERIOD        = 20
BB_STD           = 2.0
ROC_PERIOD       = 5
PAIR_COOLDOWN_SECS = 180     # was 120 — 3 min cooldown between trades

# Backward compat
RSI_OVERBOUGHT      = 70
RSI_OVERSOLD        = 30
RSI_NEUTRAL_LOW     = 45
RSI_NEUTRAL_HIGH    = 55
MACD_FAST           = 12
MACD_SLOW           = 26
MACD_SIGNAL         = 9
EMA_FAST            = 9
EMA_SLOW            = 21
ATR_PERIOD          = 14
MIN_CANDLES         = 30

# Confidence thresholds — updated for MIN_SCORE = 10
CONFIDENCE = {
    "full_trade": 83,   # score 10/12 = 83%
    "half_trade": 67,   # score 8/12 = 67%
    "skip":       0,
    "minimum":    67,   # score 8/12 minimum
}

# ─────────────────────────────────────────────────
# RISK MANAGEMENT — AO-2.0 STRICT MODE
# ─────────────────────────────────────────────────
STAKE_PERCENT          = float(os.getenv("STAKE_PERCENT", 1.0))      # was 1.5
MAX_DAILY_TRADES       = int(os.getenv("MAX_DAILY_TRADES", 6))        # was 10
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 2))  # was 3
DAILY_LOSS_LIMIT       = float(os.getenv("DAILY_LOSS_LIMIT", 4.0))    # was 5.0
DAILY_PROFIT_TARGET    = float(os.getenv("DAILY_PROFIT_TARGET", 1000.0))# was 30 — realistic
WEEKLY_LOSS_LIMIT      = 10.0
CONSECUTIVE_LOSS_PAUSE = 3600   # was 1800 — 1hr pause after 2 losses
WIN_STREAK_REDUCE      = 5
KELLY_SAFETY_FACTOR    = 0.25
MAX_CONCURRENT_TRADES  = 1      # was 2 — no overlapping trades

# ─────────────────────────────────────────────────
# REMOVED IN AO-2.0 — kept to avoid import errors
# ─────────────────────────────────────────────────
GROQ_MIN_CONFIDENCE     = 83
MIN_INDICATORS_AGREE    = 4     # was 3 — stricter
MIN_TIMEFRAMES_AGREE    = 1
VOLATILITY_LEVELS       = {"low": 1.0, "medium": 5.0, "high": 20.0, "extreme": 50.0}
WICK_BODY_RATIO_MIN     = 1.5
MAX_PRICE_DIFFERENCE    = 0.0005
SIGNAL_VALIDITY_CANDLES = 2
SIGNAL_VALIDITY_SECONDS = 600

# ─────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────
PORT              = int(os.getenv("PORT", 10000))
TIMEZONE          = os.getenv("TIMEZONE", "Africa/Lagos")
TRADING_SESSIONS  = {}
NEWS_BLOCK_MINUTES = 0

# ─────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────
LOG_LEVEL     = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE      = "logs/apex_oracle.log"
LOG_ROTATION  = "1 day"
LOG_RETENTION = "7 days"

# ─────────────────────────────────────────────────
# GOOGLE DRIVE BACKUP
# ─────────────────────────────────────────────────
GDRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# ─────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────
def validate_config():
    required = {
        "DERIV_API_TOKEN":    DERIV_API_TOKEN,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
        "TELEGRAM_CHAT_ID":   TELEGRAM_CHAT_ID,
        "SUPABASE_URL":       SUPABASE_URL,
        "SUPABASE_KEY":       SUPABASE_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        for key in missing:
            logger.error(f"❌ Missing: {key}")
        raise EnvironmentError(f"Cannot start. Missing: {', '.join(missing)}")
    logger.success("✅ All environment variables loaded")
    return True


if __name__ == "__main__":
    print(f"\n{SYMBOL} {BOT_NAME} v{VERSION}")
    print(f"'{MOTTO}'")
    print(f"\nMode:             {TRADE_MODE}")
    print(f"Pairs:            {SYNTHETIC_PAIRS}")
    print(f"Min Score:        {MIN_SCORE}/12 to trade")
    print(f"Max Trades:       {MAX_DAILY_TRADES}/day")
    print(f"Daily Target:     ${DAILY_PROFIT_TARGET}")
    print(f"Daily Loss Limit: {DAILY_LOSS_LIMIT}%")
    print(f"Stake:            {STAKE_PERCENT}% per trade")
    print(f"Expiry:           {EXPIRY_DEFAULT}min default, {EXPIRY_HIGH_CONF}min high-conf")
    print(f"Consec. Loss Pause: {CONSECUTIVE_LOSS_PAUSE // 60} minutes")