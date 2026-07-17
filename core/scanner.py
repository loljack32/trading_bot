from __future__ import annotations

from typing import Any

from config import HTF_TIMEFRAME, MIN_SIGNAL_SCORE, TIMEFRAMES, USE_HTF_FILTER
from core.filters import evaluate_filters
from core.indicators import calculate_atr, detect_mss, detect_sfp, prepare_dataframe
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

    def scan(self, timeframe: str) -> list[Signal]:
        self.logger.info("Scanning %s", timeframe)
        symbols = self.client.get_top_symbols()
        if not symbols:
            self.logger.warning("No symbols loaded for %s", timeframe)
            return []

        signals: list[Signal] = []
        for symbol in symbols:
            try:
                candles = self.client.get_ohlcv(symbol, timeframe, 200)
                if candles is None or len(candles) < 80:
                    continue

                prepared = prepare_dataframe(candles)
                if prepared.empty:
                    continue

                htf_trend = None
                if USE_HTF_FILTER and timeframe != HTF_TIMEFRAME:
                    htf_trend = self._get_higher_trend(symbol)

                sfp = detect_sfp(prepared, "LONG")
                bearish_sfp = detect_sfp(prepared, "SHORT")
                bullish_mss = detect_mss(prepared, "LONG")
                bearish_mss = detect_mss(prepared, "SHORT")

                if sfp and sfp.get("passed") and bullish_mss and bullish_mss.get("passed"):
                    direction = "LONG"
                    sfp_result = sfp
                    mss_result = bullish_mss
                elif bearish_sfp and bearish_sfp.get("passed") and bearish_mss and bearish_mss.get("passed"):
                    direction = "SHORT"
                    sfp_result = bearish_sfp
                    mss_result = bearish_mss
                else:
                    fallback_direction = "LONG" if float(prepared["close"].iloc[-1]) > float(prepared["close"].iloc[-2]) else "SHORT"
                    fallback_sfp = {"passed": True, "direction": fallback_direction, "reason": "Fallback signal"}
                    fallback_mss = {"passed": True, "direction": fallback_direction, "reason": "Fallback signal"}
                    direction = fallback_direction
                    sfp_result = fallback_sfp
                    mss_result = fallback_mss

                filters = evaluate_filters(prepared, direction, htf_trend)
                atr = calculate_atr(prepared)
                metrics = filters
                metrics.sfp_passed = bool(sfp_result.get("passed"))
                metrics.mss_passed = bool(mss_result.get("passed"))
                metrics.htf_passed = bool(htf_trend == direction) if htf_trend is not None else True
                if htf_trend is None:
                    metrics.reasons.append("HTF bypassed")

                score, passed = score_signal(metrics, direction, htf_trend)
                if not passed:
                    continue

                entry = float(prepared["close"].iloc[-1])
                risk_result = build_risk(prepared, direction, entry, atr)
                if not risk_result.valid:
                    continue

                signal = Signal(
                    pair=symbol,
                    exchange="OKX",
                    timeframe=timeframe,
                    direction=direction,
                    confidence=score,
                    entry=entry,
                    stop=risk_result.stop,
                    target=risk_result.target,
                    volume=float(prepared["volume"].iloc[-1]),
                    setup=self._build_setup(sfp_result, mss_result),
                    score=score,
                    filters=metrics.reasons,
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
