from __future__ import annotations

from core.models import SignalMetrics


def score_signal(metrics: SignalMetrics, direction: str, htf_trend: str | None = None) -> tuple[int, bool]:
    score = 0
    if metrics.mss_passed:
        score += 35
    if metrics.sfp_passed:
        score += 25
    if htf_trend is not None and htf_trend == direction:
        score += 20
    if metrics.volume_passed:
        score += 10
    if metrics.atr_passed:
        score += 5
    if metrics.candle_strength_passed:
        score += 5
    score = min(score, 100)
    return score, score >= 85
