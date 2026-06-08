# ⚡ APEX ORACLE — AO-1.0
# Self-Evolution System
# Every Sunday midnight bot reviews performance
# Identifies winning/losing patterns
# Adjusts strategy automatically
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import json
import os
from datetime import datetime, timedelta
from loguru import logger
from data.database import (
    get_weekly_stats,
    get_top_patterns,
    get_last_trades,
)
from intelligence.groq_brain import analyze_weekly_performance


# ─────────────────────────────────────────────────
# STRATEGY CONFIG
# Weights adjusted by evolution system weekly
# ─────────────────────────────────────────────────

STRATEGY_FILE = "strategy_config.json"

DEFAULT_STRATEGY = {
    "version":           1,
    "updated_at":        None,
    "min_confidence":    75,
    "indicator_weights": {
        "rsi":    1.0,
        "macd":   1.0,
        "bb":     1.0,
        "ema":    1.0,
        "volume": 1.0,
    },
    "pattern_weights": {},
    "avoid_patterns":  [],
    "top_patterns":    [],
    "performance_history": [],
}


# ─────────────────────────────────────────────────
# STRATEGY CONFIG MANAGER
# ─────────────────────────────────────────────────

def load_strategy() -> dict:
    """Load current strategy config"""
    try:
        if os.path.exists(STRATEGY_FILE):
            with open(STRATEGY_FILE, "r") as f:
                return json.load(f)
        return DEFAULT_STRATEGY.copy()
    except Exception as e:
        logger.error(f"❌ Failed to load strategy: {e}")
        return DEFAULT_STRATEGY.copy()


def save_strategy(strategy: dict) -> bool:
    """Save updated strategy config"""
    try:
        strategy["updated_at"] = datetime.now().isoformat()
        strategy["version"]    = strategy.get("version", 1) + 1
        with open(STRATEGY_FILE, "w") as f:
            json.dump(strategy, f, indent=2)
        logger.success(
            f"✅ Strategy saved! Version {strategy['version']}"
        )
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save strategy: {e}")
        return False


def get_current_min_confidence() -> int:
    """Get current minimum confidence from strategy"""
    strategy = load_strategy()
    return strategy.get("min_confidence", 75)


def get_pattern_weight(pattern_name: str) -> float:
    """Get weight for a specific pattern"""
    strategy = load_strategy()
    weights  = strategy.get("pattern_weights", {})
    return weights.get(pattern_name, 1.0)


def is_pattern_avoided(pattern_name: str) -> bool:
    """Check if pattern is in avoid list"""
    strategy = load_strategy()
    return pattern_name in strategy.get("avoid_patterns", [])


# ─────────────────────────────────────────────────
# PERFORMANCE ANALYZER
# ─────────────────────────────────────────────────

def analyze_pattern_performance(trades: list) -> dict:
    """
    Analyze which patterns performed best/worst

    Returns:
    {
        "top_patterns":  [("Bullish Engulfing", 80.0), ...],
        "weak_patterns": [("Doji", 30.0), ...],
    }
    """
    try:
        pattern_stats = {}

        for trade in trades:
            pattern = trade.get("pattern", "None")
            result  = trade.get("result", "")

            if not pattern or pattern == "None":
                continue

            if pattern not in pattern_stats:
                pattern_stats[pattern] = {"wins": 0, "total": 0}

            pattern_stats[pattern]["total"] += 1
            if result == "WIN":
                pattern_stats[pattern]["wins"] += 1

        # Calculate win rates
        pattern_rates = {}
        for pattern, stats in pattern_stats.items():
            if stats["total"] >= 3:
                win_rate = stats["wins"] / stats["total"] * 100
                pattern_rates[pattern] = round(win_rate, 1)

        # Sort by win rate
        sorted_patterns = sorted(
            pattern_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_patterns  = [p for p in sorted_patterns if p[1] >= 65][:5]
        weak_patterns = [p for p in sorted_patterns if p[1] < 45][:5]

        return {
            "top_patterns":  top_patterns,
            "weak_patterns": weak_patterns,
            "all_patterns":  sorted_patterns,
        }

    except Exception as e:
        logger.error(f"❌ Pattern analysis error: {e}")
        return {"top_patterns": [], "weak_patterns": [], "all_patterns": []}


def analyze_indicator_performance(trades: list) -> dict:
    """
    Analyze which time periods and sessions performed best
    """
    try:
        hourly_stats = {}

        for trade in trades:
            timestamp = trade.get("timestamp", "")
            result    = trade.get("result", "")

            if not timestamp:
                continue

            try:
                hour = datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                ).hour
            except:
                continue

            if hour not in hourly_stats:
                hourly_stats[hour] = {"wins": 0, "total": 0}

            hourly_stats[hour]["total"] += 1
            if result == "WIN":
                hourly_stats[hour]["wins"] += 1

        # Find best hours
        best_hours = []
        for hour, stats in hourly_stats.items():
            if stats["total"] >= 2:
                win_rate = stats["wins"] / stats["total"] * 100
                best_hours.append((hour, round(win_rate, 1)))

        best_hours.sort(key=lambda x: x[1], reverse=True)

        return {
            "best_hours":  best_hours[:3],
            "worst_hours": best_hours[-3:] if len(best_hours) >= 3 else [],
        }

    except Exception as e:
        logger.error(f"❌ Indicator performance error: {e}")
        return {"best_hours": [], "worst_hours": []}


