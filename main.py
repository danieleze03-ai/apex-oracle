# ⚡ APEX ORACLE — AO-1.0
# Main Orchestrator — The Brain
# Ties ALL systems together
# Runs 24/7 on Render.com FREE
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import time
import asyncio
import threading
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# IMPORTS — All Systems
# ─────────────────────────────────────────────────

# Core
from core.logger      import setup_logger
from core.signals     import generate_signal
from core.patterns    import detect_patterns
from core.volatility  import check_volatility
from core.confluence  import calculate_confluence

# Intelligence
from intelligence.sentiment  import get_market_sentiment
from intelligence.groq_brain import get_ai_decision
from intelligence.evolution  import (
    run_weekly_evolution,
    should_run_evolution,
    load_strategy,
)

# Broker
from broker.deriv import (
    connect, disconnect, reconnect,
    get_balance, get_candles,
    get_current_price, switch_mode,
    place_trade, check_trade_result,
    is_connected,
)
from broker.guard import compare_prices

# Management
from management.risk import (
    can_trade, calculate_stake,
    update_after_trade, set_starting_balance,
    get_risk_state, pause_trading,
    resume_trading, emergency_shutdown,
)
from management.session import (
    is_trading_time, get_active_pairs,
    get_best_pair, get_session_summary,
    is_news_blocked, get_optimal_expiry,
    is_signal_valid,
)
from management.shadow import (
    place_shadow_trade, record_live_result,
    record_shadow_result, compare_live_vs_shadow,
    get_shadow_summary,
)

# Communication
from communication.telegram import (
    start_telegram_bot,
    send_alert, send_alert_sync,
    send_trade_entry, send_trade_result,
    send_manipulation_alert,
    inject_dependencies,
)
from communication.reports import (
    send_startup_report,
    send_daily_summary,
    send_weekly_evolution_report,
    send_pause_alert,
    send_loss_limit_alert,
    send_shutdown_alert,
    send_news_block_alert,
)

# Data
from data.database import (
    log_trade, log_signal,
    update_daily_performance,
    get_today_stats,
)
from data.backup import (
    run_weekly_backup,
    should_run_backup,
)

# Server
from server.keep_alive import (
    start_keep_alive,
    update_status,
)


# ─────────────────────────────────────────────────
# PAIR CONFIG — SYNTHETIC ONLY
# ─────────────────────────────────────────────────

SYNTHETIC_PAIRS = ["V75", "V50", "V25", "V10", "V100"]

def get_active_pair_list() -> list:
    """
    Return Synthetic pairs for 24/7 testing.
    Forex pairs removed completely.
    """
    logger.info("📈 Synthetic-only mode — all pairs active 24/7")
    return SYNTHETIC_PAIRS


# ─────────────────────────────────────────────────
# BOT STATE
# ─────────────────────────────────────────────────

bot_state = {
    "running":      False,
    "mode":         os.getenv("TRADING_MODE", "PRACTICE"),
    "balance":      0.0,
    "trades_today": 0,
    "wins_today":   0,
    "losses_today": 0,
    "last_signal":  None,
    "last_trade":   None,
    "start_time":   datetime.now(),
}

TIMEFRAMES    = [1, 5, 15, 60]
LOOP_INTERVAL = 30


# ─────────────────────────────────────────────────
# CANDLE FETCHER
# ─────────────────────────────────────────────────

def fetch_all_timeframes(pair: str) -> dict:
    """Fetch candles for all timeframes"""
    candles = {}
    for tf in TIMEFRAMES:
        data = get_candles(pair, tf, 100)
        if data:
            candles[str(tf)] = data
    return candles


# ─────────────────────────────────────────────────
# SIGNAL PROCESSOR
# ─────────────────────────────────────────────────

