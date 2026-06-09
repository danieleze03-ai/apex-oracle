# ⚡ APEX ORACLE — AO-1.0
# Sentiment Analysis Engine
# Scrapes news and measures market mood
# Bullish sentiment = favor CALL
# Bearish sentiment = favor PUT
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import re
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────
# FOREX KEYWORDS
# ─────────────────────────────────────────────────

BULLISH_WORDS = [
    "surge", "rally", "gain", "rise", "higher", "bullish",
    "strong", "positive", "growth", "recovery", "boost",
    "strengthen", "up", "soar", "jump", "advance", "upbeat",
    "optimism", "hawkish", "buy", "long", "breakout",
]

BEARISH_WORDS = [
    "fall", "drop", "decline", "lower", "bearish", "weak",
    "negative", "loss", "recession", "slowdown", "plunge",
    "crash", "down", "sell", "short", "breakdown", "risk",
    "fear", "dovish", "concern", "worry", "uncertainty",
]

# High impact news to block trading
HIGH_IMPACT_KEYWORDS = [
    "NFP", "non-farm payroll", "interest rate", "fed decision",
    "CPI", "inflation", "GDP", "unemployment", "FOMC",
    "central bank", "rate hike", "rate cut", "emergency",
    "crisis", "war", "sanctions", "default",
]


# ─────────────────────────────────────────────────
# NEWS SCRAPERS
# ─────────────────────────────────────────────────

def scrape_forexfactory() -> list:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        url      = "https://www.forexfactory.com/calendar"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"⚠️ ForexFactory returned {response.status_code}")
            return []

        soup  = BeautifulSoup(response.content, "lxml")
        rows  = soup.find_all("tr", class_="calendar__row")
        news  = []

        for row in rows[:20]:
            try:
                impact = row.find("td", class_="calendar__impact")
                title  = row.find("td", class_="calendar__event")
                if impact and title:
                    impact_text = impact.get_text(strip=True)
                    title_text  = title.get_text(strip=True)
                    if title_text:
                        news.append({
                            "title":  title_text,
                            "impact": impact_text,
                            "source": "ForexFactory",
                        })
            except:
                continue

        logger.debug(f"📰 ForexFactory: {len(news)} events found")
        return news

    except Exception as e:
        logger.warning(f"⚠️ ForexFactory scrape failed: {e}")
        return []


def scrape_investing_news() -> list:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            )
        }
        url      = "https://www.investing.com/news/forex-news"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        soup      = BeautifulSoup(response.content, "lxml")
        articles  = soup.find_all("article", limit=15)
        headlines = []

        for article in articles:
            title = article.find("a")
            if title and title.get_text(strip=True):
                headlines.append({
                    "title":  title.get_text(strip=True),
                    "source": "Investing.com",
                })

        logger.debug(f"📰 Investing.com: {len(headlines)} headlines")
        return headlines

    except Exception as e:
        logger.warning(f"⚠️ Investing.com scrape failed: {e}")
        return []


def get_fallback_headlines() -> list:
    return [
        {"title": "Forex markets trading in normal ranges", "source": "Fallback"},
        {"title": "EUR/USD holds steady amid mixed signals", "source": "Fallback"},
        {"title": "Currency markets await economic data",   "source": "Fallback"},
    ]


# ─────────────────────────────────────────────────
# SENTIMENT ANALYSIS
# ─────────────────────────────────────────────────

def analyze_headline(headline: str) -> float:
    """
    Analyze sentiment of a single headline
    Returns score: -1.0 (bearish) to +1.0 (bullish)
    """
    try:
        # ── LAZY IMPORT — only loads textblob when this function is called ──
        from textblob import TextBlob

        blob  = TextBlob(headline)
        score = blob.sentiment.polarity

        headline_lower = headline.lower()

        bullish_count = sum(
            1 for word in BULLISH_WORDS
            if word in headline_lower
        )
        bearish_count = sum(
            1 for word in BEARISH_WORDS
            if word in headline_lower
        )

        keyword_score = (bullish_count - bearish_count) * 0.1
        final_score   = max(-1.0, min(1.0, score + keyword_score))

        return final_score

    except Exception as e:
        logger.error(f"❌ Headline analysis error: {e}")
        return 0.0


