# ⚡ APEX ORACLE — AO-1.0
# Database Layer — Supabase Connection
# Stores all trades, signals, performance data
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
from datetime import datetime
from loguru import logger

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────

def get_client():
    """Create and return Supabase client"""
    from supabase import create_client
    import os

    # Remove Render/system proxy vars that break supabase httpx internals
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(var, None)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("❌ Supabase URL or KEY missing from .env!")

    return create_client(url, key)def get_client():
    """Create and return Supabase client"""
    from supabase import create_client
    import os

    # Remove Render/system proxy vars that break supabase httpx internals
    for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        os.environ.pop(var, None)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("❌ Supabase URL or KEY missing from .env!")

    return create_client(url, key)

# ─────────────────────────────────────────────────
# TABLE SETUP — Run once to create all tables
# ─────────────────────────────────────────────────

TABLES_SQL = """
-- TRADES TABLE
create table if not exists trades (
    id              bigserial primary key,
    timestamp       timestamptz default now(),
    pair            text not null,
    direction       text not null,
    stake           float not null,
    expiry_seconds  int not null,
    confidence      float not null,
    result          text,
    profit_loss     float,
    balance_after   float,
    pattern         text,
    market_regime   text,
    sentiment_score float,
    groq_reasoning  text,
    mode            text default 'PRACTICE'
);

-- SIGNALS TABLE (includes skipped signals)
create table if not exists signals (
    id              bigserial primary key,
    timestamp       timestamptz default now(),
    pair            text not null,
    direction       text,
    confidence      float,
    rsi_value       float,
    macd_value      float,
    ema_cross       text,
    bb_position     text,
    volume_signal   text,
    tf_agreement    int,
    action          text,
    skip_reason     text
);

-- PERFORMANCE TABLE (daily stats)
create table if not exists performance (
    id              bigserial primary key,
    date            date default current_date unique,
    total_trades    int default 0,
    wins            int default 0,
    losses          int default 0,
    win_rate        float default 0,
    profit_loss     float default 0,
    starting_balance float,
    ending_balance  float,
    best_trade      float,
    worst_trade     float
);

-- PATTERNS TABLE (pattern success rates)
create table if not exists patterns (
    id              bigserial primary key,
    pattern_name    text unique,
    total_trades    int default 0,
    wins            int default 0,
    losses          int default 0,
    win_rate        float default 0,
    last_updated    timestamptz default now()
);

-- EVOLUTION TABLE (weekly strategy updates)
create table if not exists evolution (
    id              bigserial primary key,
    week_start      date,
    week_end        date,
    top_patterns    text,
    weak_patterns   text,
    adjustments     text,
    win_rate_before float,
    win_rate_after  float,
    created_at      timestamptz default now()
);

-- MANIPULATION LOG
create table if not exists manipulation_log (
    id              bigserial primary key,
    timestamp       timestamptz default now(),
    pair            text,
    iq_price        float,
    yahoo_price     float,
    difference      float,
    action_taken    text
);

-- SENTIMENT LOG
create table if not exists sentiment_log (
    id              bigserial primary key,
    timestamp       timestamptz default now(),
    score           float,
    bias            text,
    headlines       text,
    source          text
);
"""


# ─────────────────────────────────────────────────
# TRADE OPERATIONS
# ─────────────────────────────────────────────────

def log_trade(trade_data: dict) -> bool:
    """
    Log a completed trade to database

    trade_data = {
        "pair":           "EURUSD-OTC",
        "direction":      "CALL",
        "stake":          150.00,
        "expiry_seconds": 300,
        "confidence":     88.5,
        "result":         "WIN",
        "profit_loss":    127.50,
        "balance_after":  10127.50,
        "pattern":        "Bullish Engulfing",
        "market_regime":  "TRENDING",
        "sentiment_score": 65.0,
        "groq_reasoning": "Strong uptrend...",
        "mode":           "PRACTICE"
    }
    """
    try:
        client = get_client()
        trade_data["timestamp"] = datetime.now().isoformat()
        result = client.table("trades").insert(trade_data).execute()
        logger.success(f"✅ Trade logged: {trade_data['pair']} {trade_data['direction']} → {trade_data['result']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to log trade: {e}")
        return False


def log_signal(signal_data: dict) -> bool:
    """Log every signal including skipped ones"""
    try:
        client = get_client()
        signal_data["timestamp"] = datetime.now().isoformat()
        client.table("signals").insert(signal_data).execute()
        logger.debug(f"📊 Signal logged: {signal_data.get('pair')} → {signal_data.get('action')}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to log signal: {e}")
        return False


def log_manipulation(manip_data: dict) -> bool:
    """Log suspected broker manipulation"""
    try:
        client = get_client()
        manip_data["timestamp"] = datetime.now().isoformat()
        client.table("manipulation_log").insert(manip_data).execute()
        logger.warning(f"🚨 Manipulation logged: {manip_data.get('pair')} diff={manip_data.get('difference')}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to log manipulation: {e}")
        return False


def log_sentiment(sentiment_data: dict) -> bool:
    """Log sentiment analysis results"""
    try:
        client = get_client()
        sentiment_data["timestamp"] = datetime.now().isoformat()
        client.table("sentiment_log").insert(sentiment_data).execute()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to log sentiment: {e}")
        return False


# ─────────────────────────────────────────────────
# PERFORMANCE OPERATIONS
# ─────────────────────────────────────────────────

