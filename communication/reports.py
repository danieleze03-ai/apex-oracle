# ⚡ APEX ORACLE — AO-1.0
# Reports System
# Generates performance reports
# Sends beautiful summaries to Telegram
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
from datetime import datetime, timedelta, time as dt_time
from loguru import logger
from data.database import (
    get_today_stats,
    get_weekly_stats,
    get_last_trades,
    get_top_patterns,
)
from communication.telegram import send_alert


# ─────────────────────────────────────────────────
# DAILY REPORT
# ─────────────────────────────────────────────────

async def send_daily_summary():
    """
    Send daily performance summary
    Runs automatically at 8PM WAT every day
    """
    try:
        stats  = get_today_stats()
        trades = get_last_trades(5)

        total  = stats.get("total_trades", 0)
        wins   = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        pnl    = stats.get("profit_loss", 0)
        wr     = stats.get("win_rate", 0)

        pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
        emoji   = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        grade   = (
            "🏆 EXCELLENT" if wr >= 70 else
            "✅ GOOD"      if wr >= 60 else
            "⚠️ AVERAGE"   if wr >= 50 else
            "❌ POOR"
        )

        # Recent trades summary
        recent_str = ""
        for t in trades[:5]:
            r = t.get("result", "?")
            p = t.get("pair",   "?")
            d = t.get("direction", "?")
            e = "✅" if r == "WIN" else "❌"
            recent_str += f"  {e} {p} {d}\n"

        msg = (
            f"⚡ <b>APEX ORACLE — DAILY SUMMARY</b>\n"
            f"{'─' * 32}\n"
            f"📅 {datetime.now().strftime('%A, %d %B %Y')}\n\n"
            f"{emoji} <b>P&L Today:</b> {pnl_str}\n"
            f"📊 <b>Total Trades:</b> {total}\n"
            f"✅ <b>Wins:</b> {wins} "
            f"❌ <b>Losses:</b> {losses}\n"
            f"🎯 <b>Win Rate:</b> {wr}%\n"
            f"🏅 <b>Grade:</b> {grade}\n\n"
            f"<b>Recent Trades:</b>\n"
            f"{recent_str if recent_str else '  No trades today'}\n"
            f"{'─' * 32}\n"
            f"⚡ <i>We Don't Predict. We Know.</i>"
        )

        await send_alert(msg)
        logger.success("✅ Daily summary sent to Telegram!")
        return True

    except Exception as e:
        logger.error(f"❌ Daily summary error: {e}")
        return False


# ─────────────────────────────────────────────────
# WEEKLY EVOLUTION REPORT
# ─────────────────────────────────────────────────

async def send_weekly_evolution_report(evolution_data: dict):
    """
    Send weekly evolution report
    Runs every Sunday after evolution system
    """
    try:
        stats     = evolution_data.get("stats", {})
        total     = stats.get("total_trades", 0)
        wins      = stats.get("wins", 0)
        losses    = stats.get("losses", 0)
        wr        = stats.get("win_rate", 0)
        pnl       = stats.get("profit_loss", 0)
        pnl_str   = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"

        top_pats  = evolution_data.get("top_patterns",   [])
        weak_pats = evolution_data.get("weak_patterns",  [])
        avoid_pats= evolution_data.get("avoid_patterns", [])
        recs      = evolution_data.get("recommendations", [])
        new_conf  = evolution_data.get("new_confidence", 75)
        version   = evolution_data.get("strategy_version", 1)
        ai_analysis = evolution_data.get("ai_analysis", "")
        best_hours  = evolution_data.get("best_hours", [])

        # Format patterns
        top_str = "\n".join(
            [f"  ✅ {p[0]} ({p[1]}%)" for p in top_pats[:3]]
        ) or "  None identified yet"

        weak_str = "\n".join(
            [f"  ❌ {p[0]} ({p[1]}%)" for p in weak_pats[:3]]
        ) or "  None identified"

        avoid_str = (
            ", ".join(avoid_pats[:3]) if avoid_pats else "None"
        )

        recs_str = "\n".join(
            [f"  → {r}" for r in recs[:3]]
        ) or "  Continue current approach"

        hours_str = (
            ", ".join([f"{h[0]:02d}:00" for h in best_hours[:3]])
            if best_hours else "All sessions"
        )

        emoji = "🟢" if pnl > 0 else "🔴"

        msg = (
            f"⚡ <b>APEX ORACLE — WEEKLY EVOLUTION</b>\n"
            f"🧬 <b>Strategy v{version} Deployed!</b>\n"
            f"{'─' * 32}\n\n"
            f"📊 <b>WEEKLY PERFORMANCE</b>\n"
            f"{emoji} P&L: {pnl_str}\n"
            f"📈 Trades: {total} | "
            f"✅ {wins}W ❌ {losses}L\n"
            f"🎯 Win Rate: {wr}%\n\n"
            f"🏆 <b>TOP PATTERNS THIS WEEK</b>\n"
            f"{top_str}\n\n"
            f"⚠️ <b>WEAK PATTERNS</b>\n"
            f"{weak_str}\n\n"
            f"🚫 <b>AVOIDING NEXT WEEK</b>\n"
            f"  {avoid_str}\n\n"
            f"⏰ <b>BEST TRADING HOURS</b>\n"
            f"  {hours_str}\n\n"
            f"🧠 <b>AI ANALYSIS</b>\n"
            f"  {ai_analysis[:200] if ai_analysis else 'N/A'}\n\n"
            f"📋 <b>RECOMMENDATIONS</b>\n"
            f"{recs_str}\n\n"
            f"🎯 <b>New Min Confidence:</b> {new_conf}%\n"
            f"{'─' * 32}\n"
            f"⚡ <i>APEX ORACLE is getting smarter!</i>"
        )

        await send_alert(msg)
        logger.success("✅ Weekly evolution report sent!")
        return True

    except Exception as e:
        logger.error(f"❌ Weekly report error: {e}")
        return False


