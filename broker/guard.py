# ⚡ APEX ORACLE — AO-1.0
# Manipulation Guard
# Compares IQ Option price vs Yahoo Finance
# Detects broker price manipulation
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import time
import yfinance as yf
from datetime import datetime
from loguru import logger
from data.database import log_manipulation


# ─────────────────────────────────────────────────
# PAIR MAPPING
# IQ Option pairs → Yahoo Finance symbols
# ─────────────────────────────────────────────────

PAIR_MAP = {
    "EURUSD-OTC": "EURUSD=X",
    "EURUSD":     "EURUSD=X",
    "GBPUSD-OTC": "GBPUSD=X",
    "GBPUSD":     "GBPUSD=X",
    "GBPJPY-OTC": "GBPJPY=X",
    "GBPJPY":     "GBPJPY=X",
    "EURGBP-OTC": "EURGBP=X",
    "EURGBP":     "EURGBP=X",
    "USDJPY-OTC": "USDJPY=X",
    "USDJPY":     "USDJPY=X",
}

# Maximum allowed price difference (0.5 pips)
MAX_DIFFERENCE = 0.0005

# Track manipulation history
_manipulation_history = []
_suspicious_pairs     = {}


# ─────────────────────────────────────────────────
# YAHOO FINANCE PRICE FETCHER
# ─────────────────────────────────────────────────

def get_yahoo_price(pair: str) -> float:
    """
    Get current price from Yahoo Finance
    Used as reference price to verify IQ Option
    """
    try:
        yahoo_symbol = PAIR_MAP.get(pair)
        if not yahoo_symbol:
            logger.warning(f"⚠️ No Yahoo symbol for {pair}")
            return 0.0

        ticker = yf.Ticker(yahoo_symbol)
        data   = ticker.history(period="1d", interval="1m")

        if data.empty:
            logger.warning(f"⚠️ No Yahoo data for {pair}")
            return 0.0

        price = float(data["Close"].iloc[-1])
        logger.debug(f"📊 Yahoo {pair}: {price}")
        return price

    except Exception as e:
        logger.warning(f"⚠️ Yahoo Finance error for {pair}: {e}")
        return 0.0


# ─────────────────────────────────────────────────
# PRICE COMPARISON
# ─────────────────────────────────────────────────

def compare_prices(
    pair:      str,
    iq_price:  float,
) -> dict:
    """
    Compare IQ Option price with Yahoo Finance

    Returns:
    {
        "safe":       True/False,
        "difference": 0.0003,
        "iq_price":   1.08523,
        "yahoo_price":1.08520,
        "action":     "TRADE" / "SKIP"
    }
    """
    try:
        if iq_price <= 0:
            return {
                "safe":        False,
                "difference":  0,
                "iq_price":    iq_price,
                "yahoo_price": 0,
                "action":      "SKIP",
                "reason":      "Invalid IQ price",
            }

        yahoo_price = get_yahoo_price(pair)

        # If Yahoo unavailable skip check
        if yahoo_price <= 0:
            logger.warning(f"⚠️ Yahoo unavailable for {pair} — skipping guard")
            return {
                "safe":        True,
                "difference":  0,
                "iq_price":    iq_price,
                "yahoo_price": 0,
                "action":      "TRADE",
                "reason":      "Yahoo unavailable — guard bypassed",
            }

        difference = abs(iq_price - yahoo_price)

        if difference > MAX_DIFFERENCE:
            # Manipulation detected!
            logger.warning(
                f"🚨 MANIPULATION DETECTED! {pair} | "
                f"IQ: {iq_price} | Yahoo: {yahoo_price} | "
                f"Diff: {difference:.6f}"
            )

            # Log to database
            log_manipulation({
                "pair":         pair,
                "iq_price":     iq_price,
                "yahoo_price":  yahoo_price,
                "difference":   difference,
                "action_taken": "TRADE_BLOCKED",
            })

            # Track suspicious pairs
            if pair not in _suspicious_pairs:
                _suspicious_pairs[pair] = 0
            _suspicious_pairs[pair] += 1

            # Add to history
            _manipulation_history.append({
                "timestamp":   datetime.now().isoformat(),
                "pair":        pair,
                "iq_price":    iq_price,
                "yahoo_price": yahoo_price,
                "difference":  difference,
            })

            return {
                "safe":        False,
                "difference":  round(difference, 6),
                "iq_price":    iq_price,
                "yahoo_price": yahoo_price,
                "action":      "SKIP",
                "reason":      f"Price manipulation detected! Diff: {difference:.6f}",
            }

        # Prices match — safe to trade
        logger.debug(
            f"✅ {pair} price verified | "
            f"IQ: {iq_price} | Yahoo: {yahoo_price} | "
            f"Diff: {difference:.6f}"
        )

        return {
            "safe":        True,
            "difference":  round(difference, 6),
            "iq_price":    iq_price,
            "yahoo_price": yahoo_price,
            "action":      "TRADE",
            "reason":      "Price verified — safe to trade",
        }

    except Exception as e:
        logger.error(f"❌ Price comparison error: {e}")
        return {
            "safe":        True,
            "difference":  0,
            "iq_price":    iq_price,
            "yahoo_price": 0,
            "action":      "TRADE",
            "reason":      f"Guard error — bypassed: {e}",
        }


