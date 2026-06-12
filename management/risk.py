# ⚡ APEX ORACLE — AO-2.0
# Risk Management System — REBUILT
# Capital protection is JOB ONE.
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
#
# NEW RULES:
# - Max 10 trades per day (was 15, disabled)
# - Daily profit target 10% of balance → stop and LOCK gains
# - Daily loss limit 5% of balance → stop for the day
# - 3 consecutive losses → 30 min cooldown (was 1 hour)
# - Per-pair cooldown: 120s between trades on same pair
# - Max 2 trades open simultaneously
# - Stake: flat 1.5% of balance, never more
# ─────────────────────────────────────────────────

import os
import time
from datetime import datetime, timedelta
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# SETTINGS — Edit these in Render Environment panel
# ─────────────────────────────────────────────────

MAX_DAILY_TRADES            = int(os.getenv("MAX_DAILY_TRADES", 10))
DAILY_LOSS_LIMIT_PCT        = float(os.getenv("DAILY_LOSS_LIMIT", 5.0))
DAILY_PROFIT_TARGET_PCT     = float(os.getenv("DAILY_PROFIT_TARGET_PCT", 10.0))   # ✅ FIXED: reads correct env var
MAX_CONSECUTIVE_LOSSES      = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
CONSEC_LOSS_PAUSE_MINS      = 30         # minutes to pause after 3 consec losses
WEEKLY_LOSS_LIMIT_PCT       = 10.0       # % of starting balance
MAX_CONCURRENT_TRADES       = 2          # max trades open at same time
PAIR_COOLDOWN_SECONDS       = 120        # seconds between trades on same pair
STAKE_PCT                   = float(os.getenv("STAKE_PERCENT", 1.0))   # % of balance
MIN_STAKE                   = 1.0        # minimum $1 per trade
MAX_STAKE_PCT               = 2.0        # never risk more than 2% per trade
PAYOUT_RATIO                = 0.87       # Deriv typical binary payout

# ─────────────────────────────────────────────────
# RISK STATE
# ─────────────────────────────────────────────────

risk_state = {
    "consecutive_losses":  0,
    "consecutive_wins":    0,
    "trades_today":        0,
    "open_trades":         0,
    "daily_pnl":           0.0,
    "weekly_pnl":          0.0,
    "starting_balance":    0.0,
    "paused_until":        None,
    "paused_reason":       None,
    "daily_reset_date":    None,
    "weekly_reset_date":   None,
    "is_shutdown":         False,
    "daily_target_hit":    False,
    "pair_last_trade":     {},
}


# ─────────────────────────────────────────────────
# HELPER — compute dollar targets from balance
# ─────────────────────────────────────────────────

def _daily_profit_target_usd() -> float:
    """10% of starting balance in dollars. Falls back to $30 if balance not set yet."""
    bal = risk_state["starting_balance"]
    if bal > 0:
        return round(bal * (DAILY_PROFIT_TARGET_PCT / 100), 2)
    return 30.0   # safe fallback before balance is known


def _daily_loss_limit_usd() -> float:
    """5% of starting balance in dollars."""
    bal = risk_state["starting_balance"]
    if bal > 0:
        return round(bal * (DAILY_LOSS_LIMIT_PCT / 100), 2)
    return 0.0


# ─────────────────────────────────────────────────
# STAKE CALCULATOR
# ─────────────────────────────────────────────────

def calculate_stake(
    balance:    float,
    confidence: float,
    stake_size: str = "FULL",
    win_rate:   float = 0.65,
) -> float:
    try:
        if stake_size == "SKIP" or balance <= 0:
            return 0.0

        base_stake = balance * (STAKE_PCT / 100)

        if stake_size == "HALF":
            base_stake *= 0.5

        max_allowed = balance * (MAX_STAKE_PCT / 100)
        stake = min(base_stake, max_allowed)
        stake = max(stake, MIN_STAKE)

        return round(stake, 2)

    except Exception as e:
        logger.error(f"❌ Stake calculation error: {e}")
        return 0.0


