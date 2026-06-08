# ⚡ APEX ORACLE — AO-1.0
# Risk Management System
# Kelly Criterion stake sizing + Hard stop rules
# Protects capital at all times
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
from datetime import datetime, timedelta
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# RISK SETTINGS
# ─────────────────────────────────────────────────

STAKE_PERCENT          = float(os.getenv("STAKE_PERCENT", 1.5))
MAX_DAILY_TRADES       = int(os.getenv("MAX_DAILY_TRADES", 15))
MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
DAILY_LOSS_LIMIT       = float(os.getenv("DAILY_LOSS_LIMIT", 5))
WEEKLY_LOSS_LIMIT      = 10.0
KELLY_SAFETY_FACTOR    = 0.25
WIN_STREAK_REDUCE      = 5
PAYOUT_PERCENT         = 0.87    # IQ Option typical payout


# ─────────────────────────────────────────────────
# RISK STATE TRACKER
# ─────────────────────────────────────────────────

risk_state = {
    "consecutive_losses":  0,
    "consecutive_wins":    0,
    "trades_today":        0,
    "daily_pnl":           0.0,
    "weekly_pnl":          0.0,
    "starting_balance":    0.0,
    "paused_until":        None,
    "paused_reason":       None,
    "daily_reset_date":    None,
    "weekly_reset_date":   None,
    "is_shutdown":         False,
}


# ─────────────────────────────────────────────────
# KELLY CRITERION STAKE CALCULATOR
# ─────────────────────────────────────────────────

def calculate_kelly_stake(
    balance:  float,
    win_rate: float = 0.65,
    payout:   float = PAYOUT_PERCENT,
) -> float:
    """
    Calculate optimal stake using Kelly Criterion

    Formula: Kelly = (Win% - Loss%) / Payout
    We use 25% of Kelly for safety

    Example at 65% win rate:
    Full Kelly = 6.25% of balance
    Our stake  = 1.56% of balance
    """
    try:
        if balance <= 0:
            return 0.0

        win_rate  = min(max(win_rate, 0.1), 0.95)
        loss_rate = 1 - win_rate

        # Kelly formula
        kelly = (win_rate - loss_rate) / payout

        # Apply safety factor (25% of full Kelly)
        safe_kelly = kelly * KELLY_SAFETY_FACTOR

        # Calculate stake amount
        stake = balance * safe_kelly

        # Minimum $1, maximum 2% of balance
        min_stake = max(1.0, balance * 0.005)
        max_stake = balance * 0.02

        stake = max(min_stake, min(stake, max_stake))

        return round(stake, 2)

    except Exception as e:
        logger.error(f"❌ Kelly calculation error: {e}")
        return round(balance * 0.01, 2)


def calculate_stake(
    balance:     float,
    confidence:  float,
    stake_size:  str = "FULL",
    win_rate:    float = 0.65,
) -> float:
    """
    Calculate final stake based on confidence and size

    stake_size:
    FULL = full Kelly stake
    HALF = 50% of Kelly stake
    SKIP = 0 (don't trade)
    """
    try:
        if stake_size == "SKIP" or balance <= 0:
            return 0.0

        base_stake = calculate_kelly_stake(balance, win_rate)

        # Adjust for confidence
        if confidence >= 90:
            multiplier = 1.0      # Full stake
        elif confidence >= 80:
            multiplier = 0.8      # 80% of stake
        elif confidence >= 75:
            multiplier = 0.6      # 60% of stake
        else:
            multiplier = 0.0      # Don't trade

        # Apply stake size
        if stake_size == "HALF":
            multiplier *= 0.5

        stake = base_stake * multiplier

        # Never risk more than 2% per trade
        max_allowed = balance * 0.02
        stake = min(stake, max_allowed)

        # Minimum $1
        stake = max(stake, 1.0) if stake > 0 else 0.0

        return round(stake, 2)

    except Exception as e:
        logger.error(f"❌ Stake calculation error: {e}")
        return 0.0


