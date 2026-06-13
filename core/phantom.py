# ⚡ APEX ORACLE — PHANTOM MODE ENGINE
# core/phantom.py
# "Invisible. Unpredictable. Lethal."
# Anti-detection execution engine — data-driven randomness
# ─────────────────────────────────────────────────

import random
import hashlib
from datetime import datetime, date
from zoneinfo import ZoneInfo
from loguru import logger

LAGOS = ZoneInfo("Africa/Lagos")

# ─────────────────────────────────────────────────
# WINNING HOURS — derived from Supabase analysis
# All times in WAT (Lagos)
# ─────────────────────────────────────────────────
HOUR_WEIGHTS = {
    18: 100,   # 100% win rate — PRIMARY
    19: 90,    # 80% win rate  — PRIMARY
    22: 80,    # 100% win rate — SECONDARY (small sample)
    23: 70,    # 62.5% win rate — SECONDARY
    12: 60,    # 54.5% win rate — TERTIARY
    5:  40,    # 100% win rate (tiny sample — cautious)
    6:  40,    # 100% win rate (tiny sample — cautious)
    9:  30,    # 50% win rate  — LOW
    # Everything else = 0 (dead zone)
}

DEAD_HOURS = [0, 1, 2, 3, 4, 13, 14, 15, 16, 17, 20, 21]

