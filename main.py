# ⚡ APEX ORACLE — AO-2.5
# Main Orchestrator — TREND FOLLOWING REBUILD
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
# CHANGES FROM AO-2.4:
# - Strategy: MEAN REVERSION → TREND FOLLOWING
# - process_signal now fetches 3m, 5m, 10m, 1m candles
#   and passes them all to calculate_confluence
# - 1M confirmation replaced with pullback-resume check
#   (now handled INSIDE confluence engine, not here)
# - Score gate: 10+/12 = live, 8-9 = phantom
# - VERSION bumped to AO-2.5
# ─────────────────────────────────────────────────

import os
import time
import asyncio
import threading
import numpy as np
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────

from core.logger import setup_logger
from core.confluence import calculate_confluence
from core.phantom import phantom

from broker.deriv import (
    connect, disconnect, reconnect,
    get_balance, get_candles,
    get_current_price,
    place_trade, check_trade_result,
    is_connected,
)

from management.risk import (
    can_trade, can_trade_pair,
    calculate_stake,
    update_after_trade,
    register_trade_open,
    set_starting_balance,
    get_risk_state,
    pause_trading, resume_trading,
    emergency_shutdown,
)
from management.session import get_optimal_expiry

from communication.telegram import (
    start_telegram_bot,
    send_alert, send_alert_sync,
    send_trade_entry, send_trade_result,
    inject_dependencies,
)
from communication.reports import (
    send_startup_report,
    send_daily_summary,
    send_pause_alert,
    send_loss_limit_alert,
    send_shutdown_alert,
)

from data.database import (
    log_trade, log_signal,
    update_daily_performance,
    get_today_stats,
)
from data.backup import run_weekly_backup, should_run_backup

from server.keep_alive import start_keep_alive, update_status

import config

# ─────────────────────────────────────────────────
# PAIR LIST
# ─────────────────────────────────────────────────

ACTIVE_PAIRS  = config.SYNTHETIC_PAIRS
LOOP_INTERVAL = 30

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
    "trade_active": False,
    "start_time":   datetime.now(),
}

# ─────────────────────────────────────────────────
# SIGNAL PROCESSOR — AO-2.5
#
# KEY CHANGE: We now fetch ALL 4 timeframes here
# and pass them into confluence as candles_by_tf.
# The confluence engine does all the scoring.
# No separate 1M reversal check needed anymore —
# pullback-resume logic lives inside confluence.py.
# ─────────────────────────────────────────────────

def process_signal(pair: str) -> dict:
    """
    AO-2.5 Signal Pipeline:
    1. Fetch 5min candles (primary)
    2. Fetch 3min, 10min, 1min candles (for MTF + pullback)
    3. Pass ALL to calculate_confluence
    4. Confluence handles: TF alignment, EMA strength,
       pullback-resume, RSI brake, MACD — scores out of 12
    5. Return TRADE / PHANTOM / SKIP decision
    """
    try:
        # ── Fetch all timeframes ───────────────────
        candles_5m  = get_candles(pair, 5,  config.CANDLES_TREND_TF)
        candles_3m  = get_candles(pair, 3,  config.CANDLES_TREND_TF)
        candles_10m = get_candles(pair, 10, config.CANDLES_TREND_TF)
        candles_1m  = get_candles(pair, 1,  config.CANDLES_ENTRY_TF)

        if not candles_5m or len(candles_5m) < 30:
            return {"action": "SKIP", "reason": "Not enough 5min candle data"}

        candles_by_tf = {
            "3m":  candles_3m,
            "10m": candles_10m,
            "1m":  candles_1m,
        }

        # ── Run confluence engine ──────────────────
        result = calculate_confluence(candles_5m, candles_by_tf, pair)

        log_signal({
            "pair":        pair,
            "direction":   result.get("direction", "SKIP"),
            "confidence":  result.get("confidence", 0),
            "action":      result.get("action", "SKIP"),
            "skip_reason": result.get("reason", ""),
        })

        bot_state["last_signal"] = {
            "pair":      pair,
            "direction": result.get("direction"),
            "score":     result.get("score", 0),
            "time":      datetime.now().isoformat(),
        }
        update_status("last_signal", bot_state["last_signal"])

        # ── Hard skip ──────────────────────────────
        if result["action"] == "SKIP":
            return {"action": "SKIP", "reason": result.get("reason", "No signal")}

        # ── Phantom only ───────────────────────────
        if result["action"] == "PHANTOM":
            logger.info(
                f"👻 PHANTOM LOG: {pair} {result['direction']} | "
                f"Score={result['score']}/12 — no real trade"
            )
            return {
                "action": "SKIP",
                "reason": f"Score {result['score']}/12 — phantom only, need {config.MIN_SCORE}+ for live",
            }

        # ── Score 10+ — TRADE ──────────────────────
        score  = result.get("score", 10)
        expiry = config.EXPIRY_HIGH_CONF if score >= 11 else config.EXPIRY_DEFAULT

        return {
            "action":     "TRADE",
            "direction":  result["direction"],
            "confidence": result["confidence"],
            "score":      score,
            "pair":       pair,
            "stake_size": result["stake_size"],
            "pattern":    result.get("pattern", "TREND_FOLLOWING"),
            "expiry":     expiry,
            "confirm":    result.get("reason", ""),
        }

    except Exception as e:
        import traceback
        logger.error(f"❌ Signal error on {pair}: {e}")
        logger.error(traceback.format_exc())
        return {"action": "SKIP", "reason": str(e)}