# ─────────────────────────────────────────────────
# DAILY / WEEKLY RESET
# ─────────────────────────────────────────────────

def check_and_reset_daily():
    """Reset daily counters at midnight"""
    global risk_state
    today = datetime.now().date()

    if risk_state["daily_reset_date"] != today:
        risk_state["trades_today"]     = 0
        risk_state["daily_pnl"]        = 0.0
        risk_state["daily_reset_date"] = today
        logger.info("🔄 Daily risk counters reset")


def check_and_reset_weekly():
    """Reset weekly counters on Monday"""
    global risk_state
    today     = datetime.now().date()
    monday    = today - timedelta(days=today.weekday())

    if risk_state["weekly_reset_date"] != monday:
        risk_state["weekly_pnl"]        = 0.0
        risk_state["weekly_reset_date"] = monday
        if risk_state["is_shutdown"]:
            risk_state["is_shutdown"] = False
            logger.info("🔄 Weekly shutdown lifted — new week started!")
        logger.info("🔄 Weekly risk counters reset")


# ─────────────────────────────────────────────────
# HARD STOP RULES
# ─────────────────────────────────────────────────

def can_trade(balance: float) -> dict:
    """
    Master check — can we trade right now?

    Checks all hard stop rules:
    1. Emergency shutdown
    2. Paused (after consecutive losses)
    3. Daily trade limit
    4. Daily loss limit
    5. Weekly loss limit
    6. Minimum balance

    Returns:
    {
        "allowed":  True/False,
        "reason":   "explanation"
    }
    """
    global risk_state

    check_and_reset_daily()
    check_and_reset_weekly()

    # ── Check 1: Emergency shutdown ───────────────
    if risk_state["is_shutdown"]:
        return {
            "allowed": False,
            "reason":  "🚨 Weekly loss limit hit — shutdown until Monday"
        }

    # ── Check 2: Paused ───────────────────────────
    if risk_state["paused_until"]:
        if datetime.now() < risk_state["paused_until"]:
            remaining = (
                risk_state["paused_until"] - datetime.now()
            ).seconds // 60
            return {
                "allowed": False,
                "reason":  f"⏸️ Paused for {remaining} more minutes — {risk_state['paused_reason']}"
            }
        else:
            risk_state["paused_until"] = None
            risk_state["paused_reason"] = None
            logger.info("▶️ Pause lifted — resuming trading")

    # ── Check 3: Daily trade limit ────────────────
    if risk_state["trades_today"] >= MAX_DAILY_TRADES:
        return {
            "allowed": False,
            "reason":  f"📊 Daily trade limit reached ({MAX_DAILY_TRADES} trades)"
        }

    # ── Check 4: Daily loss limit ─────────────────
    if risk_state["starting_balance"] > 0:
        daily_loss_pct = abs(
            risk_state["daily_pnl"] / risk_state["starting_balance"] * 100
        )
        if risk_state["daily_pnl"] < 0 and daily_loss_pct >= DAILY_LOSS_LIMIT:
            return {
                "allowed": False,
                "reason":  f"💸 Daily loss limit hit ({DAILY_LOSS_LIMIT}%) — resuming tomorrow"
            }

    # ── Check 5: Weekly loss limit ────────────────
    if risk_state["starting_balance"] > 0:
        weekly_loss_pct = abs(
            risk_state["weekly_pnl"] / risk_state["starting_balance"] * 100
        )
        if risk_state["weekly_pnl"] < 0 and weekly_loss_pct >= WEEKLY_LOSS_LIMIT:
            risk_state["is_shutdown"] = True
            return {
                "allowed": False,
                "reason":  "🚨 Weekly loss limit hit — shutdown until Monday"
            }

    # ── Check 6: Minimum balance ──────────────────
    if balance < 1.0:
        return {
            "allowed": False,
            "reason":  "💰 Balance too low to trade"
        }

    return {"allowed": True, "reason": "✅ All checks passed"}