# ─────────────────────────────────────────────────
# DAILY / WEEKLY RESETS
# ─────────────────────────────────────────────────

def check_and_reset_daily():
    global risk_state
    today = datetime.now().date()
    if risk_state["daily_reset_date"] != today:
        risk_state["trades_today"]      = 0
        risk_state["daily_pnl"]         = 0.0
        risk_state["daily_reset_date"]  = today
        risk_state["daily_target_hit"]  = False
        risk_state["pair_last_trade"]   = {}
        logger.info("🔄 Daily risk counters reset")


def check_and_reset_weekly():
    global risk_state
    today  = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    if risk_state["weekly_reset_date"] != monday:
        risk_state["weekly_pnl"]        = 0.0
        risk_state["weekly_reset_date"] = monday
        if risk_state["is_shutdown"]:
            risk_state["is_shutdown"] = False
            logger.info("🔄 Weekly shutdown lifted — new week started!")
        logger.info("🔄 Weekly risk counters reset")


# ─────────────────────────────────────────────────
# CAN TRADE — Master gate
# ─────────────────────────────────────────────────

def can_trade(balance: float) -> dict:
    global risk_state

    check_and_reset_daily()
    check_and_reset_weekly()

    profit_target_usd = _daily_profit_target_usd()
    loss_limit_usd    = _daily_loss_limit_usd()

    # 1. Emergency shutdown
    if risk_state["is_shutdown"]:
        return {"allowed": False, "reason": "🚨 Weekly loss limit hit — shutdown until Monday"}

    # 2. Paused (consecutive losses)
    if risk_state["paused_until"]:
        if datetime.now() < risk_state["paused_until"]:
            mins = int((risk_state["paused_until"] - datetime.now()).seconds / 60)
            return {
                "allowed": False,
                "reason":  f"⏸️ Cooling down — {mins} min left ({risk_state['paused_reason']})"
            }
        else:
            risk_state["paused_until"]  = None
            risk_state["paused_reason"] = None
            logger.info("▶️ Cooldown lifted — resuming trading")

    # 3. Daily profit target — percentage-based ✅
    if risk_state["daily_target_hit"]:
        return {
            "allowed": False,
            "reason":  f"🎯 Daily profit target ${profit_target_usd:.2f} ({DAILY_PROFIT_TARGET_PCT:.0f}%) hit — gains locked!"
        }

    if risk_state["daily_pnl"] >= profit_target_usd:
        risk_state["daily_target_hit"] = True
        logger.success(
            f"🎯 Daily profit target ${profit_target_usd:.2f} "
            f"({DAILY_PROFIT_TARGET_PCT:.0f}% of ${risk_state['starting_balance']:.2f}) reached — stopping for today!"
        )
        return {
            "allowed": False,
            "reason":  f"🎯 Daily profit target hit — gains locked!"
        }

    # 4. Daily loss limit — percentage-based ✅
    if loss_limit_usd > 0 and risk_state["daily_pnl"] <= -loss_limit_usd:
        return {
            "allowed": False,
            "reason":  f"💸 Daily loss limit ${loss_limit_usd:.2f} ({DAILY_LOSS_LIMIT_PCT:.0f}%) hit — resuming tomorrow"
        }

    # 5. Weekly loss limit → shutdown
    if risk_state["starting_balance"] > 0:
        weekly_loss_pct = abs(risk_state["weekly_pnl"] / risk_state["starting_balance"] * 100)
        if risk_state["weekly_pnl"] < 0 and weekly_loss_pct >= WEEKLY_LOSS_LIMIT_PCT:
            risk_state["is_shutdown"] = True
            return {"allowed": False, "reason": "🚨 Weekly loss limit hit — shutdown until Monday"}

    # 6. Daily trade cap
    if risk_state["trades_today"] >= MAX_DAILY_TRADES:
        return {
            "allowed": False,
            "reason":  f"📊 Daily trade cap ({MAX_DAILY_TRADES}) reached — done for today"
        }

    # 7. Too many concurrent open trades
    if risk_state["open_trades"] >= MAX_CONCURRENT_TRADES:
        return {
            "allowed": False,
            "reason":  f"⏳ {risk_state['open_trades']} trades already open — waiting"
        }

    # 8. Minimum balance
    if balance < MIN_STAKE:
        return {"allowed": False, "reason": "💰 Balance too low to trade"}

    return {"allowed": True, "reason": "✅ All checks passed"}