# ─────────────────────────────────────────────────
# TRADE EXECUTOR
# ─────────────────────────────────────────────────

def execute_trade(signal: dict) -> bool:
    """Execute trade and spawn background thread to watch result."""
    try:
        pair      = signal["pair"]
        direction = signal["direction"]
        expiry    = signal.get("expiry", config.EXPIRY_DEFAULT)
        balance   = get_balance()

        stake = calculate_stake(
            balance,
            signal["confidence"],
            signal["stake_size"],
        )
        if stake <= 0:
            logger.warning("⚠️ Stake is $0 — skipping")
            return False

        logger.info(
            f"⚡ TRADE: {pair} {direction} | "
            f"${stake} | {expiry}min | Score={signal.get('score', '?')}/12"
        )

        trade_result = place_trade(pair, direction, stake, expiry)
        if not trade_result["success"]:
            logger.error(f"❌ Trade failed: {trade_result.get('error', 'unknown')}")
            return False

        trade_id = trade_result["trade_id"]

        register_trade_open(pair)
        bot_state["trade_active"] = True

        asyncio.run(send_trade_entry({
            "pair":        pair,
            "direction":   direction,
            "stake":       stake,
            "expiry":      expiry,
            "confidence":  signal["confidence"],
            "pattern":     signal.get("pattern", "TREND_FOLLOWING"),
            "mode":        bot_state["mode"],
            "entry_price": 0.0,
        }))

        bot_state["trades_today"] += 1
        bot_state["last_trade"] = {
            "pair":      pair,
            "direction": direction,
            "stake":     stake,
            "time":      datetime.now().isoformat(),
        }
        update_status("trades_today", bot_state["trades_today"])
        update_status("last_trade",   bot_state["last_trade"])

        def wait_for_result():
            try:
                wait_sec = (expiry * 60) + 5
                logger.info(f"⏳ Waiting {wait_sec}s for {pair} result...")
                time.sleep(wait_sec)

                result  = check_trade_result(trade_id)
                outcome = result["result"]
                profit  = result["profit"]
                new_bal = get_balance()

                update_after_trade(outcome, profit)
                phantom.record_trade(result=outcome)

                if outcome == "WIN":
                    bot_state["wins_today"] += 1
                    update_status("wins_today", bot_state["wins_today"])
                else:
                    bot_state["losses_today"] += 1
                    update_status("losses_today", bot_state["losses_today"])

                bot_state["balance"]      = new_bal
                bot_state["trade_active"] = False
                update_status("balance", new_bal)

                log_trade({
                    "pair":            pair,
                    "direction":       direction,
                    "stake":           stake,
                    "expiry_seconds":  expiry * 60,
                    "confidence":      signal["confidence"],
                    "result":          outcome,
                    "profit_loss":     profit,
                    "balance_after":   new_bal,
                    "pattern":         signal.get("pattern", "TREND_FOLLOWING"),
                    "sentiment_score": 0,
                    "groq_reasoning":  (
                        f"Score={signal.get('score', 0)}/12 | "
                        f"{signal.get('confirm', 'N/A')}"
                    ),
                    "mode": bot_state["mode"],
                })

                asyncio.run(send_trade_result({
                    "pair":          pair,
                    "direction":     direction,
                    "result":        outcome,
                    "profit_loss":   profit,
                    "balance_after": new_bal,
                    "entry_price":   result.get("entry_price", 0.0),
                    "exit_price":    result.get("exit_price", 0.0),
                }))

                logger.info(
                    f"{'✅ WIN' if outcome == 'WIN' else '❌ LOSS'} | "
                    f"{pair} {direction} | P&L: ${profit:.2f} | "
                    f"Balance: ${new_bal:.2f}"
                )

            except Exception as e:
                logger.error(f"❌ Result thread error: {e}")
                bot_state["trade_active"] = False

        threading.Thread(target=wait_for_result, daemon=True).start()
        return True

    except Exception as e:
        logger.error(f"❌ Execute trade error: {e}")
        bot_state["trade_active"] = False
        return False


