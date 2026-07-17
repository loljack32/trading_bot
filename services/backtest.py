from __future__ import annotations

from typing import Any

from core.models import BacktestReport, BacktestTrade, Signal
from utils.logger import get_logger


class Backtester:
    def __init__(self) -> None:
        self.logger = get_logger("backtest")

    def evaluate(self, signal: Signal, candles: list[dict[str, Any]]) -> dict[str, Any]:
        if not candles:
            return {"pnl": 0.0, "win": False, "reason": "No data", "rr": signal.rr}

        entry = signal.entry
        stop = signal.stop
        target = signal.target
        if signal.direction == "LONG":
            outcome = max((c["high"] for c in candles), default=entry)
            if outcome >= target:
                pnl = (target - entry) / max(entry, 1e-9)
                return {"pnl": pnl * 100, "win": True, "reason": "Target hit", "rr": signal.rr}
            if outcome <= stop:
                pnl = (stop - entry) / max(entry, 1e-9)
                return {"pnl": pnl * 100, "win": False, "reason": "Stop hit", "rr": signal.rr}
        else:
            outcome = min((c["low"] for c in candles), default=entry)
            if outcome <= target:
                pnl = (entry - target) / max(entry, 1e-9)
                return {"pnl": pnl * 100, "win": True, "reason": "Target hit", "rr": signal.rr}
            if outcome >= stop:
                pnl = (entry - stop) / max(entry, 1e-9)
                return {"pnl": pnl * 100, "win": False, "reason": "Stop hit", "rr": signal.rr}

        return {"pnl": 0.0, "win": False, "reason": "No exit", "rr": signal.rr}

    def summarize(self, results: list[dict[str, Any]]) -> BacktestReport:
        if not results:
            return BacktestReport(trades=[], signals=0, winrate=0.0, profit_factor=0.0, average_rr=0.0, max_drawdown=0.0, by_timeframe={})

        wins = [item["pnl"] for item in results if item.get("win")]
        losses = [abs(item["pnl"]) for item in results if not item.get("win") and item.get("pnl")]
        winrate = len(wins) / len(results) if results else 0.0
        profit_factor = sum(wins) / max(sum(losses), 1e-9) if losses else float("inf")
        average_rr = sum(item.get("rr", 0.0) for item in results) / len(results)
        by_timeframe: dict[str, dict[str, float]] = {}
        for item in results:
            tf = item.get("timeframe", "unknown")
            by_timeframe.setdefault(tf, {"signals": 0, "wins": 0, "winrate": 0.0})
            by_timeframe[tf]["signals"] += 1
            if item.get("win"):
                by_timeframe[tf]["wins"] += 1
        for tf, data in by_timeframe.items():
            data["winrate"] = round((data["wins"] / data["signals"]) * 100, 2) if data["signals"] else 0.0
        trades = []
        for item in results:
            trade = BacktestTrade(
                pair=item.get("pair", "unknown"),
                timeframe=item.get("timeframe", "unknown"),
                direction=item.get("direction", "LONG"),
                entry=float(item.get("entry", 0.0)),
                stop=float(item.get("stop", 0.0)),
                target=float(item.get("target", 0.0)),
                rr=float(item.get("rr", 0.0)),
                result="Win" if item.get("win") else "Loss",
                pnl=float(item.get("pnl", 0.0)),
                max_favorable=0.0,
                max_adverse=0.0,
            )
            trades.append(trade)

        return BacktestReport(
            trades=trades,
            signals=len(results),
            winrate=round(winrate * 100, 2),
            profit_factor=round(profit_factor, 2),
            average_rr=round(average_rr, 2),
            max_drawdown=0.0,
            by_timeframe=by_timeframe,
        )