def update_after_trade(result: str, pnl: float):
    """
    Update risk state after every trade result

    result = "WIN" or "LOSS"
    pnl    = profit or loss amount
    """
    global risk_state

    risk_state["trades_today"] += 1
    risk_state["daily_pnl"]   += pnl
    risk_state["weekly_pnl"]  += pnl

    if result == "WIN":
        risk_state["consecutive_losses"] = 0
        risk_state["consecutive_wins"]  += 1

        # Win streak protection
        if risk_state["consecutive_wins"] >= WIN_STREAK_REDUCE:
            logger.info(
                f"🏆 {WIN_STREAK_REDUCE} consecutive wins! "
                f"Reducing stake size by 20% to protect profits"
            )

    elif result == "LOSS":
        risk_state["consecutive_wins"]   = 0
        risk_state["consecutive_losses"] += 1

        # Consecutive loss pause
        if risk_state["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
            pause_until = datetime.now() + timedelta(hours=1)
            risk_state["paused_until"]  = pause_until
            risk_state["paused_reason"] = (
                f"{MAX_CONSECUTIVE_LOSSES} consecutive losses"
            )
            risk_state["consecutive_losses"] = 0
            logger.warning(
                f"⏸️ {MAX_CONSECUTIVE_LOSSES} consecutive losses! "
                f"Pausing for 1 hour..."
            )

    logger.info(
        f"📊 Risk State: "
        f"Trades={risk_state['trades_today']} | "
        f"Daily PnL=${risk_state['daily_pnl']:.2f} | "
        f"Streak: {risk_state['consecutive_wins']}W "
        f"{risk_state['consecutive_losses']}L"
    )


def set_starting_balance(balance: float):
    """Set starting balance for loss calculations"""
    global risk_state
    if risk_state["starting_balance"] == 0:
        risk_state["starting_balance"] = balance
        logger.info(f"💰 Starting balance set: ${balance:.2f}")


def get_risk_state() -> dict:
    """Get current risk state for reporting"""
    return risk_state.copy()


def pause_trading(reason: str, minutes: int = 60):
    """Manually pause trading"""
    global risk_state
    risk_state["paused_until"]  = datetime.now() + timedelta(minutes=minutes)
    risk_state["paused_reason"] = reason
    logger.warning(f"⏸️ Trading paused for {minutes} mins: {reason}")


def resume_trading():
    """Manually resume trading"""
    global risk_state
    risk_state["paused_until"]  = None
    risk_state["paused_reason"] = None
    logger.info("▶️ Trading resumed manually")


def emergency_shutdown(reason: str):
    """Emergency shutdown"""
    global risk_state
    risk_state["is_shutdown"] = True
    logger.critical(f"🚨 EMERGENCY SHUTDOWN: {reason}")


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Risk Management Test")
    print("─" * 45)

    balance = 10000.00
    set_starting_balance(balance)

    print(f"\n💰 Balance: ${balance}")
    print(f"\n--- Kelly Stake Calculation ---")
    stake = calculate_kelly_stake(balance, win_rate=0.65)
    print(f"Kelly Stake (65% win rate): ${stake}")

    stake_full = calculate_stake(balance, 88, "FULL", 0.65)
    stake_half = calculate_stake(balance, 76, "HALF", 0.65)
    print(f"Full stake (88% conf): ${stake_full}")
    print(f"Half stake (76% conf): ${stake_half}")

    print(f"\n--- Can Trade Check ---")
    check = can_trade(balance)
    print(f"Allowed: {check['allowed']}")
    print(f"Reason:  {check['reason']}")

    print(f"\n--- Simulating 3 losses ---")
    for i in range(3):
        update_after_trade("LOSS", -stake_full)
        print(f"Loss {i+1}: Daily PnL = ${risk_state['daily_pnl']:.2f}")

    check = can_trade(balance)
    print(f"\nCan trade after 3 losses: {check['allowed']}")
    print(f"Reason: {check['reason']}")