def process_signal(pair: str) -> dict:
    """
    Full signal processing pipeline:
    1. Fetch candles
    2. Calculate confluence
    3. Check sentiment
    4. Ask Groq AI
    5. Return final decision
    """
    try:
        # ── Fetch candles ─────────────────────────
        all_candles = fetch_all_timeframes(pair)
        primary     = all_candles.get("5", [])

        if len(primary) < 50:
            return {
                "action": "SKIP",
                "reason": "Not enough candle data",
            }

        # ── Calculate confluence ──────────────────
        confluence = calculate_confluence(
            primary, all_candles, pair
        )

        direction  = confluence["direction"]
        confidence = confluence["confidence"]

        # Log signal
        log_signal({
            "pair":        pair,
            "direction":   direction,
            "confidence":  confidence,
            "action":      confluence["action"],
            "skip_reason": confluence.get("reason", ""),
        })

        bot_state["last_signal"] = {
            "pair":       pair,
            "direction":  direction,
            "confidence": confidence,
            "time":       datetime.now().isoformat(),
        }
        update_status("last_signal", bot_state["last_signal"])

        if confluence["action"] != "TRADE":
            return {
                "action": "SKIP",
                "reason": confluence["reason"],
            }

        # ── Check sentiment ───────────────────────
        sentiment = get_market_sentiment()

        if sentiment["blocked"]:
            asyncio.run(send_news_block_alert(
                sentiment["block_reason"], 30
            ))
            return {
                "action": "SKIP",
                "reason": f"News blocked: {sentiment['block_reason']}",
            }

        # ── Get price for manipulation check ─────
        deriv_price = get_current_price(pair)
        guard       = compare_prices(pair, deriv_price)

        if not guard["safe"]:
            asyncio.run(send_manipulation_alert({
                "pair":        pair,
                "deriv_price": guard["deriv_price"],
                "yahoo_price": guard["yahoo_price"],
                "difference":  guard["difference"],
            }))
            return {
                "action": "SKIP",
                "reason": guard["reason"],
            }

        # ── Ask Groq AI ───────────────────────────
        breakdown  = confluence.get("breakdown", {})
        indicators = breakdown.get("indicators", {})
        ind_data   = indicators.get("details", {})

        trade_data = {
            "pair":                 pair,
            "timeframe":            "5min",
            "expiry":               "5 minutes",
            "rsi_value":            ind_data.get("rsi",      {}).get("value",  50),
            "rsi_signal":           ind_data.get("rsi",      {}).get("signal", "N/A"),
            "macd_signal":          ind_data.get("macd",     {}).get("signal", "N/A"),
            "bb_signal":            ind_data.get("bb",       {}).get("signal", "N/A"),
            "ema_signal":           ind_data.get("ema",      {}).get("signal", "N/A"),
            "stochrsi_signal":      ind_data.get("stochrsi", {}).get("signal", "N/A"),
            "indicators_agree":     breakdown.get("indicators", {}).get("agreements", 0),
            "pattern":              confluence.get("pattern", "None"),
            "pattern_direction":    direction,
            "pattern_strength":     breakdown.get("pattern",    {}).get("strength",  0),
            "volatility_level":     breakdown.get("volatility", {}).get("level", "MEDIUM"),
            "volatility_tradeable": True,
            "sentiment_score":      sentiment["score"],
            "sentiment_bias":       sentiment["bias"],
            "news_blocked":         sentiment["blocked"],
            "tf_agreements":        breakdown.get("timeframes", {}).get("agreements", 0),
            "primary_direction":    direction,
            "confluence_score":     confidence,
            "balance":              bot_state["balance"],
            "trades_today":         bot_state["trades_today"],
        }

        ai_result = get_ai_decision(trade_data)

        if not ai_result["approved"]:
            return {
                "action": "SKIP",
                "reason": f"AI rejected: {ai_result['reasoning'][:100]}",
            }

        # ── All checks passed — TRADE! ────────────
        return {
            "action":       "TRADE",
            "direction":    direction,
            "confidence":   confidence,
            "pair":         pair,
            "stake_size":   confluence["stake_size"],
            "pattern":      confluence.get("pattern", "None"),
            "sentiment":    sentiment["score"],
            "ai_reasoning": ai_result["reasoning"],
            "expiry":       get_optimal_expiry(),
        }

    except Exception as e:
        logger.error(f"❌ Signal processing error: {e}")
        return {"action": "SKIP", "reason": str(e)}


# ─────────────────────────────────────────────────
# TRADE EXECUTOR — NON-BLOCKING
# ─────────────────────────────────────────────────

