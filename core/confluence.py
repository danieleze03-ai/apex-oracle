# ⚡ APEX ORACLE — AO-2.5
# Confluence Engine — TREND FOLLOWING REBUILD
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────
#
# STRATEGY CHANGE: Mean Reversion → Trend Following
#
# KEY INSIGHT:
# V10/V25 are random walks that produce SHORT STREAKS
# by chance. We don't predict long-term direction.
# We only trade when ALL 3 timeframes show a detectable
# lean — and only enter on a pullback within that trend.
#
# SCORING (out of 12):
#   [4pts] TF Alignment  — 3/5/10min EMA8/21 all agree
#                          1pt per TF + 1 bonus if all 3
#   [2pts] EMA Strength  — avg diff size above threshold
#   [3pts] Pullback-Resume — 1min RSI dipped then turned
#   [1pt]  RSI Brake     — RSI NOT already extreme on entry
#   [2pts] MACD Momentum — MACD turning in trend direction
#
# GATES:
#   score >= 10  → TRADE (live + practice)
#   score  8-9   → PHANTOM (shadow log, no real money)
#   score  < 8   → SKIP
#
# HARD RULE:
#   If 3/3 TFs not aligned → NO TRADE, score irrelevant
#
# v2.5.1 FIX:
#   Per-timeframe EMA thresholds replace single global threshold.
#   3m=0.02%  5m=0.03%  10m=0.07%
#   Reason: shorter candles produce smaller EMA diffs naturally.
#   Single threshold of 0.07% was impossible for 3m/5m to cross.
# ─────────────────────────────────────────────────

import os
import numpy as np
from loguru import logger
import config

# ─────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────
MIN_SCORE         = config.MIN_SCORE            # 10
PHANTOM_MIN_SCORE = config.PHANTOM_MIN_SCORE    # 8
EMA_FAST          = config.EMA_FAST             # 8
EMA_SLOW          = config.EMA_SLOW             # 21
EMA_DIFF_THRESH   = config.EMA_DIFF_THRESHOLD   # 0.0007 (kept for EMA strength check)
RSI_PERIOD        = config.RSI_PERIOD           # 14
RSI_BRAKE_HIGH    = config.RSI_BRAKE_HIGH       # 70
RSI_BRAKE_LOW     = config.RSI_BRAKE_LOW        # 30
RSI_PULLBACK_LOW  = config.RSI_PULLBACK_LOW     # 40
RSI_PULLBACK_HIGH = config.RSI_PULLBACK_HIGH    # 55
MACD_FAST         = config.MACD_FAST            # 12
MACD_SLOW         = config.MACD_SLOW            # 26
MACD_SIGNAL       = config.MACD_SIGNAL          # 9

# ─────────────────────────────────────────────────
# PER-TIMEFRAME EMA THRESHOLDS  ← v2.5.1 FIX
# Shorter candles produce smaller diffs — each TF
# gets its own realistic threshold based on log data.
# ─────────────────────────────────────────────────
EMA_THRESH_3M  = 0.0002   # 0.02% — 3m candles are tight
EMA_THRESH_5M  = 0.0003   # 0.03% — 5m candles slightly wider
EMA_THRESH_10M = 0.0007   # 0.07% — 10m unchanged, already working


# ─────────────────────────────────────────────────
# INDICATOR CALCULATORS
# ─────────────────────────────────────────────────

def _ema(closes: np.ndarray, period: int) -> float:
    """Exponential Moving Average — returns last value."""
    if len(closes) < period:
        return float(closes[-1])
    k   = 2.0 / (period + 1)
    ema = float(closes[0])
    for price in closes[1:]:
        ema = float(price) * k + ema * (1 - k)
    return ema


def _ema_series(closes: np.ndarray, period: int) -> np.ndarray:
    """Full EMA series — needed for MACD."""
    k      = 2.0 / (period + 1)
    result = np.zeros(len(closes))
    result[0] = closes[0]
    for i in range(1, len(closes)):
        result[i] = closes[i] * k + result[i - 1] * (1 - k)
    return result