# ─────────────────────────────────────────────────
# STARTUP REPORT
# ─────────────────────────────────────────────────

async def send_startup_report(balance: float, mode: str):
    """Send report when bot starts up"""
    try:
        from management.session import get_session_summary
        session = get_session_summary()

        msg = (
            f"⚡ <b>APEX ORACLE IS ONLINE!</b>\n"
            f"<i>We Don't Predict. We Know.</i>\n"
            f"{'─' * 32}\n"
            f"🤖 <b>Version:</b> AO-1.0\n"
            f"📊 <b>Mode:</b> {mode}\n"
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"🕐 <b>Session:</b> {session['session']}\n"
            f"⭐ <b>Quality:</b> {session['session_quality']}\n"
            f"💱 <b>Best Pair:</b> {session['best_pair']}\n"
            f"✅ <b>Trading:</b> "
            f"{'ALLOWED' if session['trading_allowed'] else 'WAITING'}\n"
            f"{'─' * 32}\n"
            f"📱 Send /start to see all commands\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S WAT')}"
        )

        await send_alert(msg)
        logger.success("✅ Startup report sent!")

    except Exception as e:
        logger.error(f"❌ Startup report error: {e}")


# ─────────────────────────────────────────────────
# RISK ALERTS
# ─────────────────────────────────────────────────

async def send_pause_alert(reason: str, duration_mins: int):
    """Alert when bot pauses trading"""
    await send_alert(
        f"⏸️ <b>TRADING PAUSED</b>\n"
        f"{'─' * 30}\n"
        f"📋 <b>Reason:</b> {reason}\n"
        f"⏱️ <b>Duration:</b> {duration_mins} minutes\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M WAT')}"
    )


async def send_resume_alert():
    """Alert when bot resumes trading"""
    await send_alert(
        f"▶️ <b>TRADING RESUMED</b>\n"
        f"⚡ APEX ORACLE is back in action!\n"
        f"🕐 {datetime.now().strftime('%H:%M WAT')}"
    )


async def send_loss_limit_alert(
    limit_type: str,
    current_loss: float,
    limit_pct: float
):
    """Alert when loss limit is hit"""
    await send_alert(
        f"🚨 <b>{limit_type} LOSS LIMIT HIT!</b>\n"
        f"{'─' * 30}\n"
        f"💸 <b>Current Loss:</b> ${abs(current_loss):.2f}\n"
        f"📊 <b>Limit:</b> {limit_pct}%\n"
        f"🛑 <b>Trading stopped</b> to protect capital\n"
        f"🕐 {datetime.now().strftime('%H:%M WAT')}"
    )


async def send_win_streak_alert(streak: int):
    """Alert on impressive win streak"""
    await send_alert(
        f"🏆 <b>WIN STREAK: {streak} IN A ROW!</b>\n"
        f"⚡ APEX ORACLE is on fire!\n"
        f"🛡️ Reducing stake by 20% to protect profits\n"
        f"🕐 {datetime.now().strftime('%H:%M WAT')}"
    )


async def send_shutdown_alert(reason: str):
    """Alert on emergency shutdown"""
    await send_alert(
        f"🚨 <b>EMERGENCY SHUTDOWN!</b>\n"
        f"{'─' * 30}\n"
        f"📋 <b>Reason:</b> {reason}\n"
        f"🛑 All trading stopped!\n"
        f"🕐 {datetime.now().strftime('%H:%M WAT')}"
    )


# ─────────────────────────────────────────────────
# NEWS BLOCK ALERT
# ─────────────────────────────────────────────────

async def send_news_block_alert(event: str, minutes: int):
    """Alert when news blocks trading"""
    await send_alert(
        f"📰 <b>NEWS BLOCK ACTIVE</b>\n"
        f"{'─' * 30}\n"
        f"📋 <b>Event:</b> {event}\n"
        f"⏱️ <b>Block:</b> {minutes} minutes\n"
        f"🛡️ Trading paused to protect capital\n"
        f"🕐 {datetime.now().strftime('%H:%M WAT')}"
    )


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    print("\n⚡ APEX ORACLE — Reports Test")
    print("─" * 45)
    print("Sending startup report test...")

    asyncio.run(send_startup_report(10000.00, "PRACTICE"))
    print("✅ Check your Telegram!")