def execute_trade(signal: dict) -> bool:
    """
    Execute a trade based on signal
    1. Calculate stake
    2. Place live trade
    3. Spawn background thread to wait for result
    4. Return immediately so main loop stays responsive
    """
    try:
        pair      = signal["pair"]
        direction = signal["direction"]
        expiry    = signal.get("expiry", 5)
        balance   = get_balance()

        # ── Calculate stake ───────────────────────
        strategy = load_strategy()
        win_rate = 0.65
        history  = strategy.get("performance_history", [])
        if history:
            last_wr  = history[-1].get("win_rate", 65)
            win_rate = last_wr / 100

        stake = calculate_stake(
            balance,
            signal["confidence"],
            signal["stake_size"],
            win_rate,
        )

        if stake <= 0:
            logger.warning("⚠️ Stake is 0 — skipping trade")
            return False

        # ── Place live trade ──────────────────────
        logger.info(
            f"⚡ EXECUTING: {pair} {direction} "
            f"${stake} {expiry}min"
        )

        trade_result = place_trade(pair, direction, stake, expiry)

        if not trade_result["success"]:
            error_msg = trade_result.get('error', 'Unknown error')
            # Handle specific Deriv API errors gracefully
            if "Trading is not offered for this duration" in error_msg:
                logger.warning(f"⏳ Deriv does not allow {expiry}min expiry on {pair}. Try 5min.")
            elif "closed" in error_msg.lower():
                logger.warning(f"🔒 {pair} is closed for trading.")
            else:
                logger.error(f"❌ Trade failed: {error_msg}")
            return False

        trade_id = trade_result["trade_id"]

        # ── Send entry alert ──────────────────────
        asyncio.run(send_trade_entry({
            "pair":       pair,
            "direction":  direction,
            "stake":      stake,
            "expiry":     expiry,
            "confidence": signal["confidence"],
            "pattern":    signal.get("pattern", "None"),
            "mode":       bot_state["mode"],
        }))

        # ── Update bot state ──────────────────────
        bot_state["trades_today"] += 1
        update_status("trades_today", bot_state["trades_today"])
        bot_state["last_trade"] = {
            "pair":      pair,
            "direction": direction,
            "stake":     stake,
            "time":      datetime.now().isoformat(),
        }
        update_status("last_trade", bot_state["last_trade"])

        # ── Spawn background thread to handle result ──
        def wait_for_result():
            wait_seconds = (expiry * 60) + 5
            logger.info(f"⏳ Waiting {wait_seconds}s for result in background...")
            time.sleep(wait_seconds)

            result = check_trade_result(trade_id)
            outcome = result["result"]
            profit = result["profit"]
            new_balance = get_balance()

            # Update risk state
            update_after_trade(outcome, profit)

            # Update counters
            if outcome == "WIN":
                bot_state["wins_today"] += 1
                update_status("wins_today", bot_state["wins_today"])
            else:
                bot_state["losses_today"] += 1
                update_status("losses_today", bot_state["losses_today"])

            bot_state["balance"] = new_balance
            update_status("balance", new_balance)

            # Log to database
            log_trade({
                "pair":            pair,
                "direction":       direction,
                "stake":           stake,
                "expiry_seconds":  expiry * 60,
                "confidence":      signal["confidence"],
                "result":          outcome,
                "profit_loss":     profit,
                "balance_after":   new_balance,
                "pattern":         signal.get("pattern", "None"),
                "sentiment_score": signal.get("sentiment", 0),
                "groq_reasoning":  signal.get("ai_reasoning", ""),
                "mode":            bot_state["mode"],
            })

            # Send result alert
            asyncio.run(send_trade_result({
                "pair":          pair,
                "direction":     direction,
                "result":        outcome,
                "profit_loss":   profit,
                "balance_after": new_balance,
            }))

            # Record live result for shadow
            record_live_result(trade_id, outcome, profit)

            logger.info(
                f"{'✅ WIN' if outcome == 'WIN' else '❌ LOSS'} | "
                f"{pair} {direction} | "
                f"P&L: ${profit:.2f} | "
                f"Balance: ${new_balance:.2f}"
            )

        threading.Thread(target=wait_for_result, daemon=True).start()

        return True

    except Exception as e:
        logger.error(f"❌ Trade execution error: {e}")
        return False


# ─────────────────────────────────────────────────
# DAILY TASKS
# ─────────────────────────────────────────────────

