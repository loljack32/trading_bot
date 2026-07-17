#!/usr/bin/env python3
"""Debug MSS detection to understand why so few signals."""

import sys
sys.path.insert(0, '/c/Users/GOD/Desktop/trade_bot/trading_bot')

import pandas as pd
from core.okx import OKXClient
from core.indicators import prepare_dataframe, detect_mss, _recent_swing_high, _recent_swing_low
from utils.logger import get_logger

logger = get_logger("debug_mss")

client = OKXClient()
candles = client.get_ohlcv("BTC-USDT", "4H", 200)
df = prepare_dataframe(candles)

print(f"Loaded {len(df)} candles\n")

# Show last 20 candles with their swings
print("Last 20 candles and swing analysis:")
print("idx | timestamp | close | swing_high | swing_low | mss_short | mss_long")
print("-" * 120)

for idx in range(max(80, len(df) - 20), len(df)):
    window = df.iloc[:idx + 1]
    close = float(window["close"].iloc[-1])
    
    sh = _recent_swing_high(window)
    sl = _recent_swing_low(window)
    
    mss_short = detect_mss(window, "SHORT")
    mss_long = detect_mss(window, "LONG")
    
    mss_s_pass = "YES" if (mss_short and mss_short.get("passed")) else "NO"
    mss_l_pass = "YES" if (mss_long and mss_long.get("passed")) else "NO"
    
    ts = window["timestamp"].iloc[-1] if "timestamp" in window else str(idx)
    print(f"{idx:3d} | {ts} | {close:10.2f} | {sh:10.2f} | {sl:10.2f} | {mss_s_pass:9s} | {mss_l_pass:9s}")
    
    if mss_short:
        print(f"      SHORT: {mss_short}")
    if mss_long:
        print(f"      LONG:  {mss_long}")
