# ⚡ APEX ORACLE — AO-1.0
# Groq AI Brain — Intelligent Trade Decision
# Uses Groq's FREE LLaMA model to reason like
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
    rsi_period = trade_data.get('rsi_period', 14)
    return f"""You are APEX ORACLE, an expert binary options trading AI specializing in Synthetic Indices.
Analyze this market data and make a trading decision.

TRADING PAIR: {trade_data.get('pair', 'V75')} (Synthetic Index — trades 24/7, no news impact)
TIMEFRAME: {trade_data.get('timeframe', '5min')}
EXPIRY: {trade_data.get('expiry', '5 minutes')}

TECHNICAL INDICATORS:
- RSI ({rsi_period}): {trade_data.get('rsi_value', 'N/A')} → Signal: {trade_data.get('rsi_signal', 'N/A')}
- MACD: Signal = {trade_data.get('macd_signal', 'N/A')}
- Bollinger Bands: {trade_data.get('bb_signal', 'N/A')}
- EMA Cross (9/21): {trade_data.get('ema_signal', 'N/A')}
- StochRSI: {trade_data.get('stochrsi_signal', 'N/A')}
- Indicators Agreeing: {trade_data.get('indicators_agree', 0)}/5

CANDLESTICK PATTERN:
- Pattern: {trade_data.get('pattern', 'None')}
- Direction: {trade_data.get('pattern_direction', 'NEUTRAL')}
- Strength: {trade_data.get('pattern_strength', 0)}/10

VOLATILITY:
- Level: {trade_data.get('volatility_level', 'MEDIUM')}
- Tradeable: {trade_data.get('volatility_tradeable', True)}

TIMEFRAME AGREEMENT:
- Timeframes Agreeing: {trade_data.get('tf_agreements', 0)}/4
- Primary Direction: {trade_data.get('primary_direction', 'N/A')}

CONFLUENCE SCORE: {trade_data.get('confluence_score', 0)}/100
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
- Only say CALL or PUT if confidence >= 70
- Say SKIP if confluence score is below 65
- Be conservative — protecting capital is priority
- This is a Synthetic Index — ignore news, focus only on technicals"""


# ─────────────────────────────────────────────────
# GROQ AI DECISION — WITH JSON FALLBACK
# ─────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"  # ← Updated model (llama3-70b-8192 decommissioned)


def get_ai_decision(trade_data: dict) -> dict:
    """
    Get Groq AI trading decision with robust JSON fallback
    """
    try:
        client = get_groq_client()
        prompt = build_trade_prompt(trade_data)

        logger.info("🧠 Asking Groq AI for trade decision...")

        response = client.chat.completions.create(
            model    = GROQ_MODEL,
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert Synthetic Index trading AI. "
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
            temperature = 0.1,
        )

        # ── Parse response ───────────────────────
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            ai_result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("⚠️ Groq returned malformed JSON. Retrying...")
            retry_response = client.chat.completions.create(
                model    = GROQ_MODEL,
                messages = [
                    {
                        "role": "system",
                        "content": "You MUST respond with VALID JSON only. No markdown, no backticks, no explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nIMPORTANT: Respond with valid JSON only. Example: {\"decision\": \"SKIP\", \"confidence\": 0, \"reasoning\": \"Invalid data\", \"risk_level\": \"HIGH\", \"key_factors\": []}"
                    }
                ],
                max_tokens  = 500,
                temperature = 0.1,
            )
            content = retry_response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            try:
                ai_result = json.loads(content)
            except json.JSONDecodeError:
                logger.error("❌ Groq returned malformed JSON after retry. Using safe fallback.")
                return {
                    "decision":    "SKIP",
                    "confidence":  0,
                    "reasoning":   "AI response parsing failed after retry",
                    "risk_level":  "HIGH",
                    "key_factors": ["Parse error"],
                    "approved":    False,
                }

        decision    = ai_result.get("decision",    "SKIP")
        confidence  = ai_result.get("confidence",  0)
        reasoning   = ai_result.get("reasoning",   "No reasoning provided")
        risk_level  = ai_result.get("risk_level",  "HIGH")
        key_factors = ai_result.get("key_factors", [])

        if decision not in ["CALL", "PUT", "SKIP"]:
            decision = "SKIP"

        # Approve if confidence >= 70 (lowered from 80 for synthetics)
        approved = (
            decision in ["CALL", "PUT"] and
            confidence >= 70
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

    except Exception as e:
        logger.error(f"❌ Groq AI error: {e}")
        # ── Fallback: approve based on confluence score alone ──
        confluence  = float(trade_data.get("confluence_score", 0))
        direction   = trade_data.get("primary_direction", "SKIP")
        approved    = confluence >= 65 and direction in ["CALL", "PUT"]
        logger.warning(
            f"⚠️ Groq unavailable — fallback decision: "
            f"{'APPROVED' if approved else 'SKIP'} "
            f"(confluence: {confluence}%)"
        )
        return {
            "decision":    direction if approved else "SKIP",
            "confidence":  confluence,
            "reasoning":   "Groq unavailable — approved by confluence score alone",
            "risk_level":  "MEDIUM",
            "key_factors": ["Groq fallback", f"Confluence: {confluence}%"],
            "approved":    approved,
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

        prompt = f"""You are APEX ORACLE's strategy optimizer for Synthetic Indices trading.
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
            model    = GROQ_MODEL,
            messages = [
                {
                    "role":    "system",
                    "content": "You are a Synthetic Index trading strategy optimizer. Respond with valid JSON only."
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
            "analysis":              "Analysis unavailable",
            "top_strategy":          "Continue current approach",
            "avoid_strategy":        "No specific patterns to avoid",
            "confidence_adjustment": 0,
            "recommendations":       ["Monitor performance closely"],
        }


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Groq AI Brain Test")
    print("─" * 45)

    test_data = {
        "pair":                 "V75",
        "timeframe":            "5min",
        "expiry":               "5 minutes",
        "rsi_value":            28.5,
        "rsi_signal":           "CALL",
        "macd_signal":          "CALL",
        "bb_signal":            "CALL",
        "ema_signal":           "CALL",
        "stochrsi_signal":      "CALL",
        "indicators_agree":     5,
        "pattern":              "Bullish Engulfing",
        "pattern_direction":    "CALL",
        "pattern_strength":     9,
        "volatility_level":     "MEDIUM",
        "volatility_tradeable": True,
        "tf_agreements":        3,
        "primary_direction":    "CALL",
        "confluence_score":     88.0,
        "balance":              10000.00,
        "trades_today":         3,
    }

    print("\nSending data to Groq AI...")
    result = get_ai_decision(test_data)

    print(f"\nDecision:    {result['decision']}")
    print(f"Confidence:  {result['confidence']}%")
    print(f"Approved:    {result['approved']}")
    print(f"Risk Level:  {result['risk_level']}")
    print(f"Reasoning:   {result['reasoning']}")
    print(f"Key Factors: {result['key_factors']}")
