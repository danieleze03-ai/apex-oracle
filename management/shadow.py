# ⚡ APEX ORACLE — AO-1.0
# Shadow Trading System
# Mirrors every LIVE trade on DEMO simultaneously
# Compares results to detect broker manipulation
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────
# SHADOW STATE
# ─────────────────────────────────────────────────

shadow_state = {
    "enabled":         True,
    "live_trades":     [],
    "shadow_trades":   [],
    "live_wins":       0,
    "live_losses":     0,
    "shadow_wins":     0,
    "shadow_losses":   0,
    "manipulation_alerts": 0,
    "last_comparison": None,
}


# ─────────────────────────────────────────────────
# SHADOW TRADE EXECUTOR
# ─────────────────────────────────────────────────

def place_shadow_trade(
    iq_instance,
    pair:      str,
    direction: str,
    stake:     float,
    expiry:    int,
    live_id:   int,
) -> dict:
    """
    Place shadow trade on DEMO account
    Mirrors a live trade exactly
    """
    try:
        if not shadow_state["enabled"]:
            return {"success": False, "reason": "Shadow mode disabled"}

        logger.debug(
            f"👥 Shadow trade: {pair} {direction} "
            f"${stake} {expiry}min"
        )

        # Switch to PRACTICE mode temporarily
        iq_instance.change_balance("PRACTICE")

        # Place shadow trade
        status, shadow_id = iq_instance.buy(
            stake, pair, direction.lower(), expiry
        )

        # Switch back to original mode
        original_mode = os.getenv("TRADING_MODE", "PRACTICE")
        iq_instance.change_balance(original_mode)

        if status:
            shadow_trade = {
                "shadow_id":   shadow_id,
                "live_id":     live_id,
                "pair":        pair,
                "direction":   direction,
                "stake":       stake,
                "expiry":      expiry,
                "timestamp":   datetime.now().isoformat(),
                "result":      None,
                "profit":      None,
            }
            shadow_state["shadow_trades"].append(shadow_trade)
            logger.debug(f"👥 Shadow trade placed: ID {shadow_id}")
            return {"success": True, "shadow_id": shadow_id}
        else:
            logger.warning("⚠️ Shadow trade placement failed")
            return {"success": False, "reason": "Shadow trade rejected"}

    except Exception as e:
        logger.error(f"❌ Shadow trade error: {e}")
        return {"success": False, "reason": str(e)}


# ─────────────────────────────────────────────────
# RESULT TRACKER
# ─────────────────────────────────────────────────

def record_live_result(live_id: int, result: str, profit: float):
    """Record result of a live trade"""
    shadow_state["live_trades"].append({
        "live_id": live_id,
        "result":  result,
        "profit":  profit,
        "time":    datetime.now().isoformat(),
    })

    if result == "WIN":
        shadow_state["live_wins"] += 1
    else:
        shadow_state["live_losses"] += 1

    logger.debug(f"📊 Live result recorded: {result} ${profit:.2f}")


def record_shadow_result(shadow_id: int, result: str, profit: float):
    """Record result of a shadow trade"""
    for trade in shadow_state["shadow_trades"]:
        if trade["shadow_id"] == shadow_id:
            trade["result"] = result
            trade["profit"] = profit
            break

    if result == "WIN":
        shadow_state["shadow_wins"] += 1
    else:
        shadow_state["shadow_losses"] += 1

    logger.debug(f"👥 Shadow result recorded: {result} ${profit:.2f}")


# ─────────────────────────────────────────────────
# MANIPULATION DETECTOR
# ─────────────────────────────────────────────────

