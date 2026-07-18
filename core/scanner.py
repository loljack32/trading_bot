from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from config import HTF_TIMEFRAME, MSS_WINDOW_CANDLES, SFP_LOOKBACK
from core.filters import evaluate_filters
from core.indicators import (
    _recent_swing_high,
    _recent_swing_low,
    calculate_atr,
    detect_mss,
    detect_sfp,
    prepare_dataframe,
)
from core.models import Signal
from core.okx import OKXClient
from core.risk import build_risk
from core.scoring import score_signal
from utils.logger import get_logger


class SignalScanner:
    def __init__(self, client: OKXClient | None = None) -> None:
        self.client = client or OKXClient()
        self.logger = get_logger("scanner")
        self._htf_cache: dict[str, str] = {}

    def _get_higher_trend(self, symbol: str) -> str | None:
        if symbol in self._htf_cache:
            return self._htf_cache[symbol]
        candles = self.client.get_ohlcv(symbol, HTF_TIMEFRAME, 200)
        if candles is None or len(candles) < 100:
            return None
        from core.filters import ema200_trend

        trend = ema200_trend(candles)
        self._htf_cache[symbol] = trend
        return trend

    def _timeframe_to_timedelta(self, timeframe: str) -> timedelta:
        unit = timeframe[-1].upper()
        amount = int(timeframe[:-1])
        if unit == "M":
            return timedelta(minutes=amount)
        if unit == "H":
            return timedelta(hours=amount)
        if unit == "D":
            return timedelta(days=amount)
        return timedelta()

    def _find_4h_sfp(self, symbol: str) -> dict[str, Any] | None:
        candles = self.client.get_ohlcv(symbol, HTF_TIMEFRAME, 200)
        if candles is None or len(candles) < SFP_LOOKBACK:
            return None
        prepared = prepare_dataframe(candles)
        if prepared.empty or len(prepared) < SFP_LOOKBACK:
            return None

        sfp_window = prepared.iloc[-SFP_LOOKBACK:]
        long_sfp = detect_sfp(sfp_window, "LONG")
        short_sfp = detect_sfp(sfp_window, "SHORT")
        last_candle = sfp_window.iloc[-1]
        sfp_timestamp = last_candle["timestamp"] if "timestamp" in last_candle else None

        daily_candles = self.client.get_ohlcv(symbol, "1D", 200)
        if daily_candles is None or len(daily_candles) < 10:
            return None
        daily_prepared = prepare_dataframe(daily_candles)
        if daily_prepared.empty:
            return None
        daily_prev_low = _recent_swing_low(daily_prepared)
        daily_prev_high = _recent_swing_high(daily_prepared)

        def _classify_daily_sfp(direction: str) -> dict[str, object] | None:
            touch_tol = 0.0015
            if direction == "LONG":
                if daily_prev_low is None or pd.isna(daily_prev_low):
                    return None
                low = float(last_candle["low"])
                close = float(last_candle["close"])
                broke = low < daily_prev_low
                touched = low <= daily_prev_low * (1 + touch_tol)
                reclaimed = close >= daily_prev_low * (1 - touch_tol)
                if broke and reclaimed:
                    return {
                        "type": "break",
                        "text": "Тень свечи пробила локальный минимум",
                        "emoji": "🚨",
                    }
                if touched or abs(low - daily_prev_low) <= abs(daily_prev_low) * touch_tol:
                    return {
                        "type": "touch",
                        "text": "Тень свечи близко к локальному минимуму",
                        "emoji": "⚡",
                    }
                return None

            if direction == "SHORT":
                if daily_prev_high is None or pd.isna(daily_prev_high):
                    return None
                high = float(last_candle["high"])
                close = float(last_candle["close"])
                broke = high > daily_prev_high
                touched = high >= daily_prev_high * (1 - touch_tol)
                reclaimed = close <= daily_prev_high * (1 + touch_tol)
                if broke and reclaimed:
                    return {
                        "type": "break",
                        "text": "Тень свечи пробила локальный максимум",
                        "emoji": "🚨",
                    }
                if touched or abs(high - daily_prev_high) <= abs(daily_prev_high) * touch_tol:
                    return {
                        "type": "touch",
                        "text": "Тень свечи близко к локальному максимуму",
                        "emoji": "⚡",
                    }
                return None

            return None

        if long_sfp and long_sfp.get("passed"):
            sfp_event = _classify_daily_sfp("LONG")
            if not sfp_event:
                return None
            return {
                "direction": "LONG",
                "result": long_sfp,
                "timeframe": HTF_TIMEFRAME,
                "sfp_timestamp": sfp_timestamp,
                "sfp_event": sfp_event,
            }
        if short_sfp and short_sfp.get("passed"):
            sfp_event = _classify_daily_sfp("SHORT")
            if not sfp_event:
                return None
            return {
                "direction": "SHORT",
                "result": short_sfp,
                "timeframe": HTF_TIMEFRAME,
                "sfp_timestamp": sfp_timestamp,
                "sfp_event": sfp_event,
            }

        return None

    def _find_15m_mss(self, symbol: str, direction: str, sfp_timestamp: pd.Timestamp | None) -> dict[str, Any] | None:
        candles = self.client.get_ohlcv(symbol, "15m", 200)
        if candles is None or len(candles) == 0:
            return None
        prepared = prepare_dataframe(candles)
        if prepared.empty:
            return None

        if sfp_timestamp is None:
            return None

        start_time = sfp_timestamp + self._timeframe_to_timedelta(HTF_TIMEFRAME)
        filtered = prepared[prepared["timestamp"] >= start_time]
        if filtered.empty:
            return None
        if len(filtered) > MSS_WINDOW_CANDLES:
            filtered = filtered.tail(MSS_WINDOW_CANDLES)

        mss = detect_mss(filtered, direction)
        return {"result": mss, "prepared": filtered}

    def _format_signal_setup(self, sfp_event: dict[str, Any] | None, has_mss: bool) -> str:
        if not sfp_event:
            return "SFP"
        sfp_type = sfp_event.get("type", "touch")
        sfp_text = sfp_event.get("text", "Тень свечи близко к локальному экстремуму")
        sfp_emoji = sfp_event.get("emoji", "⚡")
        if has_mss:
            return f"SFP+MSS!!! {sfp_emoji} {sfp_text}"
        if sfp_type == "break":
            return f"SFP! {sfp_emoji} {sfp_text}"
        return f"SFP {sfp_emoji} {sfp_text}"

    def scan_symbol(self, symbol: str) -> list[Signal]:
        signals: list[Signal] = []
        try:
            sfp_info = self._find_4h_sfp(symbol)
            if not sfp_info:
                return []

            direction = sfp_info["direction"]
            sfp_timestamp = sfp_info.get("sfp_timestamp")
            sfp_event = sfp_info.get("sfp_event")
            mss_info = self._find_15m_mss(symbol, direction, sfp_timestamp)
            if not mss_info or mss_info.get("prepared") is None or mss_info["prepared"].empty:
                return []

            prepared_15m = mss_info["prepared"]
            mss_passed = bool(mss_info.get("result") and mss_info["result"].get("passed"))

            htf_trend = self._get_higher_trend(symbol)
            filters = evaluate_filters(prepared_15m, direction, htf_trend)
            filters.sfp_passed = True
            filters.mss_passed = mss_passed
            filters.htf_passed = bool(htf_trend == direction) if htf_trend is not None else True
            if htf_trend is None:
                filters.reasons.append("HTF bypassed")

            entry = float(prepared_15m["close"].iloc[-1])
            atr = calculate_atr(prepared_15m)
            risk_result = build_risk(prepared_15m, direction, entry, atr)
            if not risk_result.valid:
                return []

            setup = self._format_signal_setup(sfp_event, mss_passed)
            confidence = 100
            timeframe_label = "15m"

            signal = Signal(
                pair=symbol,
                exchange="OKX",
                timeframe=timeframe_label,
                direction=direction,
                confidence=confidence,
                entry=entry,
                stop=risk_result.stop,
                target=risk_result.target,
                volume=float(prepared_15m["volume"].iloc[-1]),
                setup=setup,
                score=confidence,
                filters=filters.reasons,
                rr=risk_result.rr,
            )

            self.logger.info(
                "Signal ready: %s | %s | score=%s | rr=%.2f | setup=%s",
                signal.pair,
                signal.direction,
                signal.confidence,
                signal.rr,
                signal.setup,
            )
            signals.append(signal)
        except Exception as exc:  # pragma: no cover - defensive.
            self.logger.warning("Failed scanning %s: %s", symbol, exc)
        return signals

    def scan(self, timeframe: str) -> list[Signal]:
        self.logger.info("Scanning %s", timeframe)
        if timeframe != HTF_TIMEFRAME:
            self.logger.info("Skipping scan for %s, only 4H/15m combination is supported", timeframe)
            return []

        symbols = self.client.get_top_symbols()
        if not symbols:
            self.logger.warning("No symbols loaded for %s", timeframe)
            return []

        signals: list[Signal] = []
        for symbol in symbols:
            signals.extend(self.scan_symbol(symbol))

        signals.sort(key=lambda item: item.confidence, reverse=True)
        return signals

    def _build_setup(self, sfp_result: dict[str, Any], mss_result: dict[str, Any]) -> str:
        parts = ["Liquidity sweep", "Structure break"]
        if sfp_result.get("direction") == "LONG":
            parts.append("Bullish SFP")
        else:
            parts.append("Bearish SFP")
        if mss_result.get("direction") == "LONG":
            parts.append("Bullish MSS")
        else:
            parts.append("Bearish MSS")
        return " | ".join(parts)
