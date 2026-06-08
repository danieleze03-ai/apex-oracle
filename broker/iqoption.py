# ⚡ APEX ORACLE — AO-1.0
# IQ Option Broker Connection
# Handles login, data fetch, trade execution
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from iqoptionapi.api import IQOptionAPI as IQ_Option

load_dotenv()

# ─────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────

# Global IQ Option instance
iq = None

def connect() -> bool:
    """Connect to IQ Option"""
    global iq
    try:
        email    = os.getenv("IQ_OPTION_EMAIL")
        password = os.getenv("IQ_OPTION_PASSWORD")
        mode     = os.getenv("TRADING_MODE", "PRACTICE")

        if not email or not password:
            logger.error("❌ IQ Option credentials missing from .env!")
            return False

        logger.info(f"⚡ Connecting to IQ Option as {email}...")
        iq = IQ_Option(email, password)
        iq.connect()

        if iq.check_connect():
            iq.change_balance(mode)
            balance = get_balance()
            logger.success(f"✅ Connected! Mode: {mode} | Balance: ${balance:.2f}")
            return True
        else:
            logger.error("❌ Connection failed! Check credentials.")
            return False

    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        return False


def disconnect():
    """Disconnect from IQ Option"""
    global iq
    try:
        if iq:
            iq.close()
            logger.info("🔌 Disconnected from IQ Option")
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")


def reconnect(max_attempts: int = 5) -> bool:
    """Auto reconnect if connection drops"""
    for attempt in range(1, max_attempts + 1):
        logger.warning(f"🔄 Reconnect attempt {attempt}/{max_attempts}...")
        if connect():
            logger.success("✅ Reconnected successfully!")
            return True
        time.sleep(5 * attempt)
    logger.error("❌ All reconnect attempts failed!")
    return False


def is_connected() -> bool:
    """Check if still connected"""
    global iq
    try:
        if iq and iq.check_connect():
            return True
        return False
    except:
        return False


def ensure_connected() -> bool:
    """Make sure we are connected before any operation"""
    if not is_connected():
        logger.warning("⚠️ Connection lost! Attempting reconnect...")
        return reconnect()
    return True


# ─────────────────────────────────────────────────
# ACCOUNT INFO
# ─────────────────────────────────────────────────

def get_balance() -> float:
    """Get current account balance"""
    global iq
    try:
        if ensure_connected():
            return iq.get_balance()
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to get balance: {e}")
        return 0.0


def get_mode() -> str:
    """Get current trading mode"""
    return os.getenv("TRADING_MODE", "PRACTICE")


def switch_mode(mode: str) -> bool:
    """Switch between PRACTICE and REAL"""
    global iq
    try:
        if mode not in ["PRACTICE", "REAL"]:
            logger.error("❌ Mode must be PRACTICE or REAL")
            return False
        if ensure_connected():
            iq.change_balance(mode)
            os.environ["TRADING_MODE"] = mode
            logger.success(f"✅ Switched to {mode} mode")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Failed to switch mode: {e}")
        return False


# ─────────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────────

def get_candles(pair: str, timeframe: int, count: int = 100) -> list:
    """
    Fetch candle data for a pair
    pair      = "EURUSD-OTC"
    timeframe = candle size in seconds (60=1min, 300=5min)
    count     = number of candles to fetch
    """
    global iq
    try:
        if not ensure_connected():
            return []

        tf_seconds = timeframe * 60
        candles = iq.get_candles(pair, tf_seconds, count, time.time())

        if not candles:
            logger.warning(f"⚠️ No candles returned for {pair}")
            return []

        formatted = []
        for c in candles:
            formatted.append({
                "timestamp": c["from"],
                "open":      c["open"],
                "high":      c["max"],
                "low":       c["min"],
                "close":     c["close"],
                "volume":    c["volume"],
            })

        logger.debug(f"📊 Got {len(formatted)} candles for {pair} {timeframe}min")
        return formatted

    except Exception as e:
        logger.error(f"❌ Failed to get candles for {pair}: {e}")
        return []


