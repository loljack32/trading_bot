from __future__ import annotations

from core.models import SignalMetrics


def score_signal(metrics: SignalMetrics, direction: str, htf_trend: str | None = None) -> tuple[int, bool]:
    score = 0
    if metrics.mss_passed:
        score += 25
    if metrics.sfp_passed:
        score += 20
    if htf_trend is not None and htf_trend == direction:
        score += 15
    if metrics.trend_passed:
        score += 15
    if metrics.rsi_passed:
        score += 10
    if metrics.volume_passed:
        score += 7
    if metrics.atr_passed:
        score += 4
    if metrics.candle_strength_passed:
        score += 4
    score = min(score, 100)
    return score, score >= 90
