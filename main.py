# ⚡ APEX ORACLE — AO-2.4
# Main Orchestrator — REBUILT
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
# CHANGES FROM AO-2.3:
# - MTF EMA trend filter REPLACED with 1M reversal
#   confirmation — compatible with mean reversion
# - Score gate enforced: 9+ = live, 7-8 = phantom
# - PHANTOM action from confluence now shadow-logged
#   automatically without firing a real trade
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
# 1M REVERSAL CONFIRMATION ENGINE — AO-2.4
#
# PURPOSE: Confirm the mean reversion has already
# started on the fastest timeframe before committing
# real money on a 3-minute trade.
#
# WHY NOT EMA TREND AGREEMENT:
# Our confluence engine is MEAN REVERSION — it fires
# when price is at an extreme and just flipped.
# Requiring 15M/5M EMAs to agree with the reversal
# direction is impossible — the trend that CAUSED
# the extreme hasn't reversed on those TFs yet.
# That filter was blocking our best setups.
#
# NEW RULE (AO-2.4):
# For a PUT signal — confirm on 1M that either:
#   (a) EMA10 has crossed below EMA21, OR
#   (b) Last 2 candles are both bearish (down momentum)
# For a CALL signal — mirror logic (bullish).
#
# This is REVERSAL CONFIRMATION, not trend agreement.
# It only asks: "has the turn already started?"
# ─────────────────────────────────────────────────

def _calc_ema(closes: list, period: int) -> float:
    """EMA from list of closes, returns last value."""
    k   = 2 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = price * k + ema * (1 - k)
    return ema


def get_reversal_confirmation(pair: str, signal_direction: str) -> tuple:
    """
    AO-2.4 Reversal Confirmation — 1M timeframe.

    For PUT: EMA10 < EMA21 on 1M, OR last 2 closes falling.
    For CALL: EMA10 > EMA21 on 1M, OR last 2 closes rising.

    One of the two conditions is enough — we don't need both.
    This keeps it sensitive enough to catch early reversals.

    Returns: (confirmed: bool, reason: str)
    """
    try:
        candles_1m = get_candles(pair, 1, 30)

        if not candles_1m or len(candles_1m) < 5:
            # Not enough 1M data — default approve so bot doesn't freeze
            logger.warning(f"⚠️ 1M confirm: not enough candles for {pair} — defaulting approved")
            return True, "1M confirm: insufficient data — defaulted approved"

        closes = [
            float(c.get("close", c.get("Close", 0)))
            for c in candles_1m
            if c.get("close", c.get("Close", 0)) != 0
        ]

        if len(closes) < 5:
            return True, "1M confirm: insufficient closes — defaulted approved"

        ema10 = _calc_ema(closes, 10) if len(closes) >= 10 else None
        ema21 = _calc_ema(closes, 21) if len(closes) >= 21 else None

        last_close  = closes[-1]
        prev_close  = closes[-2]
        prev2_close = closes[-3]

        if signal_direction == "PUT":
            # Condition A: EMA10 crossed below EMA21 on 1M
            ema_crossed_down = (ema10 is not None and ema21 is not None and ema10 < ema21)
            # Condition B: Last 2 candles both bearish
            momentum_down = (last_close < prev_close) and (prev_close < prev2_close)

            confirmed = ema_crossed_down or momentum_down

            reason = (
                f"1M PUT confirm | "
                f"EMA10={'%.4f' % ema10 if ema10 else 'N/A'} "
                f"EMA21={'%.4f' % ema21 if ema21 else 'N/A'} | "
                f"EMA_cross_down={ema_crossed_down} | "
                f"Momentum_down={momentum_down} | "
                f"{'✅ CONFIRMED' if confirmed else '❌ NOT confirmed'}"
            )

        else:  # CALL
            # Condition A: EMA10 crossed above EMA21 on 1M
            ema_crossed_up = (ema10 is not None and ema21 is not None and ema10 > ema21)
            # Condition B: Last 2 candles both bullish
            momentum_up = (last_close > prev_close) and (prev_close > prev2_close)

            confirmed = ema_crossed_up or momentum_up

            reason = (
                f"1M CALL confirm | "
                f"EMA10={'%.4f' % ema10 if ema10 else 'N/A'} "
                f"EMA21={'%.4f' % ema21 if ema21 else 'N/A'} | "
                f"EMA_cross_up={ema_crossed_up} | "
                f"Momentum_up={momentum_up} | "
                f"{'✅ CONFIRMED' if confirmed else '❌ NOT confirmed'}"
            )

        logger.info(f"🕯️ {reason}")
        return confirmed, reason

    except Exception as e:
        logger.error(f"❌ 1M reversal confirm error: {e}")
        return True, f"1M confirm error — defaulted approved: {e}"


