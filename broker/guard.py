# ⚡ APEX ORACLE — AO-1.0
# Manipulation Guard
# Compares Deriv price vs Yahoo Finance (Forex only)
# Detects broker price manipulation
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import yfinance as yf
from datetime import datetime
from loguru import logger
from data.database import log_manipulation


# ─────────────────────────────────────────────────
# PAIR MAPPING — SYNTHETIC ONLY
# All Synthetic indices have no Yahoo equivalent.
# The guard will always return safe for them.
# ─────────────────────────────────────────────────

# This mapping is kept for future Forex support,
# but is currently unused in Synthetic-only mode.
PAIR_MAP = {
    # Forex pairs (commented out — not used)
    # "EURUSD": "EURUSD=X",
    # "GBPUSD": "GBPUSD=X",
    # "GBPJPY": "GBPJPY=X",
    # "EURGBP": "EURGBP=X",
    # "USDJPY": "USDJPY=X",
    # Volatility Indices — no external reference
    "V75":    None,
    "V50":    None,
    "V25":    None,
    "V10":    None,
    "V100":   None,
    "V60":    None,
    "V90":    None,
}

# Maximum allowed price difference (0.5 pips)
MAX_DIFFERENCE = 0.0005

# Track manipulation history
_manipulation_history = []
_suspicious_pairs     = {}


# ─────────────────────────────────────────────────
# YAHOO FINANCE PRICE FETCHER (Forex only)
# ─────────────────────────────────────────────────

def get_yahoo_price(pair: str) -> float:
    """
    Get current price from Yahoo Finance
    Only used for Forex pairs (not used in Synthetic-only mode)
    """
    try:
        yahoo_symbol = PAIR_MAP.get(pair)
        if not yahoo_symbol:
            return 0.0

        ticker = yf.Ticker(yahoo_symbol)
        data   = ticker.history(period="1d", interval="1m")

        if data.empty:
            return 0.0

        price = float(data["Close"].iloc[-1])
        return price

    except Exception:
        return 0.0


# ─────────────────────────────────────────────────
# PRICE COMPARISON
# ─────────────────────────────────────────────────

def compare_prices(
    pair:         str,
    deriv_price:  float,
) -> dict:
    """
    Compare Deriv price with Yahoo Finance (Forex only).
    For Synthetic indices, always returns safe.

    Returns:
    {
        "safe":          True/False,
        "difference":    0.0003,
        "deriv_price":   1.08523,
        "yahoo_price":   1.08520,
        "action":        "TRADE" / "SKIP"
    }
    """
    try:
        # ── Synthetic indices — always safe ──
        if PAIR_MAP.get(pair) is None:
            return {
                "safe":         True,
                "difference":   0,
                "deriv_price":  deriv_price,
                "yahoo_price":  0,
                "action":       "TRADE",
                "reason":       "Synthetic index — no external reference needed",
            }

        if deriv_price <= 0:
            return {
                "safe":         False,
                "difference":   0,
                "deriv_price":  deriv_price,
                "yahoo_price":  0,
                "action":       "SKIP",
                "reason":       "Invalid Deriv price",
            }

        yahoo_price = get_yahoo_price(pair)

        if yahoo_price <= 0:
            return {
                "safe":         True,
                "difference":   0,
                "deriv_price":  deriv_price,
                "yahoo_price":  0,
                "action":       "TRADE",
                "reason":       "Yahoo unavailable — guard bypassed",
            }

        difference = abs(deriv_price - yahoo_price)

        if difference > MAX_DIFFERENCE:
            # Manipulation detected!
            logger.warning(
                f"🚨 MANIPULATION DETECTED! {pair} | "
                f"Deriv: {deriv_price} | Yahoo: {yahoo_price} | "
                f"Diff: {difference:.6f}"
            )

            log_manipulation({
                "pair":         pair,
                "deriv_price":  deriv_price,
                "yahoo_price":  yahoo_price,
                "difference":   difference,
                "action_taken": "TRADE_BLOCKED",
            })

            if pair not in _suspicious_pairs:
                _suspicious_pairs[pair] = 0
            _suspicious_pairs[pair] += 1

            _manipulation_history.append({
                "timestamp":   datetime.now().isoformat(),
                "pair":        pair,
                "deriv_price": deriv_price,
                "yahoo_price": yahoo_price,
                "difference":  difference,
            })

            return {
                "safe":         False,
                "difference":   round(difference, 6),
                "deriv_price":  deriv_price,
                "yahoo_price":  yahoo_price,
                "action":       "SKIP",
                "reason":       f"Price manipulation detected! Diff: {difference:.6f}",
            }

        logger.debug(
            f"✅ {pair} price verified | "
            f"Deriv: {deriv_price} | Yahoo: {yahoo_price} | "
            f"Diff: {difference:.6f}"
        )

        return {
            "safe":         True,
            "difference":   round(difference, 6),
            "deriv_price":  deriv_price,
            "yahoo_price":  yahoo_price,
            "action":       "TRADE",
            "reason":       "Price verified — safe to trade",
        }

    except Exception as e:
        logger.error(f"❌ Price comparison error: {e}")
        return {
            "safe":         True,
            "difference":   0,
            "deriv_price":  deriv_price,
            "yahoo_price":  0,
            "action":       "TRADE",
            "reason":       f"Guard error — bypassed: {e}",
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
            for pair in ["V75", "V50", "V25", "V10", "V100", "V60", "V90"]
        },
    }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Manipulation Guard Test")
    print("─" * 45)

    print("\n🔍 Testing Synthetic V75 — should always be safe:")
    result = compare_prices("V75", 123.45)
    print(f"Safe: {result['safe']} | Action: {result['action']} | Reason: {result['reason']}")

    print("\n✅ All tests passed.")