# ⚡ APEX ORACLE — AO-1.0
# Groq AI Brain — Intelligent Trade Decision
# Uses Groq's FREE LLaMA3 model to reason like
# a professional trader before every trade
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import json
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────

def get_groq_client():
    from groq import Groq
    """Initialize Groq client"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY missing from .env!")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────

def build_trade_prompt(trade_data: dict) -> str:
    """
    Build a detailed prompt for Groq AI
    Gives it all market context to make decision
    """
    return f"""You are APEX ORACLE, an expert binary options trading AI.
Analyze this market data and make a trading decision.

TRADING PAIR: {trade_data.get('pair', 'EURUSD-OTC')}
TIMEFRAME: {trade_data.get('timeframe', '5min')}
EXPIRY: {trade_data.get('expiry', '5 minutes')}

TECHNICAL INDICATORS:
- RSI ({trade_data.get('rsi_period', 14)}): {trade_data.get('rsi_value', 'N/A')} → Signal: {trade_data.get('rsi_signal', 'N/A')}
- MACD: Signal = {trade_data.get('macd_signal', 'N/A')}
- Bollinger Bands: {trade_data.get('bb_signal', 'N/A')}
- EMA Cross (9/21): {trade_data.get('ema_signal', 'N/A')}
- Volume: {trade_data.get('volume_signal', 'N/A')}
- Indicators Agreeing: {trade_data.get('indicators_agree', 0)}/5

CANDLESTICK PATTERN:
- Pattern: {trade_data.get('pattern', 'None')}
- Direction: {trade_data.get('pattern_direction', 'NEUTRAL')}
- Strength: {trade_data.get('pattern_strength', 0)}/10

VOLATILITY:
- Level: {trade_data.get('volatility_level', 'MEDIUM')}
- ATR: {trade_data.get('atr', 'N/A')}
- Tradeable: {trade_data.get('volatility_tradeable', True)}

MARKET SENTIMENT:
- Score: {trade_data.get('sentiment_score', 0)} (-100 bearish to +100 bullish)
- Bias: {trade_data.get('sentiment_bias', 'NEUTRAL')}
- High Impact News: {trade_data.get('news_blocked', False)}

TIMEFRAME AGREEMENT:
- Timeframes Agreeing: {trade_data.get('tf_agreements', 0)}/4
- Primary Direction: {trade_data.get('primary_direction', 'N/A')}

CONFLUENCE SCORE: {trade_data.get('confluence_score', 0)}/100
CURRENT TIME (WAT): {trade_data.get('current_time', datetime.now().strftime('%H:%M'))}
ACCOUNT BALANCE: ${trade_data.get('balance', 0):.2f}
TRADES TODAY: {trade_data.get('trades_today', 0)}

Based on ALL this data, provide your trading decision.
Respond ONLY with valid JSON in this exact format:
{{
    "decision": "CALL" or "PUT" or "SKIP",
    "confidence": <number 0-100>,
    "reasoning": "<2-3 sentences explaining why>",
    "risk_level": "LOW" or "MEDIUM" or "HIGH",
    "key_factors": ["factor1", "factor2", "factor3"]
}}

