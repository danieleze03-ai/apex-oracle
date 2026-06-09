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
# TRADING SESSIONS
# ─────────────────────────────────────────────────

SESSIONS = {
    "london_open": {
        "start":   time(8,  0),
        "end":     time(10, 0),
        "label":   "London Open",
        "quality": "GOOD",
    },
    "overlap": {
        "start":   time(14, 0),
        "end":     time(17, 0),
        "label":   "London/NY Overlap",
        "quality": "BEST",
    },
    "ny_close": {
        "start":   time(19, 0),
        "end":     time(21, 0),
        "label":   "NY Close",
        "quality": "GOOD",
    },
}

# Avoid these times completely
AVOID_TIMES = [
    {"start": time(0,  0), "end": time(7, 59), "reason": "Asian session"},
    {"start": time(18, 0), "end": time(23, 59), "reason": "Friday close risk"},
]


# ─────────────────────────────────────────────────
# TRADING PAIRS — DERIV.COM
# ─────────────────────────────────────────────────

# Weekday forex pairs (Deriv)
PRIMARY_PAIRS = ["EURUSD", "GBPUSD"]
BACKUP_PAIRS  = ["GBPJPY", "EURGBP", "USDJPY"]

# Weekend synthetic indices (Deriv — 24/7)
SYNTHETIC_PAIRS = ["V75", "V50", "V25", "V10"]


def get_active_pairs() -> list:
    """
    Get pairs to trade based on current session

    Weekdays (market hours) → Forex pairs
    Weekends                → Synthetic indices (24/7)
    """
    current = now_wat()
    weekend = is_weekend()

    # Weekend — synthetic indices only
    if weekend:
        logger.debug("📅 Weekend — using Synthetic indices (V75/V50/V25/V10)")
        return SYNTHETIC_PAIRS

    # Market hours (8am-10pm WAT) — use forex pairs
    market_open  = time(8,  0)
    market_close = time(22, 0)

    if market_open <= current.time() <= market_close:
        logger.debug("🕐 Market hours — using Forex pairs")
        return PRIMARY_PAIRS + BACKUP_PAIRS

    # Off hours on weekday — synthetic as fallback
    logger.debug("🌙 Off hours — using Synthetic indices")
    return SYNTHETIC_PAIRS


def get_best_pair() -> str:
    """Get the single best pair for current conditions"""
    pairs = get_active_pairs()
    return pairs[0] if pairs else "EURUSD"


# ─────────────────────────────────────────────────
# SESSION CHECKER
# ─────────────────────────────────────────────────

def get_current_session() -> dict:
    """
    Get current trading session info

    Returns:
    {
        "session":  "London/NY Overlap",
        "quality":  "BEST",
        "active":   True,
        "next":     "NY Close at 19:00"
    }
    """
    current = now_wat()
    weekend = is_weekend()

    for key, session in SESSIONS.items():
        if session["start"] <= current.time() <= session["end"]:
            return {
                "session": session["label"],
                "quality": session["quality"],
                "active":  True,
                "key":     key,
            }

    # Find next session
    next_session = None
    for key, session in SESSIONS.items():
        if session["start"] > current.time():
            next_session = f"{session['label']} at {session['start'].strftime('%H:%M')}"
            break

    if not next_session:
        first = list(SESSIONS.values())[0]
        next_session = f"{first['label']} at {first['start'].strftime('%H:%M')} tomorrow"

    return {
        "session": "Outside trading hours",
        "quality": "NONE",
        "active":  False,
        "next":    next_session,
        "weekend": weekend,
    }


# ─────────────────────────────────────────────────
# TRADING WINDOW CHECK
# ─────────────────────────────────────────────────

def is_trading_time() -> dict:
    """
    Master check — should we be trading right now?

    Returns:
    {
        "allowed":  True/False,
        "reason":   "explanation",
        "session":  "London Open",
        "quality":  "GOOD"
    }
    """
    current = now_wat()
    weekend = is_weekend()

    # ── Friday after 6PM — avoid ──────────────────
    if current.weekday() == 4 and current.time() >= time(18, 0):
        return {
            "allowed": False,
            "reason":  "Friday after 18:00 — weekend gap risk",
            "session": "Weekend approaching",
            "quality": "NONE",
        }

    # ── Asian session — avoid on weekdays ────────
    if not weekend:
        if current.time() < time(7, 59):
            return {
                "allowed": False,
                "reason":  "Asian session — low volatility/choppy",
                "session": "Asian Session",
                "quality": "NONE",
            }

    # ── Check active sessions ─────────────────────
    session = get_current_session()

    if session["active"]:
        return {
            "allowed": True,
            "reason":  f"✅ {session['session']} is active",
            "session": session["session"],
            "quality": session["quality"],
        }

    # ── Weekend — Synthetic indices available 24/7 ─
    if weekend:
        return {
            "allowed": True,
            "reason":  "Weekend — Synthetic indices available 24/7",
            "session": "Weekend Synthetic",
            "quality": "MODERATE",
        }

    # ── Outside session hours ─────────────────────
    return {
        "allowed": False,
        "reason":  f"Outside trading hours. Next: {session.get('next', 'soon')}",
        "session": "No Active Session",
        "quality": "NONE",
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
    Rule: expiry = same as analysis timeframe
    """
    session = get_current_session()

    if session.get("quality") == "BEST":
        return 5
    elif session.get("quality") == "GOOD":
        return 5
    else:
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
        "session":         session.get("session", "Unknown"),
        "session_quality": session.get("quality", "NONE"),
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