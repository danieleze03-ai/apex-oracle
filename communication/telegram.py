# ⚡ APEX ORACLE — AO-1.0
# Telegram Command Center
# Control the bot from your phone!
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import asyncio
import threading
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

# ─────────────────────────────────────────────────
# BOT INSTANCE
# ─────────────────────────────────────────────────

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Global references injected by main.py
_bot_state   = None
_iq_instance = None


def inject_dependencies(bot_state, iq_instance=None):
    """Inject bot state from main.py"""
    global _bot_state, _iq_instance
    _bot_state   = bot_state
    _iq_instance = iq_instance


# ─────────────────────────────────────────────────
# SEND ALERT (used throughout bot)
# ─────────────────────────────────────────────────

async def send_alert(message: str):
    """Send alert message to Telegram"""
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id    = CHAT_ID,
            text       = message,
            parse_mode = "HTML",
        )
        logger.debug(f"📱 Telegram alert sent")
    except Exception as e:
        logger.error(f"❌ Telegram send error: {e}")


def send_alert_sync(message: str):
    """Synchronous wrapper for send_alert"""
    try:
        asyncio.get_event_loop().run_until_complete(
            send_alert(message)
        )
    except Exception:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(send_alert(message))
            loop.close()
        except Exception as e:
            logger.error(f"❌ Sync alert error: {e}")


# ─────────────────────────────────────────────────
# TRADE ALERTS
# ─────────────────────────────────────────────────

async def send_trade_entry(trade: dict):
    """Alert when trade is placed"""
    direction_emoji = "📈" if trade["direction"] == "CALL" else "📉"
    msg = (
        f"⚡ <b>APEX ORACLE — TRADE ENTRY</b>\n"
        f"{'─' * 30}\n"
        f"{direction_emoji} <b>Direction:</b> {trade['direction']}\n"
        f"💱 <b>Pair:</b> {trade['pair']}\n"
        f"💰 <b>Stake:</b> ${trade['stake']:.2f}\n"
        f"⏱️ <b>Expiry:</b> {trade['expiry']} minutes\n"
        f"🎯 <b>Confidence:</b> {trade['confidence']}%\n"
        f"🕯️ <b>Pattern:</b> {trade.get('pattern', 'None')}\n"
        f"📊 <b>Score:</b> {trade.get('confidence', 0):.0f}% ({trade.get('pattern', 'MEAN_REVERSION')})\n"
        f"📊 <b>Mode:</b> {trade.get('mode', 'PRACTICE')}\n"
        f"📌 <b>Entry Price:</b> {trade.get('entry_price', 'N/A')}\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S WAT')}"
    )
    await send_alert(msg)


async def send_trade_result(trade: dict):
    """Alert when trade result is known"""
    result  = trade.get("result", "")
    emoji   = "✅ WIN" if result == "WIN" else "❌ LOSS"
    pnl     = trade.get("profit_loss", 0)
    pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"

    msg = (
        f"⚡ <b>APEX ORACLE — TRADE RESULT</b>\n"
        f"{'─' * 30}\n"
        f"{emoji}\n"
        f"💱 <b>Pair:</b> {trade['pair']}\n"
        f"📊 <b>Direction:</b> {trade['direction']}\n"
        f"📌 <b>Entry Price:</b> {trade.get('entry_price', 'N/A')}\n"
        f"🏁 <b>Exit Price:</b> {trade.get('exit_price', 'N/A')}\n"
        f"💰 <b>P&L:</b> {pnl_str}\n"
        f"💳 <b>Balance:</b> ${trade.get('balance_after', 0):.2f}\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S WAT')}"
    )
    await send_alert(msg)


async def send_manipulation_alert(data: dict):
    """Alert when manipulation detected"""
    msg = (
        f"🚨 <b>MANIPULATION DETECTED!</b>\n"
        f"{'─' * 30}\n"
        f"💱 <b>Pair:</b> {data['pair']}\n"
        f"📊 <b>Deriv Price:</b> {data['deriv_price']}\n"
        f"📊 <b>Yahoo Price:</b> {data['yahoo_price']}\n"
        f"⚠️ <b>Difference:</b> {data['difference']:.6f}\n"
        f"🛡️ <b>Action:</b> Trade BLOCKED\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M:%S WAT')}"
    )
    await send_alert(msg)