def run_daily_tasks():
    """Run daily maintenance tasks"""
    now = datetime.now()

    # Daily report at 8PM WAT
    if now.hour == 20 and now.minute < 2:
        logger.info("📊 Running daily report...")
        asyncio.run(send_daily_summary())
        update_daily_performance()

    # Weekly evolution Sunday midnight
    if should_run_evolution():
        logger.info("🧬 Running weekly evolution...")
        evolution_data = run_weekly_evolution()
        if evolution_data.get("success"):
            asyncio.run(
                send_weekly_evolution_report(evolution_data)
            )

    # Weekly backup Sunday 1am
    if should_run_backup():
        logger.info("💾 Running weekly backup...")
        backup_result = run_weekly_backup()
        asyncio.run(send_alert(
            f"💾 <b>Weekly Backup Complete!</b>\n"
            f"📁 File: {backup_result.get('filename')}\n"
            f"📊 Trades: {backup_result.get('trades')}\n"
            f"💿 Size: {backup_result.get('size')}"
        ))


# ─────────────────────────────────────────────────
# MAIN TRADING LOOP
# ─────────────────────────────────────────────────

def trading_loop():
    """
    Main 24/7 trading loop

    Every 30 seconds:
    1. Check if trading is allowed
    2. Scan ALL synthetic pairs in order
    3. Process signal for each pair until one is found
    4. Execute trade if approved
    5. Run daily tasks
    """
    logger.info("⚡ Trading loop started!")
    bot_state["running"] = True
    update_status("running", True)

    while True:
        try:
            # ── Update balance ────────────────────
            balance = get_balance()

            if balance == 0.0:
                logger.warning("⚠️ Balance returned 0 — checking connection...")
                if not reconnect():
                    time.sleep(30)
                    continue
                balance = get_balance()
                if balance == 0.0:
                    time.sleep(30)
                    continue

            bot_state["balance"] = balance
            update_status("balance", balance)

            # ── Check if can trade ────────────────
            risk_check = can_trade(balance)
            if not risk_check["allowed"]:
                logger.info(
                    f"⏸️ Trading paused: {risk_check['reason']}"
                )
                time.sleep(LOOP_INTERVAL)
                run_daily_tasks()
                continue

            # ── Check session (REMOVED) ────────────
            session = {"allowed": True, "session": "SYNTHETIC-24/7"}

            # ── Check news block ──────────────────
            news = is_news_blocked()
            if news["blocked"]:
                logger.info(f"📰 {news['reason']}")
                time.sleep(LOOP_INTERVAL)
                continue

            # ── Scan ALL synthetic pairs ───────────
            active_pairs = get_active_pair_list()
            trade_found = False

            for pair in active_pairs:
                logger.info(
                    f"🔍 Analyzing {pair} | "
                    f"Session: {session['session']} | "
                    f"Balance: ${balance:.2f} | "
                    f"Mode: SYNTHETIC-ONLY"
                )

                # ── Process signal ──────────────────
                signal = process_signal(pair)

                if signal["action"] == "TRADE":
                    logger.info(
                        f"🚀 SIGNAL APPROVED: "
                        f"{signal['direction']} {pair} | "
                        f"Confidence: {signal['confidence']}%"
                    )
                    execute_trade(signal)
                    trade_found = True
                    break
                else:
                    logger.debug(
                        f"⏭️ {pair} skipped: {signal['reason']}"
                    )

            if not trade_found:
                logger.debug("No tradeable signal found in this cycle.")

            run_daily_tasks()
            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            logger.info("⚡ Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Trading loop error: {e}")
            time.sleep(LOOP_INTERVAL)


# ─────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────