# ─────────────────────────────────────────────────
# DAILY TASKS
# ─────────────────────────────────────────────────

def run_daily_tasks():
    now = datetime.now()
    if now.hour == 20 and now.minute < 2:
        logger.info("📊 Sending daily report...")
        asyncio.run(send_daily_summary())
        update_daily_performance()
    if should_run_backup():
        run_weekly_backup()


# ─────────────────────────────────────────────────
# MAIN TRADING LOOP — AO-2.5
# ─────────────────────────────────────────────────

def trading_loop():
    """
    AO-2.5 Main Loop — every 30 seconds:
    1. Phantom gate — hour check, cooldown, daily target
    2. Global risk rules
    3. Per-pair cooldowns
    4. Fetch 4 TFs, run confluence (trend-following engine)
    5. Score gate: 10+ → trade | 8-9 → phantom | <8 → skip
    6. Execute if all gates clear
    """
    logger.info("⚡ AO-2.5 Trading loop started!")
    logger.info("👻 PHANTOM MODE active")
    logger.info("📈 TREND FOLLOWING ENGINE active — EMA8/21 on 3m/5m/10m, 0.07% threshold")
    logger.info("🕯️ PULLBACK-RESUME entry — 1min RSI dip then resume")
    logger.info("🛑 RSI BRAKE active — skips if entry already extreme")
    bot_state["running"] = True
    update_status("running", True)

    while True:
        try:
            balance = get_balance()
            if balance == 0.0:
                logger.warning("⚠️ Balance = 0 — checking connection...")
                if not reconnect():
                    time.sleep(30)
                    continue
                balance = get_balance()
                if balance == 0.0:
                    time.sleep(30)
                    continue

            bot_state["balance"] = balance
            update_status("balance", balance)

            # ── Phantom gate ──────────────────────
            phantom_ok, phantom_reason = phantom.should_trade()
            if not phantom_ok:
                logger.info(f"👻 PHANTOM: {phantom_reason}")
                run_daily_tasks()
                time.sleep(LOOP_INTERVAL)
                continue

            # ── Global risk gate ──────────────────
            risk = can_trade(balance)
            if not risk["allowed"]:
                logger.info(f"⏸️ Trading paused: {risk['reason']}")
                run_daily_tasks()
                time.sleep(LOOP_INTERVAL)
                continue

            # ── Stuck trade flag reset ────────────
            if bot_state.get("trade_active"):
                last       = bot_state.get("last_trade", {})
                trade_time = last.get("time", "")
                if trade_time:
                    elapsed = (datetime.now() - datetime.fromisoformat(trade_time)).seconds
                    if elapsed > 600:
                        logger.warning("⚠️ Trade flag stuck — force resetting")
                        bot_state["trade_active"] = False
                    else:
                        logger.debug("⏳ Trade in progress — waiting...")
                        time.sleep(LOOP_INTERVAL)
                        continue

            # ── Scan pairs ────────────────────────
            trade_placed = False

            for pair in ACTIVE_PAIRS:
                pair_check = can_trade_pair(pair)
                if not pair_check["allowed"]:
                    logger.debug(f"⏱️ {pair}: {pair_check['reason']}")
                    continue

                logger.info(
                    f"🔍 Scanning {pair} | "
                    f"Balance: ${balance:.2f} | "
                    f"Trades today: {bot_state['trades_today']}/{config.MAX_DAILY_TRADES} | "
                    f"Phantom: {phantom.trade_count}/{phantom.daily_target}"
                )

                signal = process_signal(pair)

                if signal["action"] == "TRADE":
                    logger.info(
                        f"🚀 SIGNAL APPROVED: {pair} {signal['direction']} | "
                        f"Score={signal.get('score')}/12 | "
                        f"Expiry={signal.get('expiry')}min"
                    )
                    if execute_trade(signal):
                        trade_placed = True
                        break
                else:
                    logger.debug(f"⏭️ {pair}: {signal['reason']}")

            if not trade_placed:
                logger.debug("No signal this cycle.")

            run_daily_tasks()
            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            logger.info("⚡ Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Loop error: {e}")
            time.sleep(LOOP_INTERVAL)


