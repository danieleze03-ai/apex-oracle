# ⚡ APEX ORACLE — AO-2.5
# Central Configuration — TREND FOLLOWING REBUILD
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
#
# CHANGES FROM AO-2.4:
# - Strategy switched: MEAN REVERSION → TREND FOLLOWING
# - New EMA diff threshold: 0.07% minimum to count as trend
# - Score gate raised: 10+/12 = live, 8-9 = phantom
# - New scoring system (12pts) built for trend-following
# - RSI now a BRAKE (filter out), not a trigger
# - MACD added as momentum confirmation
# ─────────────────────────────────────────────────

import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ─────────────────────────────────────────────────
# IDENTITY
# ─────────────────────────────────────────────────
BOT_NAME = "APEX ORACLE"
VERSION  = "AO-2.5"
SYMBOL   = "⚡"
MOTTO    = "We Don't Predict. We Know."

# ─────────────────────────────────────────────────
# DERIV CREDENTIALS
# ─────────────────────────────────────────────────
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN")
TRADE_MODE      = os.getenv("TRADING_MODE", "PRACTICE")

# ─────────────────────────────────────────────────
# GROQ AI — DISABLED
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
# TRADING PAIRS
# ─────────────────────────────────────────────────
SYNTHETIC_PAIRS  = ["V25", "V10"]
MAX_ACTIVE_PAIRS = 1
PRIMARY_PAIRS    = ["V25", "V10"]
SECONDARY_PAIRS  = []
V75_MIN_SCORE    = 999  # Disabled

# ─────────────────────────────────────────────────
# TIMEFRAMES — AO-2.5 TREND FOLLOWING
# ─────────────────────────────────────────────────
TIMEFRAMES = {
    "entry":    1,   # 1min  — pullback-resume trigger
    "fast":     3,   # 3min  — trend check TF1
    "mid":      5,   # 5min  — trend check TF2
    "slow":     10,  # 10min — trend check TF3
}

# Candles to fetch per timeframe
CANDLES_TREND_TF  = 60   # enough for EMA8/21 + buffer on 3/5/10min
CANDLES_ENTRY_TF  = 40   # enough for RSI + MACD on 1min

# ─────────────────────────────────────────────────
# EXPIRY
# ─────────────────────────────────────────────────
EXPIRY_DEFAULT   = 3
EXPIRY_HIGH_CONF = 5
EXPIRY_SECONDS   = 180

# ─────────────────────────────────────────────────
# TREND-FOLLOWING ENGINE — AO-2.5
# ─────────────────────────────────────────────────

# EMA settings for trend detection
EMA_FAST   = 8
EMA_SLOW   = 21

# Minimum EMA diff (as % of price) to count as a real trend
# Below this = NEUTRAL, direction ignored
EMA_DIFF_THRESHOLD = 0.0007   # 0.07%

# Score gates
MIN_SCORE         = 10   # 10+/12 → live trade
PHANTOM_MIN_SCORE = 8    # 8-9/12 → phantom (shadow log only)

# RSI brake thresholds — FILTER OUT if already extreme on entry TF
RSI_PERIOD       = 14
RSI_BRAKE_HIGH   = 70    # In uptrend: skip if RSI already above this
RSI_BRAKE_LOW    = 30    # In downtrend: skip if RSI already below this

# Pullback zone — where RSI should DIP TO before resuming (uptrend entry)
RSI_PULLBACK_LOW  = 40   # RSI dip low end in uptrend
RSI_PULLBACK_HIGH = 55   # RSI dip high end in uptrend (mirror for downtrend)

# MACD settings
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9

# Backward compat — kept so other modules don't break
RSI_EXTREME_HIGH = 78
RSI_STRONG_HIGH  = 72
RSI_EXTREME_LOW  = 22
RSI_STRONG_LOW   = 28
RSI_OVERBOUGHT   = 70
RSI_OVERSOLD     = 30
RSI_NEUTRAL_LOW  = 45
RSI_NEUTRAL_HIGH = 55
BB_PERIOD        = 20
BB_STD           = 2.0
ROC_PERIOD       = 5
EMA_FAST_OLD     = 9   # old value — unused
EMA_SLOW_OLD     = 21
ATR_PERIOD       = 14
MIN_CANDLES      = 30
PAIR_COOLDOWN_SECS = 180

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
# REMOVED — kept to avoid import errors
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
    print(f"\nStrategy:           TREND FOLLOWING (AO-2.5)")
    print(f"Mode:               {TRADE_MODE}")
    print(f"Pairs:              {SYNTHETIC_PAIRS}")
    print(f"EMA:                {EMA_FAST}/{EMA_SLOW} | Threshold: {EMA_DIFF_THRESHOLD*100:.2f}%")
    print(f"Live Trade Score:   {MIN_SCORE}/12")
    print(f"Phantom Score:      {PHANTOM_MIN_SCORE}/12 (shadow only)")
    print(f"Max Trades:         {MAX_DAILY_TRADES}/day")
    print(f"Daily Target:       ${DAILY_PROFIT_TARGET}")
    print(f"Daily Loss Limit:   {DAILY_LOSS_LIMIT}%")
    print(f"Stake:              {STAKE_PERCENT}% per trade")
    print(f"Expiry:             {EXPIRY_DEFAULT}min default, {EXPIRY_HIGH_CONF}min high-conf")