Rules:
- Only say CALL or PUT if confidence >= 80
- Say SKIP if any major red flags
- Be conservative — protecting capital is priority
- Never trade if news_blocked is True
- Never trade if volatility_tradeable is False"""


# ─────────────────────────────────────────────────
# GROQ AI DECISION
# ─────────────────────────────────────────────────

def get_ai_decision(trade_data: dict) -> dict:
    """
    Get Groq AI trading decision

    Returns:
    {
        "decision":    "CALL" / "PUT" / "SKIP",
        "confidence":  85,
        "reasoning":   "Strong bullish momentum...",
        "risk_level":  "LOW",
        "key_factors": [...],
        "approved":    True/False
    }
    """
    try:
        # Block if news or volatility bad
        if trade_data.get("news_blocked", False):
            return {
                "decision":    "SKIP",
                "confidence":  0,
                "reasoning":   "High impact news detected. Trading blocked.",
                "risk_level":  "HIGH",
                "key_factors": ["High impact news"],
                "approved":    False,
            }

        if not trade_data.get("volatility_tradeable", True):
            return {
                "decision":    "SKIP",
                "confidence":  0,
                "reasoning":   "Volatility conditions not suitable for trading.",
                "risk_level":  "HIGH",
                "key_factors": ["Bad volatility"],
                "approved":    False,
            }

        client = get_groq_client()
        prompt = build_trade_prompt(trade_data)

        logger.info("🧠 Asking Groq AI for trade decision...")

        response = client.chat.completions.create(
            model    = "llama3-70b-8192",
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert binary options trading AI. "
                        "You ALWAYS respond with valid JSON only. "
                        "No explanations outside the JSON. "
                        "Be conservative and protect capital."
                    )
                },
                {
                    "role":    "user",
                    "content": prompt,
                }
            ],
            max_tokens  = 500,
            temperature = 0.1,   # Low temperature = consistent decisions
        )

        # ── Parse response ────────────────────────
        content = response.choices[0].message.content.strip()

        # Clean JSON if wrapped in backticks
        content = content.replace("```json", "").replace("```", "").strip()

        ai_result = json.loads(content)

        decision   = ai_result.get("decision",   "SKIP")
        confidence = ai_result.get("confidence", 0)
        reasoning  = ai_result.get("reasoning",  "No reasoning provided")
        risk_level = ai_result.get("risk_level", "HIGH")
        key_factors= ai_result.get("key_factors", [])

        # ── Validate decision ─────────────────────
        if decision not in ["CALL", "PUT", "SKIP"]:
            decision = "SKIP"

        # Only approve if confidence >= 80
        approved = (
            decision in ["CALL", "PUT"] and
            confidence >= 80
        )

        result = {
            "decision":    decision,
            "confidence":  confidence,
            "reasoning":   reasoning,
            "risk_level":  risk_level,
            "key_factors": key_factors,
            "approved":    approved,
        }

        emoji = "✅" if approved else "❌"
        logger.info(
            f"🧠 Groq AI: {emoji} {decision} | "
            f"Confidence: {confidence}% | "
            f"Risk: {risk_level}"
        )
        logger.debug(f"🧠 Reasoning: {reasoning}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"❌ Groq AI returned invalid JSON: {e}")
        return {
            "decision":    "SKIP",
            "confidence":  0,
            "reasoning":   "AI response parsing failed",
            "risk_level":  "HIGH",
            "key_factors": ["Parse error"],
            "approved":    False,
        }
    except Exception as e:
        logger.error(f"❌ Groq AI error: {e}")
        return {
            "decision":    "SKIP",
            "confidence":  0,
            "reasoning":   f"AI error: {str(e)}",
            "risk_level":  "HIGH",
            "key_factors": ["AI unavailable"],
            "approved":    False,
        }


# ─────────────────────────────────────────────────
# WEEKLY EVOLUTION ANALYSIS
# ─────────────────────────────────────────────────

def analyze_weekly_performance(weekly_stats: dict) -> dict:
    """
    Ask Groq AI to analyze weekly performance
    and suggest strategy improvements
    """
    try:
        client = get_groq_client()

        prompt = f"""You are APEX ORACLE's strategy optimizer.
Analyze this week's trading performance and suggest improvements.

WEEKLY STATS:
- Total Trades: {weekly_stats.get('total_trades', 0)}
- Wins: {weekly_stats.get('wins', 0)}
- Losses: {weekly_stats.get('losses', 0)}
- Win Rate: {weekly_stats.get('win_rate', 0)}%
- Profit/Loss: ${weekly_stats.get('profit_loss', 0):.2f}
- Top Patterns: {weekly_stats.get('top_patterns', [])}
- Weak Patterns: {weekly_stats.get('weak_patterns', [])}

Respond ONLY with valid JSON:
{{
    "analysis": "<2-3 sentences about performance>",
    "top_strategy": "<what worked best>",
    "avoid_strategy": "<what to avoid next week>",
    "confidence_adjustment": <number -10 to +10>,
    "recommendations": ["rec1", "rec2", "rec3"]
}}"""

        response = client.chat.completions.create(
            model    = "llama3-70b-8192",
            messages = [
                {
                    "role":    "system",
                    "content": "You are a trading strategy optimizer. Respond with valid JSON only."
                },
                {
                    "role":    "user",
                    "content": prompt,
                }
            ],
            max_tokens  = 600,
            temperature = 0.2,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result  = json.loads(content)

        logger.success("✅ Weekly evolution analysis complete!")
        return result

    except Exception as e:
        logger.error(f"❌ Weekly analysis error: {e}")
        return {
            "analysis":               "Analysis unavailable",
            "top_strategy":           "Continue current approach",
            "avoid_strategy":         "No specific patterns to avoid",
            "confidence_adjustment":  0,
            "recommendations":        ["Monitor performance closely"],
        }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Groq AI Brain Test")
    print("─" * 45)

    test_data = {
        "pair":                "EURUSD-OTC",
        "timeframe":           "5min",
        "expiry":              "5 minutes",
        "rsi_value":           28.5,
        "rsi_signal":          "CALL",
        "macd_signal":         "CALL",
        "bb_signal":           "CALL",
        "ema_signal":          "CALL",
        "volume_signal":       "CALL",
        "indicators_agree":    5,
        "pattern":             "Bullish Engulfing",
        "pattern_direction":   "CALL",
        "pattern_strength":    9,
        "volatility_level":    "MEDIUM",
        "volatility_tradeable": True,
        "sentiment_score":     45.0,
        "sentiment_bias":      "BULLISH",
        "news_blocked":        False,
        "tf_agreements":       3,
        "primary_direction":   "CALL",
        "confluence_score":    88.0,
        "balance":             10000.00,
        "trades_today":        3,
    }

    print("\nSending data to Groq AI...")
    result = get_ai_decision(test_data)

    print(f"\nDecision:    {result['decision']}")
    print(f"Confidence:  {result['confidence']}%")
    print(f"Approved:    {result['approved']}")
    print(f"Risk Level:  {result['risk_level']}")
    print(f"Reasoning:   {result['reasoning']}")
    print(f"Key Factors: {result['key_factors']}")