def _calc_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Standard RSI."""
    if len(closes) < period + 1:
        return 50.0
    deltas   = np.diff(closes)
    gains    = np.where(deltas > 0, deltas, 0.0)
    losses   = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    return round(float(100 - (100 / (1 + rs))), 2)


def _calc_macd(closes: np.ndarray) -> dict:
    """MACD line, signal line, histogram."""
    if len(closes) < MACD_SLOW + MACD_SIGNAL:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0, "prev_hist": 0.0}
    fast_ema    = _ema_series(closes, MACD_FAST)
    slow_ema    = _ema_series(closes, MACD_SLOW)
    macd_line   = fast_ema - slow_ema
    signal_line = _ema_series(macd_line, MACD_SIGNAL)
    hist        = macd_line - signal_line
    return {
        "macd":      round(float(macd_line[-1]), 6),
        "signal":    round(float(signal_line[-1]), 6),
        "hist":      round(float(hist[-1]), 6),
        "prev_hist": round(float(hist[-2]), 6) if len(hist) > 1 else 0.0,
    }


def _rsi_series(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Full RSI series — needed to detect pullback dip."""
    if len(closes) < period + 2:
        return np.full(len(closes), 50.0)
    result = np.full(len(closes), 50.0)
    deltas = np.diff(closes)
    for i in range(period, len(closes)):
        window_gains  = np.where(deltas[i-period:i] > 0, deltas[i-period:i], 0.0)
        window_losses = np.where(deltas[i-period:i] < 0, -deltas[i-period:i], 0.0)
        avg_gain = np.mean(window_gains)
        avg_loss = np.mean(window_losses)
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
    return result


# ─────────────────────────────────────────────────
# COMPONENT 1: TF ALIGNMENT (0-4 pts)
# ─────────────────────────────────────────────────

def _check_tf_alignment(
    closes_3m:  np.ndarray,
    closes_5m:  np.ndarray,
    closes_10m: np.ndarray,
) -> tuple:
    """
    For each TF compute EMA8 vs EMA21.
    Each timeframe uses its OWN threshold (v2.5.1 fix):
      3m  → 0.02%  (EMA_THRESH_3M)
      5m  → 0.03%  (EMA_THRESH_5M)
      10m → 0.07%  (EMA_THRESH_10M)

    Points:
      1pt per TF aligned in same direction (max 3)
      +1 bonus if ALL 3 agree

    Returns: (direction, score, aligned_count, tf_results)
    """
    # Map each label to its closes array AND its own threshold
    tf_config = [
        ("3m",  closes_3m,  EMA_THRESH_3M),
        ("5m",  closes_5m,  EMA_THRESH_5M),
        ("10m", closes_10m, EMA_THRESH_10M),
    ]

    results = {}
    for label, closes, thresh in tf_config:
        if closes is None or len(closes) < EMA_SLOW + 5:
            results[label] = {"dir": "NEUTRAL", "diff_pct": 0.0}
            continue

        fast  = _ema(closes, EMA_FAST)
        slow  = _ema(closes, EMA_SLOW)
        price = float(closes[-1])

        if price == 0:
            results[label] = {"dir": "NEUTRAL", "diff_pct": 0.0}
            continue

        diff_pct = (fast - slow) / price  # signed decimal

        if diff_pct >= thresh:
            direction = "UP"
        elif diff_pct <= -thresh:
            direction = "DOWN"
        else:
            direction = "NEUTRAL"

        results[label] = {
            "dir":      direction,
            "diff_pct": round(diff_pct * 100, 4),
            "fast":     round(fast, 4),
            "slow":     round(slow, 4),
            "thresh":   round(thresh * 100, 4),  # for logging clarity
        }

    dirs       = [v["dir"] for v in results.values()]
    up_count   = dirs.count("UP")
    down_count = dirs.count("DOWN")

    if up_count >= 3:
        agreed_dir = "UP"
        score      = 4   # 3 TFs + bonus
        aligned    = 3
    elif down_count >= 3:
        agreed_dir = "DOWN"
        score      = 4
        aligned    = 3
    elif up_count == 2:
        agreed_dir = "UP"
        score      = 2
        aligned    = 2
    elif down_count == 2:
        agreed_dir = "DOWN"
        score      = 2
        aligned    = 2
    else:
        agreed_dir = "NEUTRAL"
        score      = 0
        aligned    = 0

    return agreed_dir, score, aligned, results


# ─────────────────────────────────────────────────
# COMPONENT 2: EMA STRENGTH (0-2 pts)
# ─────────────────────────────────────────────────