# ─────────────────────────────────────────────────
# STRATEGY UPDATER
# ─────────────────────────────────────────────────

def update_strategy(
    weekly_stats:   dict,
    pattern_analysis: dict,
    ai_analysis:    dict,
) -> dict:
    """
    Update strategy based on weekly analysis

    Adjusts:
    - Minimum confidence threshold
    - Pattern weights
    - Avoid list
    """
    try:
        strategy = load_strategy()

        # ── Update pattern weights ────────────────
        top_patterns  = pattern_analysis.get("top_patterns",  [])
        weak_patterns = pattern_analysis.get("weak_patterns", [])

        for pattern, win_rate in top_patterns:
            # Boost winning patterns
            current = strategy["pattern_weights"].get(pattern, 1.0)
            strategy["pattern_weights"][pattern] = min(
                current * 1.1, 2.0
            )

        for pattern, win_rate in weak_patterns:
            # Reduce weak patterns
            current = strategy["pattern_weights"].get(pattern, 1.0)
            strategy["pattern_weights"][pattern] = max(
                current * 0.9, 0.3
            )

        # ── Update avoid list ─────────────────────
        strategy["avoid_patterns"] = [
            p[0] for p in weak_patterns
            if p[1] < 35   # Avoid patterns below 35% win rate
        ]

        # ── Update top patterns ───────────────────
        strategy["top_patterns"] = [
            p[0] for p in top_patterns
        ]

        # ── Adjust confidence threshold ───────────
        adj = ai_analysis.get("confidence_adjustment", 0)
        strategy["min_confidence"] = max(
            65,
            min(90, strategy["min_confidence"] + adj)
        )

        # ── Save performance history ──────────────
        strategy["performance_history"].append({
            "week":      datetime.now().strftime("%Y-W%W"),
            "win_rate":  weekly_stats.get("win_rate", 0),
            "trades":    weekly_stats.get("total_trades", 0),
            "pnl":       weekly_stats.get("profit_loss", 0),
        })

        # Keep only last 12 weeks
        strategy["performance_history"] = (
            strategy["performance_history"][-12:]
        )

        save_strategy(strategy)
        return strategy

    except Exception as e:
        logger.error(f"❌ Strategy update error: {e}")
        return load_strategy()


# ─────────────────────────────────────────────────
# WEEKLY EVOLUTION RUNNER
# ─────────────────────────────────────────────────