def startup():
    """Initialize all systems and start bot"""
    setup_logger(os.getenv("LOG_LEVEL", "INFO"))

    # ── Check all required environment variables ──
    required_vars = ["DERIV_API_TOKEN", "GROQ_API_KEY", "TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.critical(f"❌ Missing environment variables: {', '.join(missing)}")
        return False

    setup_logger(os.getenv("LOG_LEVEL", "INFO"))

    logger.info("=" * 50)
    logger.info("⚡ APEX ORACLE — AO-1.0 STARTING UP")
    logger.info("   We Don't Predict. We Know.")
    logger.info("=" * 50)

    start_keep_alive()

    if not connect():
        logger.critical("❌ Cannot connect to Deriv.com!")
        logger.critical("Check DERIV_API_TOKEN in .env")
        return False

    balance = get_balance()
    mode    = os.getenv("TRADING_MODE", "PRACTICE")
    bot_state["balance"] = balance
    bot_state["mode"]    = mode
    update_status("balance", balance)
    update_status("mode",    mode)

    set_starting_balance(balance)

    inject_dependencies(bot_state)
    telegram_app = start_telegram_bot()

    from telegram.ext import CommandHandler

    async def test_trade(update, context):
        import random
        from broker.deriv import get_balance, place_trade, check_trade_result
        from data.database import log_trade
        from datetime import datetime
        import asyncio

        try:
            await update.message.reply_text("🔄 Starting test trade...")

            loop = asyncio.get_running_loop()
            balance = await loop.run_in_executor(None, get_balance)
            if balance < 5.0:
                await update.message.reply_text(f"⚠️ Balance too low: ${balance:.2f}")
                return

            pair = "V75"
            direction = "CALL" if random.randint(0, 1) == 0 else "PUT"
            stake = 1.00
            expiry = 1

            trade_result = await loop.run_in_executor(None, place_trade, pair, direction, stake, expiry)

            if not trade_result.get("success"):
                error_msg = trade_result.get('error', 'Unknown error')
                if "Trading is not offered for this duration" in error_msg:
                    await update.message.reply_text(f"❌ Trade failed: {error_msg}\n\nTry expiry=5 instead.")
                else:
                    await update.message.reply_text(f"❌ Trade failed: {error_msg}")
                return

            trade_id = trade_result.get("trade_id")
            await update.message.reply_text(
                f"🚀 Trade placed!\n"
                f"{pair} {direction} | ${stake} | {expiry}min\n"
                f"Trade ID: {trade_id}\n\n"
                f"⏳ Waiting {expiry} minutes..."
            )

            await asyncio.sleep((expiry * 60) + 5)

            result = await loop.run_in_executor(None, check_trade_result, trade_id)
            outcome = result.get("result", "UNKNOWN")
            profit = result.get("profit", 0.0)
            new_balance = await loop.run_in_executor(None, get_balance)

            await loop.run_in_executor(None, log_trade, {
                "pair": pair,
                "direction": direction,
                "stake": stake,
                "expiry_seconds": expiry * 60,
                "confidence": 99.9,
                "result": outcome,
                "profit_loss": profit,
                "balance_after": new_balance,
                "pattern": "TEST_PATTERN",
                "market_regime": "TEST",
                "sentiment_score": 50.0,
                "groq_reasoning": "Manual test trade",
                "mode": "TESTING"
            })

            await update.message.reply_text(
                f"✅ **Test Trade Complete!**\n"
                f"Result: **{outcome}**\n"
                f"Profit/Loss: **${profit:.2f}**\n"
                f"New Balance: **${new_balance:.2f}**\n\n"
                f"Check Supabase table `trades` for the entry."
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    telegram_app.add_handler(CommandHandler("testtrade", test_trade))

    asyncio.run(send_startup_report(balance, mode))

    pair_display = "V75, V50, V25, V10, V100"

    logger.success("=" * 50)
    logger.success(f"✅ APEX ORACLE IS ONLINE!")
    logger.success(f"💰 Balance:         ${balance:.2f}")
    logger.success(f"📊 Mode:            {mode}")
    logger.success(f"🎯 Min Confidence:  75%")
    logger.success(f"💱 Active Pairs:    {pair_display}")
    logger.success(f"📅 Trading:         SYNTHETIC-ONLY 24/7")
    logger.success(f"🔌 Broker:          Deriv.com")
    logger.success("=" * 50)

    return telegram_app


# ─────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app = startup()
        if not app:
            logger.critical("❌ Startup failed! Check your .env file")
            exit(1)

        # Start trading loop in a background thread
        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()

        # ❌ DO NOT CALL app.run_polling() HERE — it is already handled inside start_telegram_bot()

        # Keep the main thread alive by waiting
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n⚡ APEX ORACLE shutting down...")
        asyncio.run(send_alert(
            "⚡ <b>APEX ORACLE OFFLINE</b>\n"
            "Bot stopped manually."
        ))
        disconnect()
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        asyncio.run(send_shutdown_alert(str(e)))
        disconnect()