# ─────────────────────────────────────────────────
# SIGNAL PROCESSOR — AO-2.4
# ─────────────────────────────────────────────────

def process_signal(pair: str) -> dict:
    """
    AO-2.4 Signal Pipeline:
    1. Fetch 5min candles
    2. Run mean reversion scoring engine
    3. If score 7-8 → phantom log, no real trade
    4. If score 9+ → 1M reversal confirmation check
    5. Return decision
    """
    try:
        candles = get_candles(pair, 5, 100)
        if not candles or len(candles) < 30:
            return {"action": "SKIP", "reason": "Not enough candle data"}

        result = calculate_confluence(candles, {}, pair)

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

        # ── Hard skip ─────────────────────────────
        if result["action"] == "SKIP":
            return {"action": "SKIP", "reason": result.get("reason", "No signal")}

        # ── Phantom only (score 7-8) ───────────────
        # Shadow log it but do not fire real trade
        if result["action"] == "PHANTOM":
            logger.info(
                f"👻 PHANTOM LOG: {pair} {result['direction']} | "
                f"Score={result['score']}/12 — no real trade"
            )
            return {
                "action": "SKIP",
                "reason": f"Score {result['score']}/12 — phantom only, need 9+ for live",
            }

        # ── Score 9+ — run 1M reversal confirmation
        signal_direction = result["direction"]
        confirmed, confirm_reason = get_reversal_confirmation(pair, signal_direction)

        if not confirmed:
            logger.info(
                f"🕯️ 1M confirm BLOCKED: {pair} {signal_direction} | {confirm_reason}"
            )
            return {
                "action": "SKIP",
                "reason": f"1M reversal not confirmed: {confirm_reason}",
            }

        score = result.get("score", 9)
        expiry = config.EXPIRY_HIGH_CONF if score >= 10 else config.EXPIRY_DEFAULT

        return {
            "action":     "TRADE",
            "direction":  result["direction"],
            "confidence": result["confidence"],
            "score":      score,
            "pair":       pair,
            "stake_size": result["stake_size"],
            "pattern":    result.get("pattern", "MEAN_REVERSION"),
            "expiry":     expiry,
            "confirm":    confirm_reason,
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
            "pattern":     signal.get("pattern", "MEAN_REVERSION"),
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
                    "pattern":         signal.get("pattern", "MEAN_REVERSION"),
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
# MAIN TRADING LOOP — AO-2.4
# ─────────────────────────────────────────────────

def trading_loop():
    """
    AO-2.4 Main Loop — every 30 seconds:
    1. Phantom gate — hour check, cooldown, daily target
    2. Global risk rules
    3. Per-pair cooldowns
    4. Confluence scoring (5M candles)
    5. Score gate: 9+ → 1M reversal confirm → trade
                  7-8 → phantom log only
                  <7  → skip
    6. Execute if all gates clear
    """
    logger.info("⚡ AO-2.4 Trading loop started!")
    logger.info("👻 PHANTOM MODE active")
    logger.info("🕯️ 1M REVERSAL CONFIRMATION active — replaces EMA trend filter")
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
    logger.success(f"💰 Balance:          ${balance:.2f}")
    logger.success(f"📊 Mode:             {mode}")
    logger.success(f"🎯 Live Score:       {config.MIN_SCORE}/12+ to trade real money")
    logger.success(f"👻 Phantom Score:    {config.PHANTOM_MIN_SCORE}-{config.MIN_SCORE - 1}/12 shadow only")
    logger.success(f"💱 Pairs:            {', '.join(ACTIVE_PAIRS)}")
    logger.success(f"⏱️  Expiry:           {config.EXPIRY_DEFAULT}min / {config.EXPIRY_HIGH_CONF}min")
    logger.success(f"🔒 Daily target:     ${config.DAILY_PROFIT_TARGET}")
    logger.success(f"🛡️  Daily loss:       {config.DAILY_LOSS_LIMIT}%")
    logger.success(f"👻 Phantom target:   {ps['daily_target']} trades today")
    logger.success(f"🕯️  1M Confirm:       EMA cross OR 2-candle momentum")
    logger.success(f"🚫 EMA trend filter: REMOVED — was killing reversals")
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