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
ws_connection    = None
account_balance  = 0.0
trading_mode     = "demo"
open_trades      = {}
_last_ping_time  = 0
_shared_loop     = None
_ws_lock         = None  # ← NEW: prevents concurrent WebSocket calls

# Pair mapping: our pairs → Deriv symbols
PAIR_MAP = {
    "V75":  "R_75",
    "V50":  "R_50",
    "V25":  "R_25",
    "V10":  "R_10",
    "V100": "R_100",
    "V60":  "R_60",
    "V90":  "R_90",
}


# ─────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────

def _run(coro):
    global _shared_loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if _shared_loop is None or _shared_loop.is_closed():
            _shared_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_shared_loop)
        loop = _shared_loop

    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return loop.run_until_complete(coro)


def _to_deriv_symbol(pair: str) -> str:
    return PAIR_MAP.get(pair.upper(), pair)


def _get_lock():
    """Get or create the asyncio lock for the current loop"""
    global _ws_lock, _shared_loop
    if _ws_lock is None:
        if _shared_loop is None or _shared_loop.is_closed():
            _shared_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_shared_loop)
        _ws_lock = asyncio.Lock()
    return _ws_lock


async def _send_receive(payload: dict, timeout: int = 15) -> dict:
    """Thread-safe send/receive — one call at a time"""
    global ws_connection
    lock = _get_lock()
    async with lock:
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
    global ws_connection, account_balance, trading_mode, _ws_lock

    try:
        token = os.getenv("DERIV_API_TOKEN")
        mode  = os.getenv("TRADING_MODE", "PRACTICE").upper()

        if not token:
            logger.error("❌ DERIV_API_TOKEN missing from .env!")
            return False

        logger.info("⚡ Connecting to Deriv.com WebSocket...")

        ws_connection = await websockets.connect(
            DERIV_WS_URL,
            ping_interval=20,
            ping_timeout=10,
        )

        # Reset lock for new connection
        _ws_lock = asyncio.Lock()

        auth_payload = {"authorize": token}
        await ws_connection.send(json.dumps(auth_payload))
        response = json.loads(await asyncio.wait_for(ws_connection.recv(), timeout=15))

        if "error" in response:
            logger.error(f"❌ Deriv auth failed: {response['error']['message']}")
            return False

        if "authorize" not in response:
            logger.error("❌ Deriv auth response invalid!")
            return False

        auth_data    = response["authorize"]
        trading_mode = "demo" if mode == "PRACTICE" else "real"

        account_list  = auth_data.get("account_list", [])
        target_type   = "virtual" if trading_mode == "demo" else "real"

        logger.info(
            f"🔍 Found {len(account_list)} account(s). "
            f"Looking for {target_type} account..."
        )

        for acc in account_list:
            is_virtual = acc.get("is_virtual", 0)
            if trading_mode == "demo" and is_virtual == 1:
                logger.success(f"✅ Found correct account: {acc['loginid']}")
                break
            elif trading_mode == "real" and is_virtual == 0 \
                    and acc.get("currency") == "USD":
                logger.success(f"✅ Found correct account: {acc['loginid']}")
                break

        account_balance = float(auth_data.get("balance", 0.0))

        logger.success(
            f"✅ Connected to Deriv! "
            f"Mode: {trading_mode.upper()} | "
            f"Balance: ${account_balance:.2f}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Deriv connection error: {e}")
        return False


def connect() -> bool:
    return _run(_connect_async())


def disconnect():
    global ws_connection
    try:
        if ws_connection:
            _run(ws_connection.close())
            ws_connection = None
            logger.info("🔌 Disconnected from Deriv.com")
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")


def reconnect(max_attempts: int = 5) -> bool:
    global ws_connection, _ws_lock
    ws_connection = None
    _ws_lock      = None
    for attempt in range(1, max_attempts + 1):
        logger.warning(f"🔄 Reconnect attempt {attempt}/{max_attempts}...")
        if connect():
            logger.success("✅ Reconnected to Deriv successfully!")
            return True
        time.sleep(5 * attempt)
    logger.error("❌ All reconnect attempts failed!")
    return False


def is_connected() -> bool:
    global ws_connection
    try:
        if ws_connection is None:
            return False
        if ws_connection.state.name != "OPEN":
            return False
        return True
    except:
        return False


def ensure_connected() -> bool:
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
    try:
        if ensure_connected():
            return _run(_get_balance_async())
        return 0.0
    except Exception as e:
        logger.error(f"❌ Failed to get balance: {e}")
        return 0.0


def get_mode() -> str:
    return os.getenv("TRADING_MODE", "PRACTICE")


def switch_mode(mode: str) -> bool:
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
        symbol   = _to_deriv_symbol(pair)
        end_time = int(time.time())

        payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": timeframe * 60,
        }

        response = await _send_receive(payload, timeout=20)

        if not response:
            logger.warning(f"⚠️ Empty response for {pair} candles")
            return []

        if "error" in response:
            logger.error(
                f"❌ Candle error for {pair}: "
                f"{response['error']['message']}"
            )
            return []

        if "candles" not in response:
            logger.warning(f"⚠️ No candles key in response for {pair}")
            return []

        candles = response["candles"]
        if not candles:
            logger.warning(f"⚠️ Empty candles list for {pair}")
            return []

        formatted = []
        for c in candles:
            formatted.append({
                "timestamp": int(c["epoch"]),
                "open":      float(c["open"]),
                "high":      float(c["high"]),
                "low":       float(c["low"]),
                "close":     float(c["close"]),
                "volume":    0,
            })

        logger.debug(
            f"📊 Got {len(formatted)} candles for {pair} {timeframe}min | "
            f"Latest close: {formatted[-1]['close']}"
        )
        return formatted

    except Exception as e:
        logger.error(f"❌ Failed to get candles for {pair}: {e}")
        return []