def update_daily_performance(date: str = None) -> bool:
    """Calculate and update today's performance stats"""
    try:
        client  = get_client()
        today   = date or datetime.now().date().isoformat()

        result = client.table("trades")\
            .select("*")\
            .gte("timestamp", f"{today}T00:00:00")\
            .lte("timestamp", f"{today}T23:59:59")\
            .execute()

        trades = result.data
        if not trades:
            return True

        total   = len(trades)
        wins    = len([t for t in trades if t["result"] == "WIN"])
        losses  = len([t for t in trades if t["result"] == "LOSS"])
        pnl     = sum(t["profit_loss"] for t in trades if t["profit_loss"])
        win_rate= (wins / total * 100) if total > 0 else 0

        profits = [t["profit_loss"] for t in trades if t["profit_loss"]]
        best    = max(profits) if profits else 0
        worst   = min(profits) if profits else 0

        perf_data = {
            "date":            today,
            "total_trades":    total,
            "wins":            wins,
            "losses":          losses,
            "win_rate":        round(win_rate, 2),
            "profit_loss":     round(pnl, 2),
            "best_trade":      round(best, 2),
            "worst_trade":     round(worst, 2),
        }

        client.table("performance").upsert(perf_data).execute()
        logger.success(f"✅ Performance updated: {total} trades, {win_rate:.1f}% win rate")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update performance: {e}")
        return False


def get_today_stats() -> dict:
    """Get today's trading statistics"""
    try:
        client = get_client()
        today  = datetime.now().date().isoformat()

        result = client.table("trades")\
            .select("*")\
            .gte("timestamp", f"{today}T00:00:00")\
            .execute()

        trades  = result.data
        total   = len(trades)
        wins    = len([t for t in trades if t.get("result") == "WIN"])
        losses  = len([t for t in trades if t.get("result") == "LOSS"])
        pnl     = sum(t.get("profit_loss", 0) for t in trades)
        win_rate= (wins / total * 100) if total > 0 else 0

        return {
            "total_trades": total,
            "wins":         wins,
            "losses":       losses,
            "win_rate":     round(win_rate, 1),
            "profit_loss":  round(pnl, 2),
        }

    except Exception as e:
        logger.error(f"❌ Failed to get today stats: {e}")
        return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "profit_loss": 0}


def get_last_trades(limit: int = 10) -> list:
    """Get last N trades for Telegram /history command"""
    try:
        client = get_client()
        result = client.table("trades")\
            .select("*")\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get last trades: {e}")
        return []


def get_weekly_stats() -> dict:
    """Get this week's statistics for evolution report"""
    try:
        client = get_client()
        from datetime import timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        result = client.table("trades")\
            .select("*")\
            .gte("timestamp", week_ago)\
            .execute()

        trades  = result.data
        total   = len(trades)
        wins    = len([t for t in trades if t.get("result") == "WIN"])
        losses  = len([t for t in trades if t.get("result") == "LOSS"])
        pnl     = sum(t.get("profit_loss", 0) for t in trades)
        win_rate= (wins / total * 100) if total > 0 else 0

        return {
            "total_trades": total,
            "wins":         wins,
            "losses":       losses,
            "win_rate":     round(win_rate, 1),
            "profit_loss":  round(pnl, 2),
            "trades":       trades,
        }

    except Exception as e:
        logger.error(f"❌ Failed to get weekly stats: {e}")
        return {}


# ─────────────────────────────────────────────────
# PATTERN OPERATIONS
# ─────────────────────────────────────────────────

def update_pattern_stats(pattern_name: str, won: bool) -> bool:
    """Update win/loss stats for a candlestick pattern"""
    try:
        client = get_client()

        result = client.table("patterns")\
            .select("*")\
            .eq("pattern_name", pattern_name)\
            .execute()

        if result.data:
            pattern = result.data[0]
            total   = pattern["total_trades"] + 1
            wins    = pattern["wins"] + (1 if won else 0)
            losses  = pattern["losses"] + (0 if won else 1)
            win_rate= (wins / total * 100)

            client.table("patterns").update({
                "total_trades": total,
                "wins":         wins,
                "losses":       losses,
                "win_rate":     round(win_rate, 2),
                "last_updated": datetime.now().isoformat(),
            }).eq("pattern_name", pattern_name).execute()
        else:
            client.table("patterns").insert({
                "pattern_name": pattern_name,
                "total_trades": 1,
                "wins":         1 if won else 0,
                "losses":       0 if won else 1,
                "win_rate":     100.0 if won else 0.0,
                "last_updated": datetime.now().isoformat(),
            }).execute()

        return True
    except Exception as e:
        logger.error(f"❌ Failed to update pattern stats: {e}")
        return False


def get_top_patterns(limit: int = 5) -> list:
    """Get top performing patterns for evolution"""
    try:
        client = get_client()
        result = client.table("patterns")\
            .select("*")\
            .gte("total_trades", 5)\
            .order("win_rate", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Failed to get top patterns: {e}")
        return []


# ─────────────────────────────────────────────────
# CONNECTION TEST
# ─────────────────────────────────────────────────

def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        client = get_client()
        client.table("trades").select("id").limit(1).execute()
        logger.success("✅ Supabase connection successful!")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")
        return False


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Database Test")
    print("Testing Supabase connection...\n")

    if test_connection():
        print("✅ Database connected!")
        print("\nTesting stats fetch...")
        stats = get_today_stats()
        print(f"Today's stats: {stats}")
    else:
        print("❌ Connection failed!")
        print("Check your SUPABASE_URL and SUPABASE_KEY in .env")