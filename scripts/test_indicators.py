#!/usr/bin/env python3
"""Simple test runner for indicators on a CSV of OHLCV.

Usage:
  python scripts/test_indicators.py path/to/candles.csv

CSV must contain columns: timestamp, open, high, low, close, volume
"""
from __future__ import annotations

import argparse
import pandas as pd

from core.indicators import prepare_dataframe, detect_sfp, detect_mss


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="CSV file with OHLCV")
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    df = prepare_dataframe(df)
    if df.empty:
        print("No data")
        return

    print(f"Loaded {len(df)} candles")

    for direction in ("LONG", "SHORT"):
        sfp = detect_sfp(df, direction)
        mss = detect_mss(df, direction)
        print("---", direction)
        print("SFP:", sfp)
        print("MSS:", mss)


if __name__ == "__main__":
    main()
