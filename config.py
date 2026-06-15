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
VERSION  = "AO-2.4"
SYMBOL   = "⚡"
MOTTO    = "We Don't Predict. We Know."

# ─────────────────────────────────────────────────
# DERIV CREDENTIALS
# ─────────────────────────────────────────────────
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")
TRADE_MODE      = os.getenv("TRADING_MODE", "PRACTICE")

# ─────────────────────────────────────────────────
# GROQ AI — DISABLED in AO-2.0
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
# V25 and V10 ONLY — most controlled oscillation
# ─────────────────────────────────────────────────
SYNTHETIC_PAIRS  = ["V25", "V10"]
MAX_ACTIVE_PAIRS = 1
PRIMARY_PAIRS    = ["V25", "V10"]
SECONDARY_PAIRS  = []
V75_MIN_SCORE    = 999    # Effectively disabled

# ─────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":   1,
    "primary": 5,
}

# ─────────────────────────────────────────────────
# EXPIRY — 3min default, 5min high confidence
# ─────────────────────────────────────────────────
EXPIRY_DEFAULT   = 3
EXPIRY_HIGH_CONF = 5
EXPIRY_SECONDS   = 180

# ─────────────────────────────────────────────────
# SIGNAL ENGINE — AO-2.4 SCORING
#
# MIN_SCORE = 9  → fires a REAL trade (75%+)
# PHANTOM_MIN_SCORE = 7 → shadow-logged only, no money
#
# This means:
#   score 7-8  → phantom trade logged, no real trade
#   score 9+   → real trade fires
#   score < 7  → skipped entirely
# ─────────────────────────────────────────────────
MIN_SCORE         = 9    # Live trade threshold — 75%+
PHANTOM_MIN_SCORE = 7    # Shadow log threshold — data collection only

RSI_PERIOD       = 14
RSI_EXTREME_HIGH = 78
RSI_STRONG_HIGH  = 72
RSI_EXTREME_LOW  = 22
RSI_STRONG_LOW   = 28
BB_PERIOD        = 20
BB_STD           = 2.0
ROC_PERIOD       = 5
PAIR_COOLDOWN_SECS = 180

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

CONFIDENCE = {
    "full_trade": 83,
    "half_trade": 67,
    "skip":       0,
    "minimum":    75,
}

# ─────────────────────────────────────────────────
# RISK MANAGEMENT
# ─────────────────────────────────────────────────
STAKE_PERCENT          = float(os.getenv("STAKE_PERCENT", 1.0))
MAX_DAILY_TRADES       = int(os.getenv("MAX_DAILY_TRADES", 25))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 2))
DAILY_LOSS_LIMIT       = float(os.getenv("DAILY_LOSS_LIMIT", 4.0))
DAILY_PROFIT_TARGET    = float(os.getenv("DAILY_PROFIT_TARGET", 1000.0))
WEEKLY_LOSS_LIMIT      = 10.0
CONSECUTIVE_LOSS_PAUSE = 3600
WIN_STREAK_REDUCE      = 5
KELLY_SAFETY_FACTOR    = 0.25
MAX_CONCURRENT_TRADES  = 1

# ─────────────────────────────────────────────────
# REMOVED IN AO-2.0 — kept to avoid import errors
# ─────────────────────────────────────────────────
GROQ_MIN_CONFIDENCE     = 83
MIN_INDICATORS_AGREE    = 4
MIN_TIMEFRAMES_AGREE    = 1
VOLATILITY_LEVELS       = {"low": 1.0, "medium": 5.0, "high": 20.0, "extreme": 50.0}
WICK_BODY_RATIO_MIN     = 1.5
MAX_PRICE_DIFFERENCE    = 0.0005
SIGNAL_VALIDITY_CANDLES = 2
SIGNAL_VALIDITY_SECONDS = 600

# ─────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────
PORT               = int(os.getenv("PORT", 10000))
TIMEZONE           = os.getenv("TIMEZONE", "Africa/Lagos")
TRADING_SESSIONS   = {}
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
    print(f"\nMode:               {TRADE_MODE}")
    print(f"Pairs:              {SYNTHETIC_PAIRS}")
    print(f"Live Trade Score:   {MIN_SCORE}/12 (75%+)")
    print(f"Phantom Score:      {PHANTOM_MIN_SCORE}/12 (shadow only)")
    print(f"Max Trades:         {MAX_DAILY_TRADES}/day")
    print(f"Daily Target:       ${DAILY_PROFIT_TARGET}")
    print(f"Daily Loss Limit:   {DAILY_LOSS_LIMIT}%")
    print(f"Stake:              {STAKE_PERCENT}% per trade")
    print(f"Expiry:             {EXPIRY_DEFAULT}min default, {EXPIRY_HIGH_CONF}min high-conf")
    print(f"Consec. Loss Pause: {CONSECUTIVE_LOSS_PAUSE // 60} minutes")