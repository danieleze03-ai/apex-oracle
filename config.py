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
# TRADING PAIRS — AO-2.0
# V100 REMOVED — too noisy for mean reversion
# V25 and V10 are PRIMARY (most controlled oscillation)
# V50 and V75 are SECONDARY (higher threshold required)
# ─────────────────────────────────────────────────
SYNTHETIC_PAIRS = [
    "V25",    # Primary — most reliable mean reversion
    "V10",    # Primary — most controlled oscillation
    "V50",    # Secondary
    "V75",    # Secondary — only trade at score >= 9
]

# V100 is intentionally excluded — too much noise
MAX_ACTIVE_PAIRS    = 2          # Max pairs trading simultaneously
PRIMARY_PAIRS       = ["V25", "V10"]
SECONDARY_PAIRS     = ["V50", "V75"]
V75_MIN_SCORE       = 9          # V75 requires higher score (out of 12)

# ─────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":   1,
    "primary": 5,
}

# ─────────────────────────────────────────────────
# EXPIRY — AO-2.0
# 1-min expiry: quick mean reversion capture
# 3-min expiry: for high-confidence (score >= 10)
# ─────────────────────────────────────────────────
EXPIRY_DEFAULT      = 1     # minutes — default
EXPIRY_HIGH_CONF    = 3     # minutes — score >= 10
EXPIRY_SECONDS      = 60    # for backward compat

# ─────────────────────────────────────────────────
# SIGNAL ENGINE — AO-2.0 SCORING SYSTEM
# ─────────────────────────────────────────────────
MIN_SCORE           = 7          # minimum score out of 12 to trade
RSI_PERIOD          = 14
RSI_EXTREME_HIGH    = 75         # overbought — FALL signal
RSI_STRONG_HIGH     = 70
RSI_EXTREME_LOW     = 25         # oversold — RISE signal
RSI_STRONG_LOW      = 30
BB_PERIOD           = 20
BB_STD              = 2.0
ROC_PERIOD          = 5
PAIR_COOLDOWN_SECS  = 120        # seconds between trades on same pair

# REMOVED in AO-2.0 (kept for backward compat only)
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
MIN_CANDLES         = 30         # reduced from 100 — we only need 30

# Kept for main.py compatibility
CONFIDENCE = {
    "full_trade": 83,   # score 10/12 = 83%
    "half_trade": 58,   # score 7/12 = 58%
    "skip":       0,
    "minimum":    58,   # score 7/12
}

# ─────────────────────────────────────────────────
# RISK MANAGEMENT — AO-2.0
# ─────────────────────────────────────────────────
STAKE_PERCENT           = float(os.getenv("STAKE_PERCENT", 1.5))
MAX_DAILY_TRADES        = int(os.getenv("MAX_DAILY_TRADES", 10))    # DOWN from 15
MAX_CONSECUTIVE_LOSSES  = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
DAILY_LOSS_LIMIT        = float(os.getenv("DAILY_LOSS_LIMIT", 5.0))
DAILY_PROFIT_TARGET     = float(os.getenv("DAILY_PROFIT_TARGET", 30.0))
WEEKLY_LOSS_LIMIT       = 10.0
CONSECUTIVE_LOSS_PAUSE  = 1800   # 30 min in seconds
WIN_STREAK_REDUCE       = 5
KELLY_SAFETY_FACTOR     = 0.25   # kept for compat
MAX_CONCURRENT_TRADES   = 2

# ─────────────────────────────────────────────────
# REMOVED IN AO-2.0 — kept as empty to avoid import errors
# ─────────────────────────────────────────────────
GROQ_MIN_CONFIDENCE     = 80
MIN_INDICATORS_AGREE    = 3
MIN_TIMEFRAMES_AGREE    = 1
VOLATILITY_LEVELS       = {"low": 1.0, "medium": 5.0, "high": 20.0, "extreme": 50.0}
WICK_BODY_RATIO_MIN     = 1.5
MAX_PRICE_DIFFERENCE    = 0.0005
SIGNAL_VALIDITY_CANDLES = 2
SIGNAL_VALIDITY_SECONDS = 600

# ─────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────
PORT     = int(os.getenv("PORT", 10000))
TIMEZONE = os.getenv("TIMEZONE", "Africa/Lagos")
TRADING_SESSIONS  = {}
NEWS_BLOCK_MINUTES = 0      # No news blocking on synthetics

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
    # GROQ_API_KEY no longer required in AO-2.0
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
    print(f"\nMode:          {TRADE_MODE}")
    print(f"Pairs:         {SYNTHETIC_PAIRS}")
    print(f"Min Score:     {MIN_SCORE}/12 to trade")
    print(f"Max Trades:    {MAX_DAILY_TRADES}/day")
    print(f"Daily Target:  ${DAILY_PROFIT_TARGET}")
    print(f"Daily Loss:    {DAILY_LOSS_LIMIT}%")
    print(f"Stake:         {STAKE_PERCENT}% per trade")
    print(f"Expiry:        {EXPIRY_DEFAULT}min default, {EXPIRY_HIGH_CONF}min high-conf")