# ─────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────

def startup():
    setup_logger(os.getenv("LOG_LEVEL", "INFO"))

    required = ["DERIV_API_TOKEN", "TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]
    missing  = [v for v in required if not os.getenv(v)]
    if missing:
        logger.critical(f"❌ Missing env vars: {', '.join(missing)}")
        return False

    logger.info("=" * 50)
    logger.info(f"⚡ {config.BOT_NAME} v{config.VERSION} STARTING")
    logger.info(f"   {config.MOTTO}")
    logger.info("=" * 50)

    start_keep_alive()

    if not connect():
        logger.critical("❌ Cannot connect to Deriv.com!")
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
    asyncio.run(send_startup_report(balance, mode))

    ps = phantom.get_status()

    logger.success("=" * 50)
    logger.success(f"✅ {config.BOT_NAME} v{config.VERSION} ONLINE!")
    logger.success(f"💰 Balance:            ${balance:.2f}")
    logger.success(f"📊 Mode:               {mode}")
    logger.success(f"📈 Strategy:           TREND FOLLOWING")
    logger.success(f"📐 TF Alignment:       3m / 5m / 10m EMA{config.EMA_FAST}/{config.EMA_SLOW}")
    logger.success(f"📏 EMA Threshold:      {config.EMA_DIFF_THRESHOLD*100:.2f}% minimum diff")
    logger.success(f"🎯 Live Score:         {config.MIN_SCORE}/12+ to trade real money")
    logger.success(f"👻 Phantom Score:      {config.PHANTOM_MIN_SCORE}-{config.MIN_SCORE-1}/12 shadow only")
    logger.success(f"🕯️  Entry:              Pullback-resume on 1min RSI")
    logger.success(f"🛑 RSI Brake:          Skip if RSI >{config.RSI_BRAKE_HIGH} (CALL) or <{config.RSI_BRAKE_LOW} (PUT)")
    logger.success(f"💱 Pairs:              {', '.join(ACTIVE_PAIRS)}")
    logger.success(f"⏱️  Expiry:             {config.EXPIRY_DEFAULT}min default / {config.EXPIRY_HIGH_CONF}min high-conf")
    logger.success(f"🔒 Daily target:       ${config.DAILY_PROFIT_TARGET}")
    logger.success(f"🛡️  Daily loss:         {config.DAILY_LOSS_LIMIT}%")
    logger.success(f"👻 Phantom target:     {ps['daily_target']} trades today")
    logger.success("=" * 50)

    return telegram_app


# ─────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app = startup()
        if not app:
            logger.critical("❌ Startup failed!")
            exit(1)

        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n⚡ APEX ORACLE shutting down...")
        asyncio.run(send_alert("⚡ <b>APEX ORACLE OFFLINE</b>\nBot stopped manually."))
        disconnect()
        logger.info("👋 Goodbye!")

    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        asyncio.run(send_shutdown_alert(str(e)))
        disconnect()