async def send_daily_report(stats: dict):
    """Send daily performance report"""
    win_rate = stats.get("win_rate", 0)
    pnl      = stats.get("profit_loss", 0)
    pnl_str  = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
    emoji    = "🟢" if pnl > 0 else "🔴"

    msg = (
        f"⚡ <b>APEX ORACLE — DAILY REPORT</b>\n"
        f"{'─' * 30}\n"
        f"{emoji} <b>P&L:</b> {pnl_str}\n"
        f"📊 <b>Trades:</b> {stats.get('total_trades', 0)}\n"
        f"✅ <b>Wins:</b> {stats.get('wins', 0)}\n"
        f"❌ <b>Losses:</b> {stats.get('losses', 0)}\n"
        f"🎯 <b>Win Rate:</b> {win_rate}%\n"
        f"📅 <b>Date:</b> {datetime.now().strftime('%d %b %Y')}\n"
        f"🕐 <b>Time:</b> {datetime.now().strftime('%H:%M WAT')}"
    )
    await send_alert(msg)


# ─────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    msg = (
        f"⚡ <b>APEX ORACLE — AO-2.0</b>\n"
        f"<i>We Don't Predict. We Know.</i>\n\n"
        f"<b>Available Commands:</b>\n"
        f"/status    — Bot health + activity\n"
        f"/pause     — Pause trading\n"
        f"/resume    — Resume trading\n"
        f"/report    — Today's performance\n"
        f"/balance   — Current balance\n"
        f"/history   — Last 10 trades\n"
        f"/mode demo — Switch to demo\n"
        f"/mode live — Switch to live\n"
        f"/risk low  — Conservative mode\n"
        f"/risk high — Aggressive mode\n"
        f"/shutdown  — Emergency stop\n"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        from management.session  import get_session_summary
        from management.risk     import get_risk_state
        from data.database       import get_today_stats

        session = get_session_summary()
        risk    = get_risk_state()
        stats   = get_today_stats()

        trading_emoji = "🟢" if session["trading_allowed"] else "🔴"
        mode          = os.getenv("TRADING_MODE", "PRACTICE")

        msg = (
            f"⚡ <b>APEX ORACLE STATUS</b>\n"
            f"{'─' * 30}\n"
            f"{trading_emoji} <b>Trading:</b> "
            f"{'ACTIVE' if session['trading_allowed'] else 'PAUSED'}\n"
            f"📊 <b>Mode:</b> {mode}\n"
            f"🕐 <b>Session:</b> {session['session']}\n"
            f"⭐ <b>Quality:</b> {session['session_quality']}\n"
            f"💱 <b>Best Pair:</b> {session['best_pair']}\n"
            f"📈 <b>Trades Today:</b> {stats['total_trades']}\n"
            f"✅ <b>Wins:</b> {stats['wins']} "
            f"❌ <b>Losses:</b> {stats['losses']}\n"
            f"🎯 <b>Win Rate:</b> {stats['win_rate']}%\n"
            f"💰 <b>Today P&L:</b> ${stats['profit_loss']:.2f}\n"
            f"🕐 <b>Time:</b> {session['current_time']}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ Status error: {e}")