def _check_ema_strength(tf_results: dict, trend_dir: str) -> tuple:
    """
    How strong is the trend? Avg absolute diff across aligned TFs.
    Uses each TF's own threshold for fair comparison.
    > 2× its threshold → 2pts
    > 1× its threshold → 1pt
    """
    thresh_map = {
        "3m":  EMA_THRESH_3M,
        "5m":  EMA_THRESH_5M,
        "10m": EMA_THRESH_10M,
    }

    ratios = []
    for label, v in tf_results.items():
        if v["dir"] != "NEUTRAL" and v["dir"] == trend_dir:
            thresh = thresh_map.get(label, EMA_DIFF_THRESH)
            ratio  = (abs(v["diff_pct"]) / 100) / thresh
            ratios.append(ratio)

    if not ratios:
        return 0, "No aligned TFs for strength check"

    avg_ratio = sum(ratios) / len(ratios)

    if avg_ratio >= 2.0:
        return 2, f"+2 EMA strength (avg {avg_ratio:.2f}× above threshold)"
    elif avg_ratio >= 1.0:
        return 1, f"+1 EMA strength (avg {avg_ratio:.2f}× above threshold)"
    else:
        return 0, f"0 EMA strength (avg {avg_ratio:.2f}× — below threshold)"


# ─────────────────────────────────────────────────
# COMPONENT 3: PULLBACK-RESUME (0-3 pts)
# ─────────────────────────────────────────────────

def _check_pullback_resume(closes_1m: np.ndarray, trend_dir: str) -> tuple:
    """
    Checks if 1min RSI dipped into pullback zone then turned back.

    For CALL (uptrend):
      RSI dipped to 40-55 range in recent candles, now rising back up.
    For PUT (downtrend):
      RSI rose to 45-60 range in recent candles, now falling back down.

    3pts = clean pullback + resume confirmed
    2pts = partial (dip detected OR resume detected, not both)
    1pt  = minor lean in right direction
    0pts = no pullback evidence
    """
    if closes_1m is None or len(closes_1m) < 20:
        return 1, "1M pullback: insufficient data — partial credit"

    rsi_arr = _rsi_series(closes_1m, RSI_PERIOD)

    lookback    = min(8, len(rsi_arr) - 1)
    recent_rsi  = rsi_arr[-lookback:]
    current_rsi = float(rsi_arr[-1])
    prev_rsi    = float(rsi_arr[-2]) if len(rsi_arr) > 1 else current_rsi

    if trend_dir == "UP":
        dip_detected = any(RSI_PULLBACK_LOW <= r <= RSI_PULLBACK_HIGH for r in recent_rsi)
        resume       = current_rsi > prev_rsi and current_rsi >= RSI_PULLBACK_LOW

        if dip_detected and resume:
            return 3, f"+3 Pullback-resume (RSI dipped, now rising @ {current_rsi:.1f})"
        elif dip_detected:
            return 2, f"+2 Pullback detected (RSI was in zone, not resumed yet @ {current_rsi:.1f})"
        elif resume:
            return 1, f"+1 RSI rising ({current_rsi:.1f}) but no clear dip zone"
        else:
            return 0, f"0 No pullback-resume (RSI={current_rsi:.1f})"

    else:  # DOWN
        rise_detected = any(RSI_PULLBACK_LOW <= r <= RSI_PULLBACK_HIGH for r in recent_rsi)
        resume        = current_rsi < prev_rsi and current_rsi <= RSI_PULLBACK_HIGH

        if rise_detected and resume:
            return 3, f"+3 Pullback-resume (RSI rose, now falling @ {current_rsi:.1f})"
        elif rise_detected:
            return 2, f"+2 Pullback detected (RSI was in zone, not resumed yet @ {current_rsi:.1f})"
        elif resume:
            return 1, f"+1 RSI falling ({current_rsi:.1f}) but no clear rise zone"
        else:
            return 0, f"0 No pullback-resume (RSI={current_rsi:.1f})"


# ─────────────────────────────────────────────────
# COMPONENT 4: RSI BRAKE (0-1 pt)
# ─────────────────────────────────────────────────