def get_candles(pair: str, timeframe: int, count: int = 100) -> list:
    try:
        if not ensure_connected():
            return []
        # Small delay between candle fetches to avoid response mixing
        time.sleep(0.3)
        return _run(_get_candles_async(pair, timeframe, count))
    except Exception as e:
        logger.error(f"❌ get_candles error: {e}")
        return []


def get_current_price(pair: str) -> float:
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
        symbol   = _to_deriv_symbol(pair)
        payload  = {"active_symbols": "brief", "product_type": "basic"}
        response = await _send_receive(payload, timeout=15)

        if "active_symbols" not in response:
            return True  # ← Default to open if check fails

        for asset in response["active_symbols"]:
            if asset["symbol"] == symbol:
                return bool(asset.get("exchange_is_open", False))

        return True  # ← Default to open if pair not found

    except Exception as e:
        logger.error(f"❌ is_pair_open error: {e}")
        return True  # ← Default to open on error


def is_pair_open(pair: str) -> bool:
    try:
        if not ensure_connected():
            return False
        return _run(_is_pair_open_async(pair))
    except Exception as e:
        logger.error(f"❌ Failed to check pair status: {e}")
        return True  # ← Default to open on error


# ─────────────────────────────────────────────────
# TRADE EXECUTION
# ─────────────────────────────────────────────────

async def _place_trade_async(
    pair: str, direction: str, stake: float, expiry: int
) -> dict:
    try:
        symbol   = _to_deriv_symbol(pair)
        contract = "CALL" if direction == "call" else "PUT"
        duration = expiry * 60

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

        buy_data  = response["buy"]
        trade_id  = buy_data["contract_id"]
        buy_price = float(buy_data["buy_price"])

        open_trades[trade_id] = {
            "pair":      pair,
            "direction": direction,
            "stake":     stake,
            "expiry":    expiry,
            "buy_price": buy_price,
            "timestamp": datetime.now().isoformat(),
        }

        logger.success(
            f"✅ Trade placed! ID: {trade_id} | "
            f"{pair} {contract} ${stake}"
        )
        return {
            "success":    True,
            "trade_id":   trade_id,
            "pair":       pair,
            "direction":  direction,
            "stake":      stake,
            "expiry":     expiry,
            "entry_price": buy_price,
            "timestamp":  datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Trade execution error: {e}")
        return {"success": False, "error": str(e)}


def place_trade(
    pair: str, direction: str, stake: float, expiry: int = 5
) -> dict:
    try:
        if not ensure_connected():
            return {"success": False, "error": "Not connected"}

        direction = direction.lower()
        if direction not in ["call", "put"]:
            return {"success": False, "error": "Direction must be call or put"}

        balance = get_balance()
        if stake > balance:
            logger.warning(f"⚠️ Stake ${stake} exceeds balance ${balance}")
            return {"success": False, "error": "Insufficient balance"}

        logger.info(
            f"⚡ Placing trade: {pair} "
            f"{direction.upper()} ${stake} {expiry}min"
        )
        return _run(_place_trade_async(pair, direction, stake, expiry))

    except Exception as e:
        logger.error(f"❌ place_trade error: {e}")
        return {"success": False, "error": str(e)}


async def _check_trade_result_async(trade_id: int) -> dict:
    try:
        payload  = {"proposal_open_contract": 1, "contract_id": trade_id}
        response = await _send_receive(payload, timeout=15)

        if "error" in response:
            logger.error(
                f"❌ Result check error: {response['error']['message']}"
            )
            return {"result": "unknown", "profit": 0}

        contract = response.get("proposal_open_contract", {})
        status   = contract.get("status", "open")

        if status == "open":
            logger.info(f"⏳ Trade {trade_id} still open...")
            return {"result": "open", "profit": 0}

        profit = float(contract.get("profit", 0))

        exit_price = float(contract.get("exit_tick_display_value", 0) or contract.get("current_spot", 0) or 0)

        if profit > 0:
            logger.success(
                f"✅ Trade {trade_id} → WIN! Profit: ${profit:.2f}"
            )
            return {"result": "WIN", "profit": profit, "exit_price": exit_price}
        else:
            logger.warning(
                f"❌ Trade {trade_id} → LOSS! ${profit:.2f}"
            )
            return {"result": "LOSS", "profit": profit, "exit_price": exit_price}

    except Exception as e:
        logger.error(f"❌ Failed to check trade result: {e}")
        return {"result": "unknown", "profit": 0}


def check_trade_result(trade_id: int) -> dict:
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
        print(f"\n🔍 Testing V75 candles...")
        candles = get_candles("V75", 5, 10)
        if candles:
            print(f"✅ Got {len(candles)} candles!")
            print(f"   Latest close: {candles[-1]['close']}")
        else:
            print("❌ No candles returned!")
        disconnect()
    else:
        print("\n❌ Connection failed!")