# ─────────────────────────────────────────────────
# PHANTOM ENGINE CLASS
# ─────────────────────────────────────────────────
class PhantomEngine:

    def __init__(self, account_id: str = "APEX"):
        self.account_id = account_id
        self.daily_target    = 0
        self.daily_seed      = 0
        self.trade_count     = 0
        self.last_trade_time = None
        self.burst_mode      = False
        self.burst_trades    = 0
        self.burst_limit     = 0
        self.current_date    = None
        self.activity_map    = {}
        self._initialize_day()

    # ─────────────────────────────────────────────
    # DAILY INITIALIZATION
    # ─────────────────────────────────────────────
    def _initialize_day(self):
        now       = datetime.now(LAGOS)
        today     = now.date()

        if self.current_date == today:
            return  # Already initialized for today

        self.current_date = today
        self.trade_count  = 0
        self.last_trade_time = None
        self.burst_mode   = False
        self.burst_trades = 0

        # Generate unique daily seed
        seed_string = f"{self.account_id}{today.year}{today.timetuple().tm_yday}{today.isocalendar()[1]}"
        seed_hash   = int(hashlib.md5(seed_string.encode()).hexdigest(), 16) % (10**8)
        self.daily_seed = seed_hash
        random.seed(self.daily_seed)

        # Random daily target between 12 and 18
        self.daily_target = random.randint(12, 18)

        # Generate hourly activity scores for today
        self._generate_activity_map()

        # Decide burst windows for today (1 or 2 burst periods)
        self._plan_burst_windows()

        logger.info(f"⚡ PHANTOM MODE initialized")
        logger.info(f"📅 Date: {today} | Seed: {seed_hash}")
        logger.info(f"🎯 Daily Target: {self.daily_target} trades")
        logger.info(f"🗺️ Activity Map: {self.activity_map}")

    # ─────────────────────────────────────────────
    # GENERATE HOURLY ACTIVITY SCORES
    # ─────────────────────────────────────────────
    def _generate_activity_map(self):
        self.activity_map = {}
        for hour in range(24):
            base_weight = HOUR_WEIGHTS.get(hour, 0)
            if base_weight == 0:
                self.activity_map[hour] = 0
            else:
                # Add daily randomness — vary by ±20 points
                variation = random.randint(-20, 20)
                score = max(10, min(100, base_weight + variation))
                self.activity_map[hour] = score

    # ─────────────────────────────────────────────
    # PLAN BURST WINDOWS
    # ─────────────────────────────────────────────
    def _plan_burst_windows(self):
        # Pick 1 or 2 random winning hours for burst trading
        winning_hours = [h for h, w in HOUR_WEIGHTS.items() if w >= 60]
        num_bursts    = random.randint(1, 2)
        self.burst_hours = random.sample(winning_hours, min(num_bursts, len(winning_hours)))
        self.burst_limit = random.randint(3, 5)  # 3–5 trades in burst
        logger.info(f"💥 Burst windows planned: hours {self.burst_hours} | limit {self.burst_limit}")

    # ─────────────────────────────────────────────
    # CORE GATE — Should the bot trade right now?
    # ─────────────────────────────────────────────
    def should_trade(self) -> tuple[bool, str]:
        self._initialize_day()  # Re-init if new day

        now  = datetime.now(LAGOS)
        hour = now.hour

        # 1. Daily target reached
        if self.trade_count >= self.daily_target:
            return False, f"Daily target reached ({self.trade_count}/{self.daily_target})"

        # 2. Dead zone — never trade
        if hour in DEAD_HOURS:
            return False, f"Dead zone — hour {hour}:00 WAT is a losing hour"

        # 3. Activity score check
        score = self.activity_map.get(hour, 0)
        if score == 0:
            return False, f"Hour {hour}:00 WAT has zero activity score"

        # 4. Reserve 6 trades for golden hours 18:00-19:00 WAT
        if hour not in [18, 19]:
            remaining = self.daily_target - self.trade_count
            if remaining <= 6:
                return False, f"🔒 Reserving last 6 trades for golden hours 18:00-19:00 WAT"

        # 4. Cooldown check
        if self.last_trade_time:
            cooldown = self._get_dynamic_cooldown()
            elapsed  = (now - self.last_trade_time).total_seconds() / 60
            if elapsed < cooldown:
                remaining = round(cooldown - elapsed, 1)
                return False, f"Cooldown active — {remaining} min remaining"

        # 5. Burst mode check
        if hour in self.burst_hours:
            if self.burst_trades < self.burst_limit:
                return True, f"BURST MODE — trade {self.burst_trades + 1}/{self.burst_limit}"

        # 6. Random participation based on activity score
        roll = random.randint(1, 100)
        if roll > score:
            return False, f"Random skip — score {score}, rolled {roll}"

        return True, f"PHANTOM APPROVED — hour {hour}:00 WAT score {score}"

    # ─────────────────────────────────────────────
    # DYNAMIC COOLDOWN
    # ─────────────────────────────────────────────
    def _get_dynamic_cooldown(self) -> float:
        now  = datetime.now(LAGOS)
        hour = now.hour

        remaining_trades = self.daily_target - self.trade_count
        progress         = self.trade_count / max(self.daily_target, 1)

        # Base cooldown: 3–45 minutes
        base = random.uniform(3, 45)

        # Late day — reduce cooldown if behind target
        if hour >= 21 and remaining_trades > 5:
            base = random.uniform(2, 15)

        # Early day — more conservative
        elif progress < 0.3:
            base = random.uniform(10, 45)

        # Burst mode — very short cooldown
        elif self.burst_mode:
            base = random.uniform(2, 8)

        return round(base, 1)

    # ─────────────────────────────────────────────
    # RECORD TRADE COMPLETION
    # ─────────────────────────────────────────────
    def record_trade(self, result: str = None):
        self.trade_count    += 1
        self.last_trade_time = datetime.now(LAGOS)

        now  = datetime.now(LAGOS)
        hour = now.hour

        # Track burst trades
        if hour in self.burst_hours:
            self.burst_trades += 1
            if self.burst_trades >= self.burst_limit:
                self.burst_mode  = False
                self.burst_trades = 0
                logger.info(f"💥 Burst window complete — entering rest period")
        else:
            self.burst_mode = False

        cooldown = self._get_dynamic_cooldown()
        logger.info(f"⚡ PHANTOM — Trade {self.trade_count}/{self.daily_target} recorded")
        logger.info(f"⏱️ Next cooldown: {cooldown} min")

    # ─────────────────────────────────────────────
    # STATUS REPORT
    # ─────────────────────────────────────────────
    def get_status(self) -> dict:
        self._initialize_day()
        now  = datetime.now(LAGOS)
        hour = now.hour
        return {
            "date":            str(self.current_date),
            "daily_target":    self.daily_target,
            "trade_count":     self.trade_count,
            "remaining":       self.daily_target - self.trade_count,
            "current_hour":    hour,
            "hour_score":      self.activity_map.get(hour, 0),
            "in_dead_zone":    hour in DEAD_HOURS,
            "burst_hours":     self.burst_hours,
            "burst_mode":      self.burst_mode,
            "seed":            self.daily_seed,
        }


# ─────────────────────────────────────────────────
# SINGLETON — one instance for the whole bot
# ─────────────────────────────────────────────────
phantom = PhantomEngine(account_id="APEX_ORACLE")