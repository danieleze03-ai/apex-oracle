# ⚡ APEX ORACLE — AO-1.0
> *"We Don't Predict. We Know."*

The world's most intelligent FREE binary options trading bot.
Built for IQ Option | Powered by AI | Hosted on Render (FREE)

---

## 🚀 What Makes APEX ORACLE Different

| Feature | Normal Bots | APEX ORACLE |
|---------|------------|-------------|
| Signal Source | 1 indicator | 5 indicators + AI |
| Timeframes | 1 | 4 simultaneous |
| AI Brain | None | Groq AI (FREE) |
| Sentiment Aware | No | Yes |
| Self Learning | No | Every Sunday |
| Manipulation Guard | No | Yes |
| Shadow Trading | No | Yes |
| Cost | $20-100/mo | $0 forever |

---

## 📁 Project Structure

```
apex-oracle/
├── core/
│   ├── logger.py         # Logging system
│   ├── signals.py        # Indicator engine
│   ├── patterns.py       # Candlestick AI
│   ├── confluence.py     # MTF scorer
│   └── volatility.py     # Thermometer
├── intelligence/
│   ├── groq_brain.py     # AI decisions
│   ├── sentiment.py      # News analysis
│   └── evolution.py      # Self learning
├── broker/
│   ├── iqoption.py       # Connection
│   ├── executor.py       # Trade execution
│   └── guard.py          # Manipulation check
├── management/
│   ├── risk.py           # Money management
│   ├── session.py        # Time management
│   └── shadow.py         # Shadow trading
├── communication/
│   ├── telegram.py       # Command center
│   └── reports.py        # Trade journal
├── data/
│   ├── database.py       # Supabase
│   └── backup.py         # Google Drive
├── server/
│   └── keep_alive.py     # Render ping
├── config.py             # All settings
├── main.py               # Orchestrator
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ⚙️ Setup Instructions

### Step 1 — Clone & Install
```bash
git clone https://github.com/yourusername/apex-oracle.git
cd apex-oracle
pip install -r requirements.txt
```

### Step 2 — Environment Variables
```bash
cp .env.example .env
# Edit .env with your real values
```

### Step 3 — Get Free API Keys

**Groq AI (FREE):**
1. Go to console.groq.com
2. Sign up free
3. Create API key
4. Add to .env as GROQ_API_KEY

**Telegram Bot (FREE):**
1. Open Telegram → search @BotFather
2. Send /newbot
3. Copy the token → TELEGRAM_BOT_TOKEN
4. Open @userinfobot → copy your ID → TELEGRAM_CHAT_ID

**Supabase (FREE):**
1. Go to supabase.com
2. Create new project (free)
3. Settings → API → copy URL and anon key

### Step 4 — Test Locally
```bash
python config.py   # Verify all settings
python main.py     # Start the bot
```

### Step 5 — Deploy to Render (FREE)
1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect your GitHub repo
4. Add all environment variables
5. Deploy!

### Step 6 — Keep Alive (FREE)
1. Go to cron-job.org
2. Create new cron job
3. URL: https://your-app.onrender.com/ping
4. Schedule: every 10 minutes
5. Bot never sleeps!

---

## 📱 Telegram Commands

| Command | Action |
|---------|--------|
| /status | Bot health + activity |
| /pause | Pause all trading |
| /resume | Resume trading |
| /report | Today's performance |
| /balance | Current balance |
| /history | Last 10 trades |
| /mode demo | Switch to demo |
| /mode live | Switch to live |
| /risk low | Conservative (0.5%) |
| /risk high | Aggressive (2%) |
| /shutdown | Emergency stop |

---

## ⚠️ Risk Warning

Binary options trading involves significant risk.
- ALWAYS test on DEMO first (minimum 2 weeks)
- Only trade with money you can afford to lose
- Past performance does not guarantee future results
- APEX ORACLE is a tool, not a guarantee

---

## 💰 Total Cost

```
Everything = $0 (FREE)
─────────────────────
Groq AI:      FREE
Render:       FREE  
Supabase:     FREE
Telegram:     FREE
GitHub:       FREE
cron-job.org: FREE
─────────────────────
TOTAL:        $0/month
```

---

*⚡ APEX ORACLE — Built to win. Designed to protect.*
