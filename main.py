# ⚡ APEX ORACLE — AO-2.0
# Main Orchestrator — REBUILT
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
# CHANGES FROM AO-1.0:
# - Groq AI gate REMOVED (was slow and not functional)
# - Candle patterns REMOVED (unreliable on synthetics)
# - Sentiment/news check REMOVED (irrelevant on synthetics)
# - Price manipulation guard REMOVED (no Yahoo data for synthetics)
# - Per-pair cooldown ADDED (120s between trades on same pair)
# - Daily profit target ADDED (lock gains at $30)
# - Expiry now 3min default, 5min for high score
# - V100 removed from pair list
# - Concurrent trade tracking ADDED
# - PHANTOM MODE ADDED (AO-2.0) — anti-detection engine
# - DAILY BIAS FILTER ADDED (AO-2.1) — trade with the trend
# - MTF BIAS FILTER UPGRADED (AO-2.2) — 1H + 15M + 5M confirmation
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
from core.phantom import phantom                    # ⚡ PHANTOM MODE

# Broker
from broker.deriv import (
    connect, disconnect, reconnect,
    get_balance, get_candles,
    get_current_price,
    place_trade, check_trade_result,
    is_connected,
)

# Management
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
from management.session import (
    get_optimal_expiry,
)

# Communication
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

# Data
from data.database import (
    log_trade, log_signal,
    update_daily_performance,
    get_today_stats,
)
from data.backup import run_weekly_backup, should_run_backup

# Server
from server.keep_alive import start_keep_alive, update_status

# Config
import config

# ─────────────────────────────────────────────────
# PAIR LIST — AO-2.0
# V100 removed. V25 and V10 lead (best oscillation)
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
# MTF BIAS ENGINE — AO-2.2
# Multi-Timeframe confirmation aligned to our
# 3-5 minute trade duration.
#
# 3 layers checked per signal:
#   1H  — overall day direction (big picture)
#   15M — medium term momentum (is move still going?)
#   5M  — immediate entry context (right now)
#
# Rule: at least 2 out of 3 timeframes must agree
# with the signal direction before a trade fires.
#
# 1H bias is cached all day (only fetched once).
# 15M and 5M are fetched fresh on every signal
# because they change frequently.
# ─────────────────────────────────────────────────

_bias_cache = {
    "date": None,
    "1h":   None,   # cached all day
}

