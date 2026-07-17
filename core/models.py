from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SignalMetrics:
    sfp_passed: bool = False
    mss_passed: bool = False
    htf_passed: bool = False
    trend_passed: bool = False
    rsi_passed: bool = False
    volume_passed: bool = False
    atr_passed: bool = False
    candle_strength_passed: bool = False
    score: int = 0
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RiskResult:
    entry: float
    stop: float
    target: float
    risk: float
    rr: float
    valid: bool
    reason: str = ""


@dataclass(slots=True)
class Signal:
    pair: str
    exchange: str
    timeframe: str
    direction: str
    confidence: int
    entry: float
    stop: float
    target: float
    volume: float
    setup: str
    score: int
    filters: list[str]
    rr: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair": self.pair,
            "exchange": self.exchange,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "confidence": self.confidence,
            "entry": round(self.entry, 8),
            "stop": round(self.stop, 8),
            "target": round(self.target, 8),
            "volume": round(self.volume, 2),
            "setup": self.setup,
            "score": self.score,
            "filters": self.filters,
            "rr": round(self.rr, 2),
        }


@dataclass(slots=True)
class BacktestTrade:
    pair: str
    timeframe: str
    direction: str
    entry: float
    stop: float
    target: float
    rr: float
    result: str
    pnl: float
    max_favorable: float
    max_adverse: float


@dataclass(slots=True)
class BacktestReport:
    trades: list[BacktestTrade]
    signals: int
    winrate: float
    profit_factor: float
    average_rr: float
    max_drawdown: float
    by_timeframe: dict[str, dict[str, float]]
