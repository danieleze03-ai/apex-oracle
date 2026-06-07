# ⚡ APEX ORACLE — AO-1.0
# Keep Alive Server
# Prevents Render.com free tier from sleeping
# cron-job.org pings /ping every 10 minutes
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import threading
from datetime import datetime
from flask import Flask, jsonify
from loguru import logger

# ─────────────────────────────────────────────────
# FLASK APP
# ─────────────────────────────────────────────────
app = Flask(__name__)

# Track when bot started
START_TIME = datetime.now()

# Bot status (updated by main.py)
bot_status = {
    "running":      False,
    "mode":         "PRACTICE",
    "trades_today": 0,
    "wins_today":   0,
    "losses_today": 0,
    "balance":      0.0,
    "last_signal":  None,
    "last_trade":   None,
    "uptime":       "0 minutes",
}


# ─────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────

@app.route("/")
def home():
    """Home page — shows bot is alive"""
    uptime = datetime.now() - START_TIME
    hours   = int(uptime.total_seconds() // 3600)
    minutes = int((uptime.total_seconds() % 3600) // 60)

    return f"""
    <html>
    <head>
        <title>⚡ APEX ORACLE</title>
        <style>
            body {{
                background: #0a0a0a;
                color: #00ff88;
                font-family: 'Courier New', monospace;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                border: 1px solid #00ff88;
                border-radius: 10px;
                max-width: 500px;
            }}
            h1 {{ font-size: 2.5em; margin-bottom: 5px; }}
            .motto {{ color: #888; margin-bottom: 30px; }}
            .status {{ 
                background: #111;
                padding: 20px;
                border-radius: 8px;
                text-align: left;
                margin-top: 20px;
            }}
            .green {{ color: #00ff88; }}
            .red   {{ color: #ff4444; }}
            .gold  {{ color: #ffd700; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ APEX ORACLE</h1>
            <p class="motto">"We Don't Predict. We Know."</p>
            <p class="green">● SYSTEM ONLINE</p>
            
            <div class="status">
                <p>🕐 Uptime: <span class="gold">{hours}h {minutes}m</span></p>
                <p>🤖 Bot: <span class="{'green' if bot_status['running'] else 'red'}">
                    {'TRADING' if bot_status['running'] else 'STANDBY'}</span></p>
                <p>📊 Mode: <span class="gold">{bot_status['mode']}</span></p>
                <p>💰 Balance: <span class="gold">${bot_status['balance']:.2f}</span></p>
                <p>📈 Trades Today: <span class="gold">{bot_status['trades_today']}</span></p>
                <p>✅ Wins: <span class="green">{bot_status['wins_today']}</span> 
                   ❌ Losses: <span class="red">{bot_status['losses_today']}</span></p>
            </div>
            
            <p style="color:#444; margin-top:20px; font-size:0.8em;">
                AO-1.0 | Version 1.0
            </p>
        </div>
    </body>
    </html>
    """


@app.route("/ping")
def ping():
    """
    Ping endpoint — called by cron-job.org every 10 minutes
    Keeps Render from sleeping
    """
    logger.debug("⚡ Ping received — APEX ORACLE is alive!")
    return jsonify({
        "status":    "alive",
        "bot":       "APEX ORACLE",
        "version":   "AO-1.0",
        "timestamp": datetime.now().isoformat(),
        "uptime":    str(datetime.now() - START_TIME),
        "trading":   bot_status["running"],
        "mode":      bot_status["mode"],
    })


@app.route("/status")
def status():
    """Full status endpoint"""
    uptime = datetime.now() - START_TIME

    win_rate = 0
    if bot_status["trades_today"] > 0:
        win_rate = (bot_status["wins_today"] / bot_status["trades_today"]) * 100

    return jsonify({
        "bot":          "APEX ORACLE",
        "version":      "AO-1.0",
        "motto":        "We Don't Predict. We Know.",
        "status":       "running" if bot_status["running"] else "standby",
        "mode":         bot_status["mode"],
        "uptime":       str(uptime),
        "balance":      bot_status["balance"],
        "trades_today": bot_status["trades_today"],
        "wins_today":   bot_status["wins_today"],
        "losses_today": bot_status["losses_today"],
        "win_rate":     f"{win_rate:.1f}%",
        "last_signal":  bot_status["last_signal"],
        "last_trade":   bot_status["last_trade"],
        "timestamp":    datetime.now().isoformat(),
    })


@app.route("/health")
def health():
    """Health check for Render"""
    return jsonify({"health": "ok"}), 200


# ─────────────────────────────────────────────────
# STATUS UPDATER
# ─────────────────────────────────────────────────

def update_status(key: str, value):
    """
    Update bot status from main.py
    Example: update_status("balance", 10500.00)
    """
    global bot_status
    bot_status[key] = value
    logger.debug(f"Status updated: {key} = {value}")


# ─────────────────────────────────────────────────
# SERVER RUNNER
# ─────────────────────────────────────────────────

def run_server():
    """Run Flask server in background thread"""
    port = int(os.getenv("PORT", 10000))
    logger.info(f"⚡ Keep-Alive server starting on port {port}")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


def start_keep_alive():
    """
    Start keep-alive server in background thread
    Call this from main.py at startup
    """
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.success("✅ Keep-Alive server started in background")
    return thread


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Keep Alive Server")
    print("Testing server on http://localhost:10000")
    print("Visit: http://localhost:10000/ping")
    print("Press Ctrl+C to stop\n")

    # Simulate bot running for test
    bot_status["running"] = True
    bot_status["mode"]    = "PRACTICE"
    bot_status["balance"] = 10000.00

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)