async def cmd_pause(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /pause command"""
    try:
        from management.risk import pause_trading
        pause_trading("Manual pause via Telegram", minutes=1440)
        await update.message.reply_text(
            "⏸️ <b>Trading PAUSED</b>\nSend /resume to continue.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Pause error: {e}")


async def cmd_resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command"""
    try:
        from management.risk import resume_trading
        resume_trading()
        await update.message.reply_text(
            "▶️ <b>Trading RESUMED</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Resume error: {e}")


async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    try:
        from data.database import get_today_stats
        stats = get_today_stats()
        await send_daily_report(stats)
        await update.message.reply_text(
            "📊 Report sent above!",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Report error: {e}")


async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    try:
        balance = _bot_state.get("balance", 0.0) if _bot_state else 0.0
        mode    = os.getenv("TRADING_MODE", "PRACTICE")
        await update.message.reply_text(
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"📊 <b>Mode:</b> {mode}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Balance error: {e}")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /history command"""
    try:
        from data.database import get_last_trades
        trades = get_last_trades(10)

        if not trades:
            await update.message.reply_text("No trades found yet!")
            return

        msg = "⚡ <b>LAST 10 TRADES</b>\n" + "─" * 30 + "\n"
        for t in trades:
            emoji   = "✅" if t.get("result") == "WIN" else "❌"
            pnl     = t.get("profit_loss", 0) or 0
            pnl_str = f"+${pnl:.2f}" if pnl > 0 else f"-${abs(pnl):.2f}"
            msg    += (
                f"{emoji} {t.get('pair')} "
                f"{t.get('direction')} "
                f"{pnl_str}\n"
            )

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        await update.message.reply_text(f"❌ History error: {e}")


async def cmd_mode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /mode command"""
    try:
        args = ctx.args
        if not args:
            await update.message.reply_text(
                "Usage: /mode demo or /mode live"
            )
            return

        mode = args[0].lower()
        if mode == "demo":
            os.environ["TRADING_MODE"] = "PRACTICE"
            await update.message.reply_text(
                "📊 <b>Switched to DEMO mode</b>",
                parse_mode="HTML"
            )
        elif mode == "live":
            os.environ["TRADING_MODE"] = "REAL"
            await update.message.reply_text(
                "💰 <b>Switched to LIVE mode</b>\n"
                "⚠️ Real money will be traded!",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                "Usage: /mode demo or /mode live"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Mode error: {e}")


async def cmd_risk(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /risk command"""
    try:
        args = ctx.args
        if not args:
            await update.message.reply_text(
                "Usage: /risk low or /risk high"
            )
            return

        level = args[0].lower()
        if level == "low":
            os.environ["STAKE_PERCENT"] = "0.5"
            await update.message.reply_text(
                "🛡️ <b>Conservative mode ON</b>\n"
                "Stake: 0.5% per trade",
                parse_mode="HTML"
            )
        elif level == "high":
            os.environ["STAKE_PERCENT"] = "2.0"
            await update.message.reply_text(
                "🚀 <b>Aggressive mode ON</b>\n"
                "Stake: 2.0% per trade",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                "Usage: /risk low or /risk high"
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Risk error: {e}")


async def cmd_shutdown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /shutdown command"""
    try:
        from management.risk import emergency_shutdown
        emergency_shutdown("Manual shutdown via Telegram")
        await update.message.reply_text(
            "🚨 <b>EMERGENCY SHUTDOWN ACTIVATED</b>\n"
            "All trading stopped immediately!",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Shutdown error: {e}")


# ─────────────────────────────────────────────────
# BOT LAUNCHER
# ─────────────────────────────────────────────────

def start_telegram_bot():
    """
    Start Telegram bot in background thread.
    Clears stale sessions FIRST to prevent Conflict errors on Render restarts.
    """
    try:
        if not TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN missing!")
            return None

        # ── STEP 1: Kill any stale polling session ──
        # This runs synchronously BEFORE the thread starts.
        # Every Render restart wipes the old session so the
        # new instance never conflicts with the previous one.
        async def _clear_stale_session():
            try:
                async with Bot(token=TOKEN) as bot:
                    await bot.delete_webhook(drop_pending_updates=True)
                logger.info("🧹 Stale Telegram session cleared")
            except Exception as e:
                logger.warning(f"⚠️ Could not clear session (non-fatal): {e}")

        asyncio.run(_clear_stale_session())

        # ── STEP 2: Build app and register commands ──
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start",    cmd_start))
        app.add_handler(CommandHandler("status",   cmd_status))
        app.add_handler(CommandHandler("pause",    cmd_pause))
        app.add_handler(CommandHandler("resume",   cmd_resume))
        app.add_handler(CommandHandler("report",   cmd_report))
        app.add_handler(CommandHandler("balance",  cmd_balance))
        app.add_handler(CommandHandler("history",  cmd_history))
        app.add_handler(CommandHandler("mode",     cmd_mode))
        app.add_handler(CommandHandler("risk",     cmd_risk))
        app.add_handler(CommandHandler("shutdown", cmd_shutdown))

        # ── STEP 3: Start polling in background thread ──
        def run_polling():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(app.initialize())
                loop.run_until_complete(app.start())
                loop.run_until_complete(app.updater.start_polling(
                    drop_pending_updates=True,  # belt-and-suspenders safety
                    allowed_updates=Update.ALL_TYPES,
                ))
                loop.run_forever()
            except Exception as e:
                logger.error(f"❌ Telegram polling error: {e}")

        thread = threading.Thread(target=run_polling, daemon=True)
        thread.start()

        logger.success("✅ Telegram bot started and polling!")
        return app

    except Exception as e:
        logger.error(f"❌ Telegram bot error: {e}")
        return None


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Telegram Test")
    print("─" * 45)
    print("Sending test message...")

    asyncio.run(send_alert(
        "⚡ <b>APEX ORACLE</b> is online!\n"
        "We Don't Predict. We Know. 🚀"
    ))
    print("✅ Test message sent! Check your Telegram!")