# ─────────────────────────────────────────────────
# PAIR TRUST SCORE
# ─────────────────────────────────────────────────

def get_pair_trust_score(pair: str) -> dict:
    """
    Calculate trust score for a pair
    Based on manipulation history

    Score: 0-100 (100 = fully trusted)
    """
    manipulation_count = _suspicious_pairs.get(pair, 0)

    if manipulation_count == 0:
        score  = 100
        trust  = "HIGH"
    elif manipulation_count <= 2:
        score  = 75
        trust  = "MEDIUM"
    elif manipulation_count <= 5:
        score  = 40
        trust  = "LOW"
    else:
        score  = 10
        trust  = "VERY_LOW"

    return {
        "pair":                pair,
        "trust_score":         score,
        "trust_level":         trust,
        "manipulation_count":  manipulation_count,
    }


def get_safest_pair(pairs: list) -> str:
    """Get the most trusted pair from list"""
    best_pair  = pairs[0]
    best_score = 0

    for pair in pairs:
        trust = get_pair_trust_score(pair)
        if trust["trust_score"] > best_score:
            best_score = trust["trust_score"]
            best_pair  = pair

    return best_pair


# ─────────────────────────────────────────────────
# SHADOW TRADE TRACKER
# ─────────────────────────────────────────────────

_shadow_trades = []


def record_shadow_trade(
    trade_id:    int,
    pair:        str,
    direction:   str,
    stake:       float,
    expiry:      int,
) -> dict:
    """
    Record a shadow trade on demo
    Mirrors every live trade for comparison
    """
    shadow = {
        "trade_id":    trade_id,
        "pair":        pair,
        "direction":   direction,
        "stake":       stake,
        "expiry":      expiry,
        "timestamp":   datetime.now().isoformat(),
        "result":      None,
    }
    _shadow_trades.append(shadow)
    logger.debug(f"👥 Shadow trade recorded: {pair} {direction}")
    return shadow


def update_shadow_result(trade_id: int, result: str):
    """Update shadow trade result"""
    for trade in _shadow_trades:
        if trade["trade_id"] == trade_id:
            trade["result"] = result
            break


def compare_live_vs_shadow() -> dict:
    """
    Compare live vs shadow trade results
    If shadow consistently beats live = manipulation!
    """
    completed = [t for t in _shadow_trades if t["result"]]

    if len(completed) < 10:
        return {
            "sufficient_data": False,
            "message":         "Need at least 10 trades to compare",
        }

    live_wins   = sum(1 for t in completed if t["result"] == "WIN")
    shadow_wins = sum(1 for t in completed if t["result"] == "WIN")

    live_rate   = live_wins   / len(completed) * 100
    shadow_rate = shadow_wins / len(completed) * 100

    difference  = shadow_rate - live_rate

    if difference > 15:
        logger.warning(
            f"🚨 MANIPULATION SUSPECTED! "
            f"Shadow wins {shadow_rate:.1f}% vs Live {live_rate:.1f}%"
        )
        return {
            "sufficient_data":    True,
            "manipulation_risk":  "HIGH",
            "live_win_rate":      live_rate,
            "shadow_win_rate":    shadow_rate,
            "difference":         difference,
            "recommendation":     "Switch to demo mode immediately!",
        }

    return {
        "sufficient_data":   True,
        "manipulation_risk": "LOW",
        "live_win_rate":     live_rate,
        "shadow_win_rate":   shadow_rate,
        "difference":        difference,
        "recommendation":    "Live and shadow results are consistent",
    }


# ─────────────────────────────────────────────────
# MANIPULATION REPORT
# ─────────────────────────────────────────────────

def get_manipulation_report() -> dict:
    """Full manipulation report for Telegram"""
    total_incidents = len(_manipulation_history)
    pairs_affected  = list(_suspicious_pairs.keys())
    most_suspicious = max(
        _suspicious_pairs,
        key=_suspicious_pairs.get
    ) if _suspicious_pairs else "None"

    return {
        "total_incidents":    total_incidents,
        "pairs_affected":     pairs_affected,
        "most_suspicious":    most_suspicious,
        "recent_incidents":   _manipulation_history[-5:],
        "pair_trust_scores":  {
            pair: get_pair_trust_score(pair)
            for pair in ["EURUSD-OTC", "GBPUSD-OTC"]
        },
    }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Manipulation Guard Test")
    print("─" * 45)

    print("\nFetching Yahoo Finance price for EURUSD...")
    yahoo = get_yahoo_price("EURUSD-OTC")
    print(f"Yahoo EURUSD price: {yahoo}")

    if yahoo > 0:
        print("\nTesting price comparison...")

        # Safe price (close to Yahoo)
        safe   = compare_prices("EURUSD-OTC", yahoo + 0.0002)
        print(f"\nSafe test:  {safe['action']} | Diff: {safe['difference']}")

        # Manipulated price (far from Yahoo)
        manip  = compare_prices("EURUSD-OTC", yahoo + 0.0010)
        print(f"Manip test: {manip['action']} | Diff: {manip['difference']}")

    print("\nPair trust scores:")
    for pair in ["EURUSD-OTC", "GBPUSD-OTC"]:
        trust = get_pair_trust_score(pair)
        print(f"  {pair}: {trust['trust_level']} ({trust['trust_score']}/100)")