def _check_rsi_brake(closes_1m: np.ndarray, trend_dir: str) -> tuple:
    """
    RSI is now a BRAKE — it filters OUT entries if already extreme.
    We want to enter DURING the move, not at the end of it.

    CALL: RSI < 70 on 1min → safe (1pt). RSI >= 70 → too late (0pt)
    PUT:  RSI > 30 on 1min → safe (1pt). RSI <= 30 → too late (0pt)
    """
    if closes_1m is None or len(closes_1m) < 15:
        return 1, "RSI brake: insufficient data — default pass"

    rsi = _calc_rsi(closes_1m, RSI_PERIOD)

    if trend_dir == "UP":
        if rsi < RSI_BRAKE_HIGH:
            return 1, f"+1 RSI brake OK (RSI={rsi:.1f} < {RSI_BRAKE_HIGH} — not overbought)"
        else:
            return 0, f"0 RSI brake BLOCKED (RSI={rsi:.1f} >= {RSI_BRAKE_HIGH} — too late)"

    else:  # DOWN
        if rsi > RSI_BRAKE_LOW:
            return 1, f"+1 RSI brake OK (RSI={rsi:.1f} > {RSI_BRAKE_LOW} — not oversold)"
        else:
            return 0, f"0 RSI brake BLOCKED (RSI={rsi:.1f} <= {RSI_BRAKE_LOW} — too late)"


# ─────────────────────────────────────────────────
# COMPONENT 5: MACD MOMENTUM (0-2 pts)
# ─────────────────────────────────────────────────

def _check_macd_momentum(closes_1m: np.ndarray, trend_dir: str) -> tuple:
    """
    MACD on 1min confirms momentum in trend direction.

    2pts = MACD line crossed signal in trend direction AND histogram growing
    1pt  = histogram turning in trend direction (early signal)
    0pts = MACD against trend direction
    """
    if closes_1m is None or len(closes_1m) < MACD_SLOW + MACD_SIGNAL + 5:
        return 1, "MACD: insufficient data — partial credit"

    macd      = _calc_macd(closes_1m)
    hist      = macd["hist"]
    prev_hist = macd["prev_hist"]
    macd_line = macd["macd"]
    sig_line  = macd["signal"]

    if trend_dir == "UP":
        crossed_up   = macd_line > sig_line
        hist_growing = hist > prev_hist and hist > 0

        if crossed_up and hist_growing:
            return 2, f"+2 MACD bullish (line > signal, hist growing @ {hist:.6f})"
        elif hist > prev_hist:
            return 1, f"+1 MACD histogram turning up ({prev_hist:.6f} → {hist:.6f})"
        else:
            return 0, f"0 MACD not bullish (hist={hist:.6f}, prev={prev_hist:.6f})"

    else:  # DOWN
        crossed_down   = macd_line < sig_line
        hist_shrinking = hist < prev_hist and hist < 0

        if crossed_down and hist_shrinking:
            return 2, f"+2 MACD bearish (line < signal, hist falling @ {hist:.6f})"
        elif hist < prev_hist:
            return 1, f"+1 MACD histogram turning down ({prev_hist:.6f} → {hist:.6f})"
        else:
            return 0, f"0 MACD not bearish (hist={hist:.6f}, prev={prev_hist:.6f})"


# ─────────────────────────────────────────────────
# MAIN CONFLUENCE CALCULATOR
# ─────────────────────────────────────────────────

