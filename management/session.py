# ⚡ APEX ORACLE — AO-1.0
# Session Management System
# Controls trading windows, pair selection,
# and automatically switches Synthetic vs Forex pairs
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import pytz
from datetime import datetime, time
from loguru import logger


# ─────────────────────────────────────────────────
# TIMEZONE
# ─────────────────────────────────────────────────

WAT = pytz.timezone("Africa/Lagos")   # UTC+1


def now_wat() -> datetime:
    """Get current time in WAT"""
    return datetime.now(WAT)


def current_time_wat() -> time:
    """Get current time object in WAT"""
    return now_wat().time()


def is_weekend() -> bool:
    """Check if it's weekend"""
    return now_wat().weekday() >= 5   # 5=Saturday 6=Sunday


# ─────────────────────────────────────────────────
# TRADING SESSIONS (DISABLED — SYNTHETIC ONLY)
# ─────────────────────────────────────────────────

SESSIONS = {
    "synthetic_24_7": {
        "start":   time(0,  0),
        "end":     time(23, 59),
        "label":   "Synthetic 24/7",
        "quality": "BEST",
    },
}

# Avoid times (all removed — Synthetics always available)
AVOID_TIMES = []


# ─────────────────────────────────────────────────
# TRADING PAIRS — DERIV.COM (SYNTHETIC ONLY)
# ─────────────────────────────────────────────────

SYNTHETIC_PAIRS = ["V75", "V50", "V25", "V10", "V100", "V60", "V90"]


def get_active_pairs() -> list:
    """
    Get pairs to trade — Synthetic indices only (24/7)
    """
    logger.debug("📈 Synthetic-only mode — all pairs active 24/7")
    return SYNTHETIC_PAIRS


def get_best_pair() -> str:
    """Get the single best pair for current conditions"""
    return "V75"  # Always V75 for Synthetic-only


# ─────────────────────────────────────────────────
# SESSION CHECKER
# ─────────────────────────────────────────────────

def get_current_session() -> dict:
    """
    Get current trading session info
    Synthetic-only — always active.
    """
    return {
        "session": "Synthetic 24/7",
        "quality": "BEST",
        "active":  True,
        "key":     "synthetic_24_7",
    }


# ─────────────────────────────────────────────────
# TRADING WINDOW CHECK
# ─────────────────────────────────────────────────

def is_trading_time() -> dict:
    """
    Master check — should we be trading right now?
    Synthetic-only — always allowed.
    """
    return {
        "allowed": True,
        "reason":  "Synthetic indices available 24/7",
        "session": "Synthetic 24/7",
        "quality": "BEST",
    }


# ─────────────────────────────────────────────────
# NEWS BLOCK CHECKER
# ─────────────────────────────────────────────────

_news_blocks = []


def block_for_news(event_name: str, minutes: int = 30):
    """Block trading around news event"""
    from datetime import timedelta
    block_until = now_wat() + timedelta(minutes=minutes)
    _news_blocks.append({
        "event":       event_name,
        "block_until": block_until,
    })
    logger.warning(
        f"📰 News block: {event_name} — "
        f"trading paused for {minutes} mins"
    )


def is_news_blocked() -> dict:
    """Check if trading is blocked due to news"""
    global _news_blocks
    now = now_wat()

    _news_blocks = [b for b in _news_blocks if b["block_until"] > now]

    if _news_blocks:
        block     = _news_blocks[0]
        remaining = (block["block_until"] - now).seconds // 60
        return {
            "blocked": True,
            "reason":  f"News block: {block['event']} — {remaining} mins remaining",
            "event":   block["event"],
        }

    return {"blocked": False, "reason": "No news blocks active"}


# ─────────────────────────────────────────────────
# EXPIRY CALCULATOR
# ─────────────────────────────────────────────────

def get_optimal_expiry(timeframe: int = 5) -> int:
    """
    Get optimal expiry time in minutes
    Synthetic-only — default 5 minutes.
    """
    return 5


def is_signal_valid(signal_age_seconds: int) -> bool:
    """
    Check if a signal is still valid
    Signal valid for max 2 candles = 10 minutes
    """
    max_age = 600   # 10 minutes in seconds
    return signal_age_seconds <= max_age


# ─────────────────────────────────────────────────
# SESSION SUMMARY
# ─────────────────────────────────────────────────

def get_session_summary() -> dict:
    """Full session status for Telegram /status command"""
    current    = now_wat()
    session    = get_current_session()
    trading    = is_trading_time()
    news_block = is_news_blocked()
    pairs      = get_active_pairs()

    return {
        "current_time":    current.strftime("%H:%M WAT"),
        "day":             current.strftime("%A"),
        "session":         session.get("session", "Synthetic 24/7"),
        "session_quality": session.get("quality", "BEST"),
        "trading_allowed": trading["allowed"],
        "trading_reason":  trading["reason"],
        "news_blocked":    news_block["blocked"],
        "news_reason":     news_block["reason"],
        "active_pairs":    pairs,
        "best_pair":       get_best_pair(),
        "is_weekend":      is_weekend(),
    }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Session Management Test")
    print("─" * 45)

    summary = get_session_summary()

    print(f"\n🕐 Current Time:    {summary['current_time']}")
    print(f"📅 Day:             {summary['day']}")
    print(f"📊 Session:         {summary['session']}")
    print(f"⭐ Quality:         {summary['session_quality']}")
    print(f"✅ Trading Allowed: {summary['trading_allowed']}")
    print(f"💬 Reason:          {summary['trading_reason']}")
    print(f"📰 News Blocked:    {summary['news_blocked']}")
    print(f"💱 Active Pairs:    {summary['active_pairs']}")
    print(f"🎯 Best Pair:       {summary['best_pair']}")
    print(f"📅 Weekend:         {summary['is_weekend']}")