def _calc_ema(closes: list, period: int) -> float:
    """Calculate EMA and return only the last value."""
    k = 2 / (period + 1)
    ema = closes[0]
    for price in closes[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def _get_bias_from_candles(candles: list, label: str) -> str:
    """
    Given a list of candles, return UP / DOWN / NEUTRAL
    based on EMA10 vs EMA21 relationship.
    """
    if not candles or len(candles) < 21:
        logger.warning(f"⚠️ MTF: not enough candles for {label} — NEUTRAL")
        return "NEUTRAL"

    closes = [
        float(c.get("close", c.get("Close", 0)))
        for c in candles
        if c.get("close", c.get("Close", 0)) != 0
    ]

    if len(closes) < 21:
        return "NEUTRAL"

    ema10 = _calc_ema(closes, 10)
    ema21 = _calc_ema(closes, 21)

    diff_pct = abs(ema10 - ema21) / ema21 * 100

    if diff_pct < 0.05:
        bias = "NEUTRAL"
    elif ema10 > ema21:
        bias = "UP"
    else:
        bias = "DOWN"

    logger.info(
        f"📊 MTF {label}: {bias} | "
        f"EMA10={ema10:.4f} EMA21={ema21:.4f} | "
        f"Diff={diff_pct:.3f}%"
    )
    return bias

def get_mtf_bias(pair: str, signal_direction: str) -> tuple[bool, str]:
    """
    Multi-Timeframe Bias Check — AO-2.2

    Checks 1H (cached), 15M (fresh), 5M (fresh).
    Requires at least 2 out of 3 to agree with
    the signal direction before approving.

    Returns:
        (approved: bool, reason: str)
    """
    try:
        today = datetime.now().date()

        # ── 1H bias — fetch once per day ─────────
        if _bias_cache["date"] != today or _bias_cache["1h"] is None:
            candles_1h = get_candles(pair, 60, 50)
            bias_1h = _get_bias_from_candles(candles_1h, "1H")
            _bias_cache["date"] = today
            _bias_cache["1h"]   = bias_1h
        else:
            bias_1h = _bias_cache["1h"]

        # ── 15M bias — fresh every signal ────────
        candles_15m = get_candles(pair, 15, 50)
        bias_15m = _get_bias_from_candles(candles_15m, "15M")

        # ── 5M bias — fresh every signal ─────────
        candles_5m = get_candles(pair, 5, 50)
        bias_5m = _get_bias_from_candles(candles_5m, "5M")

        # ── Count agreements ──────────────────────
        # Map signal direction to what we're looking for
        # CALL = we want UP biases
        # PUT  = we want DOWN biases
        target = "UP" if signal_direction == "CALL" else "DOWN"

        votes = {
            "1H":  bias_1h,
            "15M": bias_15m,
            "5M":  bias_5m,
        }

        agreements = sum(
            1 for tf, b in votes.items()
            if b == target
        )

        # NEUTRAL counts as a half-agreement — doesn't
        # block but doesn't fully support either
        neutrals = sum(
            1 for tf, b in votes.items()
            if b == "NEUTRAL"
        )

        # Need at least 2 agreements out of 3
        # A neutral on one TF with 1 agreement = not enough
        # A neutral on one TF with 2 agreements = approved
        approved = agreements >= 2

        summary = (
            f"1H={bias_1h} | 15M={bias_15m} | 5M={bias_5m} | "
            f"Agreements={agreements}/3 for {signal_direction}"
        )

        if approved:
            reason = f"✅ MTF approved ({agreements}/3 agree) | {summary}"
        else:
            reason = f"❌ MTF blocked ({agreements}/3 agree, need 2) | {summary}"

        logger.info(f"🔭 MTF Check: {reason}")
        return approved, reason

    except Exception as e:
        logger.error(f"❌ MTF bias error: {e}")
        # On error — default to approved so bot doesn't freeze
        return True, f"MTF error — defaulting to approved: {e}"


# ─────────────────────────────────────────────────
# SIGNAL PROCESSOR — AO-2.2
# ─────────────────────────────────────────────────

def process_signal(pair: str) -> dict:
    """
    AO-2.2 Signal Pipeline:
    1. Fetch 5min candles
    2. Run mean reversion scoring engine
    3. MTF bias check — 1H + 15M + 5M (2/3 must agree)
    4. Return decision
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

        if result["action"] != "TRADE":
            return {"action": "SKIP", "reason": result.get("reason", "No signal")}

        # ── MTF Bias Filter ───────────────────────
        # 1H + 15M + 5M must agree 2 out of 3
        signal_direction = result["direction"]
        mtf_approved, mtf_reason = get_mtf_bias(pair, signal_direction)

        if not mtf_approved:
            return {
                "action": "SKIP",
                "reason": f"MTF filter blocked: {mtf_reason}",
            }
        # ─────────────────────────────────────────

        score = result.get("score", 7)
        if score >= 10:
            expiry = config.EXPIRY_HIGH_CONF
        else:
            expiry = config.EXPIRY_DEFAULT

        return {
            "action":     "TRADE",
            "direction":  result["direction"],
            "confidence": result["confidence"],
            "score":      score,
            "pair":       pair,
            "stake_size": result["stake_size"],
            "pattern":    result.get("pattern", "MEAN_REVERSION"),
            "expiry":     expiry,
            "mtf":        mtf_reason,
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
    """Execute trade and spawn background thread to watch result"""
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
            error = trade_result.get("error", "unknown")
            logger.error(f"❌ Trade failed: {error}")
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

                # ⚡ PHANTOM — record trade completion
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
                    "groq_reasoning":  f"Score={signal.get('score', 0)}/12 | {signal.get('mtf', 'N/A')}",
                    "mode":            bot_state["mode"],
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
# MAIN TRADING LOOP — AO-2.2 + PHANTOM MODE
# ─────────────────────────────────────────────────

def trading_loop():
    """
    AO-2.2 Main Loop — every 30 seconds:
    1. Phantom Mode gate — hour check, cooldown, daily target
    2. Check global risk rules
    3. Check per-pair cooldowns
    4. Run scoring engine on each pair
    5. MTF bias filter — 1H + 15M + 5M (2/3 must agree)
    6. Execute only if all gates clear
    """
    logger.info("⚡ AO-2.2 Trading loop started!")
    logger.info("👻 PHANTOM MODE active — anti-detection enabled")
    logger.info("🔭 MTF BIAS FILTER active — 1H + 15M + 5M confirmation")
    bot_state["running"] = True
    update_status("running", True)

    while True:
        try:
            # ── Get balance ───────────────────────
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

            # ── PHANTOM GATE — first check ────────
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

            # ── Trade safety: stuck flag reset ────
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
                    f"Phantom: {phantom.trade_count}/{phantom.daily_target} | "
                    f"1H Bias: {_bias_cache.get('1h', 'UNKNOWN')}"
                )

                signal = process_signal(pair)

                if signal["action"] == "TRADE":
                    if pair == "V75" and signal.get("score", 0) < config.V75_MIN_SCORE:
                        logger.info(
                            f"⏭️ V75 score {signal.get('score')}/12 "
                            f"< {config.V75_MIN_SCORE} — skipping"
                        )
                        continue

                    logger.info(
                        f"🚀 SIGNAL APPROVED: {pair} {signal['direction']} | "
                        f"Score={signal.get('score')}/12 | "
                        f"Expiry={signal.get('expiry')}min | "
                        f"MTF={signal.get('mtf', 'N/A')}"
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

    # ⚡ Phantom status
    ps = phantom.get_status()

    # 🔭 Pre-fetch 1H bias on startup
    candles_1h = get_candles("V10", 60, 50)
    startup_bias = _get_bias_from_candles(candles_1h, "1H")
    _bias_cache["date"] = datetime.now().date()
    _bias_cache["1h"]   = startup_bias

    logger.success("=" * 50)
    logger.success(f"✅ {config.BOT_NAME} v{config.VERSION} ONLINE!")
    logger.success(f"💰 Balance:        ${balance:.2f}")
    logger.success(f"📊 Mode:           {mode}")
    logger.success(f"🎯 Min Score:      {config.MIN_SCORE}/12 to trade")
    logger.success(f"💱 Pairs:          {', '.join(ACTIVE_PAIRS)}")
    logger.success(f"⏱️  Expiry:         {config.EXPIRY_DEFAULT}min / {config.EXPIRY_HIGH_CONF}min")
    logger.success(f"🔒 Daily target:   ${config.DAILY_PROFIT_TARGET} then STOP")
    logger.success(f"🛡️  Daily loss:     {config.DAILY_LOSS_LIMIT}% then STOP")
    logger.success(f"👻 Phantom target: {ps['daily_target']} trades today")
    logger.success(f"👻 Phantom bursts: hours {ps['burst_hours']}")
    logger.success(f"🔭 MTF 1H bias:    {startup_bias} — 15M + 5M checked per signal")
    logger.success(f"🚫 Groq AI:        DISABLED (AO-2.0)")
    logger.success(f"🚫 V100:           EXCLUDED (too noisy)")
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