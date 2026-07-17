from __future__ import annotations

from typing import Any

from config import ATR_PERIOD, EMA_PERIOD, RSI_PERIOD
from core.indicators import calculate_atr, calculate_candle_strength, calculate_rsi, calculate_volume_ratio, prepare_dataframe
from core.models import SignalMetrics


def ema200_trend(df) -> str:
    prepared = prepare_dataframe(df)
    ema = prepared["close"].ewm(span=EMA_PERIOD, adjust=False).mean()
    price = float(prepared["close"].iloc[-1])
    ema_value = float(ema.iloc[-1])
    return "LONG" if price > ema_value else "SHORT"


def evaluate_filters(df, direction: str, htf_trend: str | None = None) -> SignalMetrics:
    prepared = prepare_dataframe(df)
    metrics = SignalMetrics()
    reasons: list[str] = []

    trend = ema200_trend(prepared)
    if trend == direction:
        metrics.trend_passed = True
        metrics.reasons.append("EMA200 aligned")
    else:
        metrics.reasons.append("EMA200 against trend")

    rsi = calculate_rsi(prepared, RSI_PERIOD)
    if direction == "LONG" and 35 <= rsi <= 70:
        metrics.reasons.append("RSI in range")
    elif direction == "SHORT" and 30 <= rsi <= 65:
        metrics.reasons.append("RSI in range")
    else:
        metrics.reasons.append("RSI extreme")

    atr = calculate_atr(prepared, ATR_PERIOD)
    price = float(prepared["close"].iloc[-1])
    atr_ratio = atr / max(price, 1e-9)
    if atr_ratio >= 0.0015:
        metrics.atr_passed = True
        metrics.reasons.append("ATR adequate")
    else:
        metrics.reasons.append("ATR too low")

    volume_ratio = calculate_volume_ratio(prepared, period=20)
    if volume_ratio >= 1.2:
        metrics.volume_passed = True
        metrics.reasons.append("Volume expansion")
    else:
        metrics.reasons.append("Volume weak")

    candle_strength = calculate_candle_strength(prepared)
    if candle_strength >= 0.75:
        metrics.candle_strength_passed = True
        metrics.reasons.append("Strong candle")
    else:
        metrics.reasons.append("Weak candle")

    if htf_trend is not None:
        if htf_trend == direction:
            metrics.htf_passed = True
            metrics.reasons.append("HTF aligned")
        else:
            metrics.reasons.append("HTF against")

    if metrics.trend_passed or metrics.atr_passed or metrics.volume_passed or metrics.candle_strength_passed:
        metrics.reasons.append("Core filters pass")
    if metrics.htf_passed is False and htf_trend is not None:
        metrics.reasons.append("HTF filter failed")

    metrics.score = sum(
        [
            20 if metrics.trend_passed else 0,
            10 if metrics.atr_passed else 0,
            10 if metrics.volume_passed else 0,
            5 if metrics.candle_strength_passed else 0,
            20 if metrics.htf_passed else 0,
        ]
    )
    return metrics