def calculate_confluence(
    candles_primary: list,
    candles_by_tf:   dict,
    pair:            str = "",
) -> dict:
    """
    AO-2.5 Trend-Following Confluence Engine.

    candles_primary → treated as 5min candles
    candles_by_tf   → must contain keys: "3m", "10m", "1m"

    HARD RULE: 3/3 TF alignment required. If not met → SKIP immediately.
    Then score the rest. 10+/12 = TRADE. 8-9/12 = PHANTOM.
    """
    try:
        def to_closes(candles):
            if not candles:
                return None
            arr = np.array([
                float(c.get("close", c.get("Close", 0)))
                for c in candles
                if c.get("close", c.get("Close", 0)) != 0
            ])
            return arr if len(arr) >= 5 else None

        closes_5m  = to_closes(candles_primary)
        closes_3m  = to_closes(candles_by_tf.get("3m"))
        closes_10m = to_closes(candles_by_tf.get("10m"))
        closes_1m  = to_closes(candles_by_tf.get("1m"))

        if closes_5m is None or len(closes_5m) < 25:
            return _skip("Not enough 5min candle data")

        # ── COMPONENT 1: TF Alignment ──────────────
        trend_dir, tf_score, aligned_count, tf_results = _check_tf_alignment(
            closes_3m, closes_5m, closes_10m
        )

        logger.info(
            f"📐 {pair} TF Alignment | Dir={trend_dir} | "
            f"Aligned={aligned_count}/3 | Score={tf_score}/4 | "
            f"3m={tf_results.get('3m', {}).get('dir','?')}({tf_results.get('3m', {}).get('diff_pct','?')}%) "
            f"5m={tf_results.get('5m', {}).get('dir','?')}({tf_results.get('5m', {}).get('diff_pct','?')}%) "
            f"10m={tf_results.get('10m', {}).get('dir','?')}({tf_results.get('10m', {}).get('diff_pct','?')}%)"
        )

        # ── HARD RULE: 3/3 required ────────────────
        if aligned_count < 3 or trend_dir == "NEUTRAL":
            return _skip(
                f"TF alignment FAILED — only {aligned_count}/3 agree "
                f"(3m={tf_results.get('3m',{}).get('dir','?')} "
                f"5m={tf_results.get('5m',{}).get('dir','?')} "
                f"10m={tf_results.get('10m',{}).get('dir','?')})"
            )

        signal_direction = "CALL" if trend_dir == "UP" else "PUT"

        # ── COMPONENT 2: EMA Strength ──────────────
        ema_score, ema_reason = _check_ema_strength(tf_results, trend_dir)

        # ── COMPONENT 3: Pullback-Resume ──────────
        pb_score, pb_reason = _check_pullback_resume(closes_1m, trend_dir)

        # ── COMPONENT 4: RSI Brake ─────────────────
        brake_score, brake_reason = _check_rsi_brake(closes_1m, trend_dir)

        # ── COMPONENT 5: MACD Momentum ────────────
        macd_score, macd_reason = _check_macd_momentum(closes_1m, trend_dir)

        # ── Total Score ────────────────────────────
        total_score = tf_score + ema_score + pb_score + brake_score + macd_score

        logger.info(
            f"🎯 {pair} | {signal_direction} | Score={total_score}/12 | "
            f"TF={tf_score}/4 | EMA={ema_score}/2 | "
            f"PB={pb_score}/3 | Brake={brake_score}/1 | MACD={macd_score}/2"
        )
        logger.debug(f"   {ema_reason}")
        logger.debug(f"   {pb_reason}")
        logger.debug(f"   {brake_reason}")
        logger.debug(f"   {macd_reason}")

        if total_score < PHANTOM_MIN_SCORE:
            return _skip(
                f"Score {total_score}/12 below minimum {PHANTOM_MIN_SCORE} — skipping"
            )

        confidence_pct = round((total_score / 12) * 100, 1)

        base_result = {
            "direction":  signal_direction,
            "confidence": confidence_pct,
            "score":      total_score,
            "stake_size": "FULL",
            "reason": (
                f"{signal_direction} | Score: {total_score}/12 | "
                f"TF={tf_score}/4 EMA={ema_score}/2 "
                f"PB={pb_score}/3 Brake={brake_score}/1 MACD={macd_score}/2"
            ),
            "pattern": "TREND_FOLLOWING",
            "breakdown": {
                "trend_dir":   trend_dir,
                "aligned_tfs": aligned_count,
                "tf_results":  tf_results,
                "components": {
                    "tf_alignment": {"score": tf_score,    "max": 4, "detail": str(tf_results)},
                    "ema_strength": {"score": ema_score,   "max": 2, "detail": ema_reason},
                    "pullback":     {"score": pb_score,    "max": 3, "detail": pb_reason},
                    "rsi_brake":    {"score": brake_score, "max": 1, "detail": brake_reason},
                    "macd":         {"score": macd_score,  "max": 2, "detail": macd_reason},
                },
            },
        }

        is_practice = os.getenv("TRADING_MODE", "PRACTICE").upper() == "PRACTICE"

        if total_score < MIN_SCORE:
            if is_practice:
                logger.info(
                    f"📊 PRACTICE TRADE: {pair} Score={total_score}/12 "
                    f"(would be phantom on LIVE)"
                )
                base_result["action"] = "TRADE"
            else:
                logger.info(
                    f"👻 PHANTOM ONLY: {pair} Score={total_score}/12 "
                    f"— need {MIN_SCORE}+ for live"
                )
                base_result["action"] = "PHANTOM"
            return base_result

        base_result["action"] = "TRADE"
        return base_result

    except Exception as e:
        import traceback
        logger.error(f"❌ Confluence error on {pair}: {e}")
        logger.error(traceback.format_exc())
        return _skip(str(e))


# ─────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────

def _skip(reason: str) -> dict:
    return {
        "direction":  "SKIP",
        "confidence": 0,
        "score":      0,
        "action":     "SKIP",
        "stake_size": "SKIP",
        "reason":     reason,
        "pattern":    "None",
        "breakdown":  {},
    }