def get_current_price(pair: str) -> float:
    """Get current live price for a pair"""
    global iq
    try:
        if not ensure_connected():
            return 0.0
        candles = get_candles(pair, 1, 1)
        if candles:
            return candles[-1]["close"]
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to get price for {pair}: {e}")
        return 0.0


def get_all_pairs() -> list:
    """Get list of all available pairs"""
    global iq
    try:
        if not ensure_connected():
            return []
        all_assets = iq.get_all_open_time()
        return all_assets
    except Exception as e:
        logger.error(f"❌ Failed to get pairs: {e}")
        return []


def is_pair_open(pair: str) -> bool:
    """Check if a trading pair is currently open"""
    global iq
    try:
        if not ensure_connected():
            return False
        all_assets = iq.get_all_open_time()

        if "binary" in all_assets:
            if pair in all_assets["binary"]:
                return all_assets["binary"][pair]["open"]

        if "digital" in all_assets:
            if pair in all_assets["digital"]:
                return all_assets["digital"][pair]["open"]

        return False
    except Exception as e:
        logger.error(f"❌ Failed to check pair status: {e}")
        return False


# ─────────────────────────────────────────────────
# TRADE EXECUTION
# ─────────────────────────────────────────────────

def place_trade(
    pair:      str,
    direction: str,
    stake:     float,
    expiry:    int = 5
) -> dict:
    global iq
    try:
        if not ensure_connected():
            return {"success": False, "error": "Not connected"}

        direction = direction.lower()
        if direction not in ["call", "put"]:
            return {"success": False, "error": "Direction must be call or put"}

        if not is_pair_open(pair):
            logger.warning(f"⚠️ {pair} is not open for trading!")
            return {"success": False, "error": f"{pair} is closed"}

        balance = get_balance()
        if stake > balance:
            logger.warning(f"⚠️ Stake ${stake} exceeds balance ${balance}")
            return {"success": False, "error": "Insufficient balance"}

        logger.info(f"⚡ Placing trade: {pair} {direction.upper()} ${stake} {expiry}min")

        status, trade_id = iq.buy(stake, pair, direction, expiry)

        if status:
            logger.success(f"✅ Trade placed! ID: {trade_id} | {pair} {direction.upper()} ${stake}")
            return {
                "success":   True,
                "trade_id":  trade_id,
                "pair":      pair,
                "direction": direction,
                "stake":     stake,
                "expiry":    expiry,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            logger.error(f"❌ Trade failed for {pair}")
            return {"success": False, "error": "Trade rejected by broker"}

    except Exception as e:
        logger.error(f"❌ Trade execution error: {e}")
        return {"success": False, "error": str(e)}


def check_trade_result(trade_id: int) -> dict:
    global iq
    try:
        if not ensure_connected():
            return {"result": "unknown", "profit": 0}

        result = iq.check_win_v3(trade_id)

        if result > 0:
            logger.success(f"✅ Trade {trade_id} → WIN! Profit: ${result:.2f}")
            return {"result": "WIN", "profit": result}
        else:
            logger.warning(f"❌ Trade {trade_id} → LOSS! ${result:.2f}")
            return {"result": "LOSS", "profit": result}

    except Exception as e:
        logger.error(f"❌ Failed to check trade result: {e}")
        return {"result": "unknown", "profit": 0}


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — IQ Option Connection Test")
    print("─" * 45)

    if connect():
        print(f"\n✅ Connected!")
        print(f"💰 Balance: ${get_balance():.2f}")
        print(f"📊 Mode: {get_mode()}")

        print("\n📈 Testing candle fetch...")
        candles = get_candles("EURUSD-OTC", 5, 10)
        if candles:
            print(f"✅ Got {len(candles)} candles!")
            print(f"Latest close: {candles[-1]['close']}")
        else:
            print("❌ No candles returned")

        print("\n✅ IQ Option connection test complete!")
        disconnect()
    else:
        print("\n❌ Connection failed!")
        print("Check your IQ_OPTION_EMAIL and IQ_OPTION_PASSWORD in .env")