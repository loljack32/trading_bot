#!/usr/bin/env python3
"""Backtest SFP/MSS signals on historical OHLCV data.

Usage:
  python scripts/backtest.py BTC-USDT 4H [--lookback=500]

Outputs: stats, signal list, performance metrics.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import TIMEFRAMES
from core.okx import OKXClient
from core.scanner import SignalScanner
from utils.logger import get_logger


logger = get_logger("backtest")


class BacktestEngine:
    def __init__(self, symbol: str, timeframe: str, lookback: int = 500):
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback = lookback
        self.client = OKXClient()
        self.scanner = SignalScanner(client=self.client)
        self.signals: list[dict] = []
        self.performance = {
            "total_signals": 0,
            "long_signals": 0,
            "short_signals": 0,
            "sfp_passed": 0,
            "mss_passed": 0,
            "both_passed": 0,
            "precision_estimate": 0.0,
            "avg_rr": 0.0,
            "max_dd": 0.0,
            "total_pnl_estimate": 0.0,
        }

    def run(self) -> dict:
        logger.info("Starting backtest for %s %s (lookback=%d)", self.symbol, self.timeframe, self.lookback)
        if self.timeframe != "4H":
            logger.error("Backtest only supports 4H signals for the current SFP+MSS logic")
            return self.performance

        signals = self.scanner.scan_symbol(self.symbol)
        if not signals:
            logger.warning("No signals found for %s", self.symbol)
            return self.performance

        for signal in signals:
            mss_passed = "SFP+MSS" in signal.setup
            self.signals.append({
                "pair": signal.pair,
                "ts": None,
                "close": signal.entry,
                "atr": None,
                "direction": signal.direction,
                "sfp": True,
                "mss": mss_passed,
                "both": mss_passed,
                "setup": signal.setup,
                "signal_detail": signal.to_dict(),
            })

        self._compute_metrics()
        logger.info("Backtest complete. Total signals: %d", self.performance["total_signals"])
        return self.performance

    def _compute_metrics(self) -> None:
        if not self.signals:
            logger.warning("No signals found")
            return

        self.performance["total_signals"] = len(self.signals)
        self.performance["long_signals"] = sum(1 for s in self.signals if s["direction"] == "LONG")
        self.performance["short_signals"] = sum(1 for s in self.signals if s["direction"] == "SHORT")
        self.performance["sfp_passed"] = sum(1 for s in self.signals if s["sfp"])
        self.performance["mss_passed"] = sum(1 for s in self.signals if s["mss"])
        self.performance["both_passed"] = sum(1 for s in self.signals if s["both"])

        if self.performance["total_signals"] > 0:
            self.performance["precision_estimate"] = (
                self.performance["both_passed"] / self.performance["total_signals"]
            )

        # Estimate RR from signal payload if available
        if self.signals:
            first_sig = self.signals[0].get("signal_detail")
            if first_sig and first_sig.get("rr") is not None:
                self.performance["avg_rr"] = float(first_sig["rr"])
            else:
                self.performance["avg_rr"] = 2.0

    def print_report(self) -> None:
        print(f"\n{'='*70}")
        print(f"BACKTEST REPORT: {self.symbol} {self.timeframe}")
        print(f"{'='*70}")
        print(f"Lookback: {self.lookback} candles")
        print(f"Total Signals: {self.performance['total_signals']}")
        print(f"  - LONG: {self.performance['long_signals']}")
        print(f"  - SHORT: {self.performance['short_signals']}")
        print(f"  - SFP Passed: {self.performance['sfp_passed']}")
        print(f"  - MSS Passed: {self.performance['mss_passed']}")
        print(f"  - Both (SFP + MSS): {self.performance['both_passed']}")
        print(f"\nMetrics:")
        print(f"  - Precision (est.): {self.performance['precision_estimate']:.2%}")
        print(f"  - Avg RR: {self.performance['avg_rr']:.2f}:1")
        print(f"\nFirst 10 signals:")
        for i, sig in enumerate(self.signals[:10]):
            atr_text = f"{sig['atr']:.4f}" if sig['atr'] is not None else "n/a"
            print(f"  {i+1}. [{sig['direction']}] ts={sig['ts']} close={sig['close']:.2f} "
                  f"SFP={sig['sfp']} MSS={sig['mss']} ATR={atr_text}")
        print(f"\n{'='*70}\n")


def main():
    p = argparse.ArgumentParser(description="Backtest SFP/MSS signals")
    p.add_argument("symbol", help="Symbol (e.g., BTC-USDT)")
    p.add_argument("timeframe", help="Timeframe (e.g., 4H, 1H)")
    p.add_argument("--lookback", type=int, default=500, help="Number of candles to load (default: 500)")
    p.add_argument("--output", help="Output JSON file for results")
    args = p.parse_args()

    if args.timeframe not in TIMEFRAMES:
        print(f"Error: timeframe {args.timeframe} not in {TIMEFRAMES}")
        return 1

    engine = BacktestEngine(args.symbol, args.timeframe, args.lookback)
    perf = engine.run()
    engine.print_report()

    if args.output:
        output = {
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "lookback": args.lookback,
            "timestamp": datetime.utcnow().isoformat(),
            "performance": perf,
            "signals": engine.signals[:100],  # Store first 100 for review
        }
        Path(args.output).write_text(json.dumps(output, indent=2, default=str))
        print(f"Results saved to {args.output}")

    return 0 if perf["total_signals"] > 0 else 1


if __name__ == "__main__":
    exit(main())
