# ⚡ APEX ORACLE — AO-1.0
# Decision Engine — Internal Confluence-Based
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

from loguru import logger


def get_ai_decision(trade_data: dict) -> dict:
    """
    Internal decision engine — no external API needed.
    Approves trade if confluence score >= 65.
    """
    confluence = float(trade_data.get("confluence_score", 0))
    direction  = trade_data.get("primary_direction", "SKIP")
    approved   = confluence >= 65 and direction in ["CALL", "PUT"]

    logger.info(
        f"🧠 Internal AI: {'✅ APPROVED' if approved else '❌ SKIP'} | "
        f"Confluence: {confluence}%"
    )

    return {
        "decision":    direction if approved else "SKIP",
        "confidence":  confluence,
        "reasoning":   f"Confluence score {confluence}% {'meets' if approved else 'below'} threshold",
        "risk_level":  "LOW" if confluence >= 80 else "MEDIUM",
        "key_factors": [f"Confluence: {confluence}%"],
        "approved":    approved,
    }


def analyze_weekly_performance(weekly_stats: dict) -> dict:
    """Simple weekly analysis — no external API"""
    wins   = weekly_stats.get("wins", 0)
    total  = weekly_stats.get("total_trades", 0)
    wr     = weekly_stats.get("win_rate", 0)
    pl     = weekly_stats.get("profit_loss", 0)

    return {
        "analysis":              f"{total} trades this week. Win rate: {wr}%. P&L: ${pl:.2f}",
        "top_strategy":          "Continue current confluence approach",
        "avoid_strategy":        "Avoid trading during low indicator agreement",
        "confidence_adjustment": 0,
        "recommendations":       ["Monitor win rate daily", "Keep stake sizes consistent"],
    }