def run_weekly_evolution() -> dict:
    """
    Main evolution function — runs every Sunday midnight

    Steps:
    1. Get weekly stats from database
    2. Analyze pattern performance
    3. Ask Groq AI for insights
    4. Update strategy config
    5. Generate evolution report
    """
    try:
        logger.info("🧬 Starting weekly evolution process...")

        # ── Step 1: Get weekly data ───────────────
        weekly_stats = get_weekly_stats()
        trades       = weekly_stats.get("trades", [])

        if not trades:
            logger.warning("⚠️ No trades this week — skipping evolution")
            return {"success": False, "reason": "No trades this week"}

        # ── Step 2: Analyze patterns ──────────────
        pattern_analysis = analyze_pattern_performance(trades)
        hour_analysis    = analyze_indicator_performance(trades)

        # ── Step 3: Ask Groq AI ───────────────────
        ai_stats = {
            "total_trades":  weekly_stats.get("total_trades", 0),
            "wins":          weekly_stats.get("wins", 0),
            "losses":        weekly_stats.get("losses", 0),
            "win_rate":      weekly_stats.get("win_rate", 0),
            "profit_loss":   weekly_stats.get("profit_loss", 0),
            "top_patterns":  pattern_analysis["top_patterns"],
            "weak_patterns": pattern_analysis["weak_patterns"],
        }
        ai_analysis = analyze_weekly_performance(ai_stats)

        # ── Step 4: Update strategy ───────────────
        new_strategy = update_strategy(
            weekly_stats, pattern_analysis, ai_analysis
        )

        # ── Step 5: Build report ──────────────────
        report = {
            "success":      True,
            "week":         datetime.now().strftime("%Y-W%W"),
            "generated_at": datetime.now().isoformat(),
            "stats": {
                "total_trades": weekly_stats.get("total_trades", 0),
                "wins":         weekly_stats.get("wins", 0),
                "losses":       weekly_stats.get("losses", 0),
                "win_rate":     weekly_stats.get("win_rate", 0),
                "profit_loss":  weekly_stats.get("profit_loss", 0),
            },
            "top_patterns":      pattern_analysis["top_patterns"],
            "weak_patterns":     pattern_analysis["weak_patterns"],
            "avoid_patterns":    new_strategy["avoid_patterns"],
            "best_hours":        hour_analysis["best_hours"],
            "new_confidence":    new_strategy["min_confidence"],
            "ai_analysis":       ai_analysis.get("analysis", ""),
            "ai_top_strategy":   ai_analysis.get("top_strategy", ""),
            "ai_avoid":          ai_analysis.get("avoid_strategy", ""),
            "recommendations":   ai_analysis.get("recommendations", []),
            "strategy_version":  new_strategy["version"],
        }

        logger.success(
            f"🧬 Evolution complete! "
            f"Strategy v{new_strategy['version']} | "
            f"Win rate: {weekly_stats.get('win_rate', 0)}%"
        )

        return report

    except Exception as e:
        logger.error(f"❌ Evolution error: {e}")
        return {"success": False, "reason": str(e)}


# ─────────────────────────────────────────────────
# SCHEDULE CHECKER
# ─────────────────────────────────────────────────

def should_run_evolution() -> bool:
    """
    Check if evolution should run
    Runs every Sunday between midnight and 1am
    """
    now = datetime.now()
    return (
        now.weekday() == 6 and   # Sunday
        now.hour == 0 and        # Midnight
        now.minute < 30          # Within first 30 mins
    )


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Evolution System Test")
    print("─" * 45)

    print("\nTesting strategy load...")
    strategy = load_strategy()
    print(f"Strategy version: {strategy['version']}")
    print(f"Min confidence:   {strategy['min_confidence']}")
    print(f"Top patterns:     {strategy['top_patterns']}")
    print(f"Avoid patterns:   {strategy['avoid_patterns']}")

    print("\nTesting pattern analysis...")
    fake_trades = [
        {"pattern": "Bullish Engulfing", "result": "WIN"},
        {"pattern": "Bullish Engulfing", "result": "WIN"},
        {"pattern": "Bullish Engulfing", "result": "WIN"},
        {"pattern": "Doji",              "result": "LOSS"},
        {"pattern": "Doji",              "result": "LOSS"},
        {"pattern": "Doji",              "result": "WIN"},
        {"pattern": "Morning Star",      "result": "WIN"},
        {"pattern": "Morning Star",      "result": "WIN"},
        {"pattern": "Morning Star",      "result": "WIN"},
    ]

    analysis = analyze_pattern_performance(fake_trades)
    print(f"\nTop patterns:  {analysis['top_patterns']}")
    print(f"Weak patterns: {analysis['weak_patterns']}")

    print("\nShould run evolution now?")
    print(f"Answer: {should_run_evolution()}")