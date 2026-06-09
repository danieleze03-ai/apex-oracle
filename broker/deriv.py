# ⚡ APEX ORACLE — AO-1.0
# Deriv.com Broker Connection
# Handles login, data fetch, trade execution
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import json
import time
import asyncio
import websockets
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# DERIV WEBSOCKET CONFIG
# ─────────────────────────────────────────────────
DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

# Global state
ws_connection = None
account_balance = 0.0
trading_mode = "demo"  # "demo" or "real"
open_trades = {}       # track active trades

# Pair mapping: our pairs → Deriv symbols
PAIR_MAP = {
    "EURUSD":  "frxEURUSD",
    "GBPUSD":  "frxGBPUSD",
    "GBPJPY":  "frxGBPJPY",
    "EURGBP":  "frxEURGBP",
    "USDJPY":  "frxUSDJPY",
    "V75":     "R_75",
    "V50":     "R_50",
    "V25":     "R_25",
    "V10":     "R_10",
    "V100":    "R_100",
}


# ─────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────

def _get_loop():
    """Get or create event loop"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _run(coro):
    """Run async function from sync context"""
    loop = _get_loop()
    return loop.run_until_complete(coro)


def _to_deriv_symbol(pair: str) -> str:
    """Convert our pair name to Deriv symbol"""
    return PAIR_MAP.get(pair.upper(), pair)


async def _send_receive(payload: dict, timeout: int = 10) -> dict:
    """Send a request to Deriv and return the response"""
    global ws_connection
    try:
        await ws_connection.send(json.dumps(payload))
        response = await asyncio.wait_for(ws_connection.recv(), timeout=timeout)
        return json.loads(response)
    except asyncio.TimeoutError:
        logger.error("❌ Deriv API timeout!")
        return {}
    except Exception as e:
        logger.error(f"❌ WebSocket send/receive error: {e}")
        return {}


# ─────────────────────────────────────────────────
# CONNECT / DISCONNECT
# ─────────────────────────────────────────────────

async def _connect_async() -> bool:
    global ws_connection, account_balance, trading_mode

    try:
        token = os.getenv("DERIV_API_TOKEN")
        mode  = os.getenv("TRADING_MODE", "PRACTICE").upper()

        if not token:
            logger.error("❌ DERIV_API_TOKEN missing from .env!")
            return False

        logger.info("⚡ Connecting to Deriv.com WebSocket...")
        ws_connection = await websockets.connect(DERIV_WS_URL)

        # Authorize with token
        auth_payload = {"authorize": token}
        response = await _send_receive(auth_payload)

        if "error" in response:
            logger.error(f"❌ Deriv auth failed: {response['error']['message']}")
            return False

        if "authorize" not in response:
            logger.error("❌ Deriv auth response invalid!")
            return False

        auth_data = response["authorize"]

        # Set trading mode
        trading_mode = "demo" if mode == "PRACTICE" else "real"

        # ─────────────────────────────────────────
        # FIX: Find correct account and switch to it
        # Deriv has separate virtual/real accounts
        # We must switch to the right one to get
        # the correct balance
        # ─────────────────────────────────────────
        account_list = auth_data.get("account_list", [])
        target_type  = "virtual" if trading_mode == "demo" else "real"

        logger.info(f"🔍 Found {len(account_list)} account(s). Looking for {target_type} account...")

        target_account = None
        for acc in account_list:
            is_virtual = acc.get("is_virtual", 0)
            loginid    = acc.get("loginid", "")
            logger.debug(f"   → Account: {loginid} | Virtual: {is_virtual}")
            if trading_mode == "demo" and is_virtual == 1:
                target_account = acc
                break
            elif trading_mode == "real" and is_virtual == 0 and acc.get("currency") == "USD":
                target_account = acc
                break

        if target_account:
            login_id = target_account["loginid"]
            logger.info(f"🔄 Switching to {target_type} account: {login_id}")

            # Switch to correct account
            switch_resp = await _send_receive({"switch_account": login_id})

            if "error" in switch_resp:
                logger.warning(f"⚠️ Account switch warning: {switch_resp['error'].get('message', 'unknown')}")
            else:
                logger.success(f"✅ Switched to account: {login_id}")

            # Re-authorize after switch to get correct balance
            re_auth = await _send_receive({"authorize": token})
            if "authorize" in re_auth:
                auth_data = re_auth["authorize"]
                logger.info("✅ Re-authorized successfully after account switch")
            else:
                logger.warning("⚠️ Re-auth after switch failed — using original auth data")
        else:
            logger.warning(f"⚠️ No {target_type} account found in account list — using default")

        # Read balance from correct account
        account_balance = float(auth_data.get("balance", 0.0))

        logger.success(f"✅ Connected to Deriv! Mode: {trading_mode.upper()} | Balance: ${account_balance:.2f}")
        return True

    except Exception as e:
        logger.error(f"❌ Deriv connection error: {e}")
        return False


def connect() -> bool:
    """Connect to Deriv.com"""
    return _run(_connect_async())


def disconnect():
    """Disconnect from Deriv.com"""
    global ws_connection
    try:
        if ws_connection:
            _run(ws_connection.close())
            ws_connection = None
            logger.info("🔌 Disconnected from Deriv.com")
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")


def reconnect(max_attempts: int = 5) -> bool:
    """Auto reconnect if connection drops"""
    global ws_connection
    ws_connection = None
    for attempt in range(1, max_attempts + 1):
        logger.warning(f"🔄 Reconnect attempt {attempt}/{max_attempts}...")
        if connect():
            logger.success("✅ Reconnected to Deriv successfully!")
            return True
        time.sleep(5 * attempt)
    logger.error("❌ All reconnect attempts failed!")
    return False


def is_connected() -> bool:
    """Check if WebSocket is still alive"""
    global ws_connection
    try:
        if ws_connection and not ws_connection.closed:
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

async def _get_balance_async() -> float:
    try:
        response = await _send_receive({"balance": 1, "subscribe": 0})
        if "balance" in response:
            return float(response["balance"]["balance"])
        return 0.0
    except Exception as e:
        logger.error(f"❌ Balance fetch error: {e}")
        return 0.0


def get_balance() -> float:
    """Get current account balance"""
    try:
        if ensure_connected():
            return _run(_get_balance_async())
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to get balance: {e}")
        return 0.0


def get_mode() -> str:
    """Get current trading mode"""
    return os.getenv("TRADING_MODE", "PRACTICE")


def switch_mode(mode: str) -> bool:
    """Switch between PRACTICE and REAL"""
    try:
        if mode not in ["PRACTICE", "REAL"]:
            logger.error("❌ Mode must be PRACTICE or REAL")
            return False
        os.environ["TRADING_MODE"] = mode
        logger.success(f"✅ Switched to {mode} mode — reconnecting...")
        return reconnect()
    except Exception as e:
        logger.error(f"❌ Failed to switch mode: {e}")
        return False


# ─────────────────────────────────────────────────
# MARKET DATA
# ─────────────────────────────────────────────────

async def _get_candles_async(pair: str, timeframe: int, count: int) -> list:
    try:
        symbol = _to_deriv_symbol(pair)
        end_time = int(time.time())
        start_time = end_time - (timeframe * 60 * count)

        payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "start": start_time,
            "style": "candles",
            "granularity": timeframe * 60,
        }

        response = await _send_receive(payload, timeout=15)

        if "error" in response:
            logger.error(f"❌ Candle error for {pair}: {response['error']['message']}")
            return []

        if "candles" not in response:
            logger.warning(f"⚠️ No candles returned for {pair}")
            return []

        formatted = []
        for c in response["candles"]:
            formatted.append({
                "timestamp": c["epoch"],
                "open":      float(c["open"]),
                "high":      float(c["high"]),
                "low":       float(c["low"]),
                "close":     float(c["close"]),
                "volume":    0,  # Deriv doesn't provide volume on candles
            })

        logger.debug(f"📊 Got {len(formatted)} candles for {pair} {timeframe}min")
        return formatted

    except Exception as e:
        logger.error(f"❌ Failed to get candles for {pair}: {e}")
        return []


def get_candles(pair: str, timeframe: int, count: int = 100) -> list:
    """Get historical candles for a pair"""
    try:
        if not ensure_connected():
            return []
        return _run(_get_candles_async(pair, timeframe, count))
    except Exception as e:
        logger.error(f"❌ get_candles error: {e}")
        return []


def get_current_price(pair: str) -> float:
    """Get latest price for a pair"""
    try:
        candles = get_candles(pair, 1, 1)
        if candles:
            return candles[-1]["close"]
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to get price for {pair}: {e}")
        return 0.0


async def _is_pair_open_async(pair: str) -> bool:
    try:
        symbol = _to_deriv_symbol(pair)
        payload = {"active_symbols": "brief", "product_type": "basic"}
        response = await _send_receive(payload, timeout=15)

        if "active_symbols" not in response:
            return False

        for asset in response["active_symbols"]:
            if asset["symbol"] == symbol:
                return bool(asset.get("exchange_is_open", False))

        return False
    except Exception as e:
        logger.error(f"❌ is_pair_open error: {e}")
        return False


def is_pair_open(pair: str) -> bool:
    """Check if a pair is currently tradeable"""
    try:
        if not ensure_connected():
            return False
        return _run(_is_pair_open_async(pair))
    except Exception as e:
        logger.error(f"❌ Failed to check pair status: {e}")
        return False


# ─────────────────────────────────────────────────
# TRADE EXECUTION
# ─────────────────────────────────────────────────

async def _place_trade_async(pair: str, direction: str, stake: float, expiry: int) -> dict:
    try:
        symbol    = _to_deriv_symbol(pair)
        contract  = "CALL" if direction == "call" else "PUT"
        duration  = expiry * 60  # convert minutes to seconds

        payload = {
            "buy": 1,
            "price": stake,
            "parameters": {
                "amount":        stake,
                "basis":         "stake",
                "contract_type": contract,
                "currency":      "USD",
                "duration":      duration,
                "duration_unit": "s",
                "symbol":        symbol,
            }
        }

        response = await _send_receive(payload, timeout=15)

        if "error" in response:
            error_msg = response["error"]["message"]
            logger.error(f"❌ Trade rejected: {error_msg}")
            return {"success": False, "error": error_msg}

        if "buy" not in response:
            return {"success": False, "error": "Invalid trade response"}

        buy_data   = response["buy"]
        trade_id   = buy_data["contract_id"]
        buy_price  = float(buy_data["buy_price"])

        # Store in open trades tracker
        open_trades[trade_id] = {
            "pair":      pair,
            "direction": direction,
            "stake":     stake,
            "expiry":    expiry,
            "buy_price": buy_price,
            "timestamp": datetime.now().isoformat(),
        }

        logger.success(f"✅ Trade placed! ID: {trade_id} | {pair} {contract} ${stake}")
        return {
            "success":   True,
            "trade_id":  trade_id,
            "pair":      pair,
            "direction": direction,
            "stake":     stake,
            "expiry":    expiry,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Trade execution error: {e}")
        return {"success": False, "error": str(e)}


def place_trade(pair: str, direction: str, stake: float, expiry: int = 5) -> dict:
    """Place a binary options trade on Deriv"""
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
        return _run(_place_trade_async(pair, direction, stake, expiry))

    except Exception as e:
        logger.error(f"❌ place_trade error: {e}")
        return {"success": False, "error": str(e)}


async def _check_trade_result_async(trade_id: int) -> dict:
    try:
        payload = {"proposal_open_contract": 1, "contract_id": trade_id}
        response = await _send_receive(payload, timeout=15)

        if "error" in response:
            logger.error(f"❌ Result check error: {response['error']['message']}")
            return {"result": "unknown", "profit": 0}

        contract = response.get("proposal_open_contract", {})
        status   = contract.get("status", "open")

        if status == "open":
            logger.info(f"⏳ Trade {trade_id} still open...")
            return {"result": "open", "profit": 0}

        profit = float(contract.get("profit", 0))

        if profit > 0:
            logger.success(f"✅ Trade {trade_id} → WIN! Profit: ${profit:.2f}")
            return {"result": "WIN", "profit": profit}
        else:
            logger.warning(f"❌ Trade {trade_id} → LOSS! ${profit:.2f}")
            return {"result": "LOSS", "profit": profit}

    except Exception as e:
        logger.error(f"❌ Failed to check trade result: {e}")
        return {"result": "unknown", "profit": 0}


def check_trade_result(trade_id: int) -> dict:
    """Check if a trade won or lost"""
    try:
        if not ensure_connected():
            return {"result": "unknown", "profit": 0}
        return _run(_check_trade_result_async(trade_id))
    except Exception as e:
        logger.error(f"❌ check_trade_result error: {e}")
        return {"result": "unknown", "profit": 0}


# ─────────────────────────────────────────────────
# CONNECTION TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Deriv.com Connection Test")
    print("─" * 45)

    if connect():
        print(f"\n✅ Connected to Deriv!")
        print(f"💰 Balance: ${get_balance():.2f}")
        print(f"📊 Mode: {get_mode()}")
        print(f"\n🔍 Testing EURUSD candles...")
        candles = get_candles("EURUSD", 5, 5)
        if candles:
            print(f"✅ Got {len(candles)} candles!")
            print(f"   Latest close: {candles[-1]['close']}")
        disconnect()
    else:
        print("\n❌ Connection failed!")