def compare_live_vs_shadow() -> dict:
    """
    Compare live vs shadow performance
    If shadow wins more = manipulation detected!

    Returns:
    {
        "sufficient_data":   True/False,
        "manipulation_risk": "LOW/MEDIUM/HIGH",
        "live_win_rate":     65.0,
        "shadow_win_rate":   65.0,
        "difference":        0.0,
        "recommendation":    "..."
    }
    """
    try:
        live_total   = (
            shadow_state["live_wins"] +
            shadow_state["live_losses"]
        )
        shadow_total = (
            shadow_state["shadow_wins"] +
            shadow_state["shadow_losses"]
        )

        # Need at least 10 trades for reliable comparison
        if live_total < 10 or shadow_total < 10:
            return {
                "sufficient_data": False,
                "message": (
                    f"Need more trades. "
                    f"Live: {live_total}/10 "
                    f"Shadow: {shadow_total}/10"
                ),
            }

        live_rate   = (
            shadow_state["live_wins"] / live_total * 100
        )
        shadow_rate = (
            shadow_state["shadow_wins"] / shadow_total * 100
        )
        difference  = shadow_rate - live_rate

        shadow_state["last_comparison"] = datetime.now().isoformat()

        # ── Determine manipulation risk ───────────
        if difference > 20:
            risk           = "HIGH"
            recommendation = (
                "🚨 HIGH manipulation risk! "
                "Switch to demo immediately!"
            )
            shadow_state["manipulation_alerts"] += 1
            logger.critical(
                f"🚨 MANIPULATION DETECTED! "
                f"Shadow: {shadow_rate:.1f}% vs Live: {live_rate:.1f}%"
            )

        elif difference > 10:
            risk           = "MEDIUM"
            recommendation = (
                "⚠️ Monitor closely. "
                "Possible manipulation detected."
            )
            logger.warning(
                f"⚠️ Possible manipulation: "
                f"Shadow: {shadow_rate:.1f}% vs Live: {live_rate:.1f}%"
            )

        else:
            risk           = "LOW"
            recommendation = (
                "✅ Live and shadow results consistent. "
                "No manipulation detected."
            )
            logger.info(
                f"✅ Shadow check passed: "
                f"Live: {live_rate:.1f}% Shadow: {shadow_rate:.1f}%"
            )

        return {
            "sufficient_data":    True,
            "manipulation_risk":  risk,
            "live_win_rate":      round(live_rate,   1),
            "shadow_win_rate":    round(shadow_rate, 1),
            "difference":         round(difference,  1),
            "live_trades":        live_total,
            "shadow_trades":      shadow_total,
            "recommendation":     recommendation,
            "timestamp":          datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Shadow comparison error: {e}")
        return {
            "sufficient_data":   False,
            "manipulation_risk": "UNKNOWN",
            "message":           str(e),
        }


# ─────────────────────────────────────────────────
# SHADOW CONTROLS
# ─────────────────────────────────────────────────

def enable_shadow():
    """Enable shadow trading"""
    shadow_state["enabled"] = True
    logger.info("👥 Shadow trading enabled")


def disable_shadow():
    """Disable shadow trading"""
    shadow_state["enabled"] = False
    logger.info("👥 Shadow trading disabled")


def reset_shadow_stats():
    """Reset shadow trading statistics"""
    shadow_state["live_wins"]    = 0
    shadow_state["live_losses"]  = 0
    shadow_state["shadow_wins"]  = 0
    shadow_state["shadow_losses"]= 0
    shadow_state["live_trades"]  = []
    shadow_state["shadow_trades"]= []
    logger.info("🔄 Shadow stats reset")


def get_shadow_summary() -> dict:
    """Get shadow trading summary for reports"""
    live_total   = (
        shadow_state["live_wins"] +
        shadow_state["live_losses"]
    )
    shadow_total = (
        shadow_state["shadow_wins"] +
        shadow_state["shadow_losses"]
    )

    live_rate = (
        shadow_state["live_wins"] / live_total * 100
        if live_total > 0 else 0
    )
    shadow_rate = (
        shadow_state["shadow_wins"] / shadow_total * 100
        if shadow_total > 0 else 0
    )

    return {
        "enabled":             shadow_state["enabled"],
        "live_trades":         live_total,
        "shadow_trades":       shadow_total,
        "live_win_rate":       round(live_rate,   1),
        "shadow_win_rate":     round(shadow_rate, 1),
        "manipulation_alerts": shadow_state["manipulation_alerts"],
        "last_comparison":     shadow_state["last_comparison"],
    }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Shadow Trading Test")
    print("─" * 45)

    # Simulate trades
    print("\nSimulating 15 live trades...")
    import random
    for i in range(15):
        result = "WIN" if random.random() > 0.35 else "LOSS"
        profit = 87.0 if result == "WIN" else -100.0
        record_live_result(i, result, profit)

    print("Simulating 15 shadow trades...")
    for i in range(15):
        result = "WIN" if random.random() > 0.35 else "LOSS"
        profit = 87.0 if result == "WIN" else -100.0
        record_shadow_result(i, result, profit)

    print("\nComparing results...")
    comparison = compare_live_vs_shadow()

    print(f"\nSufficient Data: {comparison['sufficient_data']}")
    if comparison["sufficient_data"]:
        print(f"Live Win Rate:   {comparison['live_win_rate']}%")
        print(f"Shadow Win Rate: {comparison['shadow_win_rate']}%")
        print(f"Difference:      {comparison['difference']}%")
        print(f"Risk Level:      {comparison['manipulation_risk']}")
        print(f"Recommendation:  {comparison['recommendation']}")

    summary = get_shadow_summary()
    print(f"\nShadow Summary: {summary}")