def check_high_impact_news(headlines: list) -> dict:
    try:
        found_events = []
        for item in headlines:
            title = item.get("title", "").upper()
            for keyword in HIGH_IMPACT_KEYWORDS:
                if keyword.upper() in title:
                    found_events.append({
                        "event":  keyword,
                        "title":  item["title"],
                        "source": item.get("source", ""),
                    })
                    break

        if found_events:
            return {
                "blocked":      True,
                "reason":       f"High impact news: {found_events[0]['event']}",
                "events":       found_events,
                "block_until":  (
                    datetime.now() + timedelta(minutes=30)
                ).isoformat(),
            }

        return {
            "blocked": False,
            "reason":  "No high impact news detected",
            "events":  [],
        }

    except Exception as e:
        logger.error(f"❌ High impact check error: {e}")
        return {"blocked": False, "reason": str(e), "events": []}


# ─────────────────────────────────────────────────
# MASTER SENTIMENT ANALYZER
# ─────────────────────────────────────────────────

_sentiment_cache = {
    "score":      0.0,
    "bias":       "NEUTRAL",
    "blocked":    False,
    "timestamp":  None,
    "headlines":  [],
}
CACHE_MINUTES = 5


def get_market_sentiment() -> dict:
    global _sentiment_cache

    if _sentiment_cache["timestamp"]:
        age = (datetime.now() - _sentiment_cache["timestamp"]).seconds / 60
        if age < CACHE_MINUTES:
            logger.debug(f"📰 Using cached sentiment: {_sentiment_cache['bias']}")
            cached = _sentiment_cache.copy()
            cached["cached"] = True
            return cached

    try:
        logger.info("📰 Fetching market sentiment...")
        headlines = []
        headlines += scrape_forexfactory()
        headlines += scrape_investing_news()

        if not headlines:
            headlines = get_fallback_headlines()

        impact_check = check_high_impact_news(headlines)

        scores = []
        for item in headlines[:20]:
            score = analyze_headline(item["title"])
            scores.append(score)

        avg_score       = sum(scores) / len(scores) if scores else 0.0
        sentiment_score = round(avg_score * 100, 1)

        if sentiment_score > 20:
            bias = "BULLISH"
        elif sentiment_score < -20:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        result = {
            "score":        sentiment_score,
            "bias":         bias,
            "blocked":      impact_check["blocked"],
            "block_reason": impact_check["reason"],
            "events":       impact_check["events"],
            "headlines":    [h["title"] for h in headlines[:5]],
            "cached":       False,
            "timestamp":    datetime.now().isoformat(),
        }

        _sentiment_cache = result.copy()
        _sentiment_cache["timestamp"] = datetime.now()

        emoji = "📈" if bias == "BULLISH" else "📉" if bias == "BEARISH" else "➡️"
        logger.info(
            f"{emoji} Sentiment: {bias} | "
            f"Score: {sentiment_score} | "
            f"Blocked: {impact_check['blocked']}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Sentiment analysis error: {e}")
        return {
            "score":        0.0,
            "bias":         "NEUTRAL",
            "blocked":      False,
            "block_reason": str(e),
            "events":       [],
            "headlines":    [],
            "cached":       False,
        }


def sentiment_favors_direction(
    sentiment: dict,
    direction: str
) -> bool:
    bias = sentiment.get("bias", "NEUTRAL")

    if bias == "NEUTRAL":
        return True
    if direction == "CALL" and bias == "BULLISH":
        return True
    if direction == "PUT" and bias == "BEARISH":
        return True

    return False


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Sentiment Engine Test")
    print("─" * 45)
    print("Fetching market sentiment...\n")

    result = get_market_sentiment()

    print(f"Score:    {result['score']}")
    print(f"Bias:     {result['bias']}")
    print(f"Blocked:  {result['blocked']}")
    if result["blocked"]:
        print(f"Reason:   {result['block_reason']}")
    print(f"\nTop Headlines:")
    for h in result["headlines"][:3]:
        print(f"  → {h}")

    print(f"\nFavors CALL: {sentiment_favors_direction(result, 'CALL')}")
    print(f"Favors PUT:  {sentiment_favors_direction(result, 'PUT')}")