def can_trade_pair(pair: str) -> dict:
    global risk_state
    last = risk_state["pair_last_trade"].get(pair, 0)
    elapsed = time.time() - last
    if elapsed < PAIR_COOLDOWN_SECONDS:
        remaining = int(PAIR_COOLDOWN_SECONDS - elapsed)
        return {
            "allowed": False,
            "reason":  f"⏱️ {pair} cooldown — {remaining}s remaining"
        }
    return {"allowed": True, "reason": "ok"}


# ─────────────────────────────────────────────────
# UPDATE AFTER TRADE
# ─────────────────────────────────────────────────

def update_after_trade(result: str, pnl: float):
    global risk_state

    risk_state["trades_today"] += 1
    risk_state["daily_pnl"]   += pnl
    risk_state["weekly_pnl"]  += pnl

    if risk_state["open_trades"] > 0:
        risk_state["open_trades"] -= 1

    if result == "WIN":
        risk_state["consecutive_losses"] = 0
        risk_state["consecutive_wins"]  += 1

    elif result == "LOSS":
        risk_state["consecutive_wins"]   = 0
        risk_state["consecutive_losses"] += 1

        if risk_state["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
            pause_until = datetime.now() + timedelta(minutes=CONSEC_LOSS_PAUSE_MINS)
            risk_state["paused_until"]       = pause_until
            risk_state["paused_reason"]      = f"{MAX_CONSECUTIVE_LOSSES} consecutive losses"
            risk_state["consecutive_losses"] = 0
            logger.warning(
                f"⏸️ {MAX_CONSECUTIVE_LOSSES} consecutive losses — "
                f"pausing {CONSEC_LOSS_PAUSE_MINS} minutes"
            )

    logger.info(
        f"📊 Risk | Trades={risk_state['trades_today']}/{MAX_DAILY_TRADES} | "
        f"Daily P&L=${risk_state['daily_pnl']:.2f} | "
        f"Streak: {risk_state['consecutive_wins']}W {risk_state['consecutive_losses']}L"
    )


def register_trade_open(pair: str):
    global risk_state
    risk_state["open_trades"] += 1
    risk_state["pair_last_trade"][pair] = time.time()


# ─────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────

def set_starting_balance(balance: float):
    global risk_state
    if risk_state["starting_balance"] == 0:
        risk_state["starting_balance"] = balance
        profit_target = _daily_profit_target_usd()
        loss_limit    = _daily_loss_limit_usd()
        logger.info(
            f"💰 Starting balance: ${balance:.2f} | "
            f"Profit target: ${profit_target:.2f} ({DAILY_PROFIT_TARGET_PCT:.0f}%) | "
            f"Loss limit: ${loss_limit:.2f} ({DAILY_LOSS_LIMIT_PCT:.0f}%)"
        )


def get_risk_state() -> dict:
    return risk_state.copy()


def pause_trading(reason: str, minutes: int = 60):
    global risk_state
    risk_state["paused_until"]  = datetime.now() + timedelta(minutes=minutes)
    risk_state["paused_reason"] = reason
    logger.warning(f"⏸️ Trading paused {minutes}min: {reason}")


def resume_trading():
    global risk_state
    risk_state["paused_until"]  = None
    risk_state["paused_reason"] = None
    logger.info("▶️ Trading resumed")


def emergency_shutdown(reason: str):
    global risk_state
    risk_state["is_shutdown"] = True
    logger.critical(f"🚨 EMERGENCY SHUTDOWN: {reason}")


def calculate_kelly_stake(balance: float, win_rate: float = 0.65, payout: float = PAYOUT_RATIO) -> float:
    return calculate_stake(balance, 80, "FULL", win_rate)