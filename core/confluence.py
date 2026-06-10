def calculate_confluence(
    candles_primary: list,
    candles_by_tf:   dict,
    pair:            str = "",
) -> dict:
    try:
        if not candles_primary or len(candles_primary) < 50:
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     "Not enough candle data",
            }

        primary_signal = generate_signal(candles_primary, pair)
        direction      = primary_signal["direction"]

        if direction == "SKIP":
            return {
                "direction":  "SKIP",
                "confidence": 0,
                "action":     "SKIP",
                "stake_size": "SKIP",
                "reason":     primary_signal.get("reason", "No signal"),
            }

        df         = prepare_dataframe(candles_primary)
        ind_score  = score_indicators(primary_signal, direction)
        pat_data   = detect_patterns(df)
        pat_score  = score_pattern(pat_data, direction)
        vol_data   = check_volatility(df, pair)
        vol_score  = score_volatility(vol_data)
        tf_score   = score_timeframes(candles_by_tf, direction)

        final_score = (
            (ind_score["score"] * WEIGHTS["indicators"] / 100) +
            (pat_score["score"] * WEIGHTS["patterns"]   / 100) +
            (vol_score["score"] * WEIGHTS["volatility"] / 100) +
            (tf_score["score"]  * WEIGHTS["timeframe"]  / 100)
        )
        final_score = round(final_score, 1)

        # ⭐ NEW RULE: If 3 or more indicators agree AND the final score is above 65, WE TRADE
        # This overrides the volatility block. This is what will make your bot trade.
        if ind_score["agreements"] >= 3 and final_score >= 65:
            # Check volatility override
            if not vol_data["tradeable"]:
                logger.warning(f"⚠️ Volatility flagged as non-tradeable, but overriding due to strong signal ({ind_score['agreements']}/5 agree, Score: {final_score}%).")
            
            if final_score >= 90:
                action     = "TRADE"
                stake_size = "FULL"
                reason     = f"🔥 Exceptional {direction} confluence!"
            elif final_score >= 75:
                action     = "TRADE"
                stake_size = "FULL"
                reason     = f"✅ Strong {direction} confluence"
            elif final_score >= 65:
                action     = "TRADE"
                stake_size = "HALF"
                reason     = f"⚡ Moderate {direction} — half stake"
            else:
                action     = "SKIP"
                stake_size = "SKIP"
                reason     = f"❌ Weak confluence ({final_score}%) — skipping"
        else:
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = f"❌ Weak confluence ({final_score}%) — skipping"

        # ── Step 6: Timeframe override ────────────
        if tf_score["total"] > 0 and tf_score["agreements"] == 0 and action == "TRADE":
            action     = "SKIP"
            stake_size = "SKIP"
            reason     = "No timeframes agree — skipping"

        result = {
            "direction":  direction,
            "confidence": final_score,
            "action":     action,
            "stake_size": stake_size,
            "reason":     reason,
            "pattern":    pat_data["pattern"],
            "breakdown": {
                "indicators": ind_score,
                "pattern":    pat_score,
                "volatility": vol_score,
                "timeframes": tf_score,
            },
        }

        emoji = "🚀" if action == "TRADE" else "⏸️"
        logger.info(
            f"{emoji} {pair} Confluence: {direction} | "
            f"Score: {final_score}% | Action: {action} | "
            f"Pattern: {pat_data['pattern']}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Confluence calculation error: {e}")
        return {
            "direction":  "SKIP",
            "confidence": 0,
            "action":     "SKIP",
            "stake_size": "SKIP",
            "reason":     str(e),
        }
