from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import ATR_PERIOD, MIN_WICK_PERCENT, RSI_PERIOD, SWING_LOOKBACK
from utils.helpers import safe_float


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    prepared = df.copy()
    for column in ["open", "high", "low", "close", "volume"]:
        if column not in prepared.columns:
            prepared[column] = np.nan
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    prepared = prepared.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return prepared


def calculate_ema(df: pd.DataFrame, period: int = 200) -> float:
    ema = df["close"].ewm(span=period, adjust=False).mean()
    return float(ema.iloc[-1]) if not ema.empty else float(df["close"].iloc[-1])


def calculate_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> float:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if not pd.isna(value) else 50.0


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> float:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    return float(atr) if not pd.isna(atr) else 0.0


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    if len(df) < period + 1:
        return 1.0
    avg_volume = df["volume"].rolling(period).mean().iloc[-2]
    current_volume = df["volume"].iloc[-1]
    if pd.isna(avg_volume) or avg_volume <= 0:
        return 1.0
    return float(current_volume / avg_volume)


def calculate_candle_strength(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    current = df.iloc[-1]
    previous = df.iloc[-2]
    body = abs(current["close"] - current["open"])
    range_size = max(current["high"] - current["low"], 1e-9)
    body_ratio = body / range_size
    return float(min(body_ratio, 1.0))


def _recent_swing_high(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> float:
    return float(df["high"].iloc[-lookback - 1 : -1].max())


def _recent_swing_low(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> float:
    return float(df["low"].iloc[-lookback - 1 : -1].min())


def detect_sfp(df: pd.DataFrame, direction: str) -> dict[str, Any] | None:
    prepared = prepare_dataframe(df)
    if len(prepared) < 5:
        return None
    candle = prepared.iloc[-1]
    prev_close = float(prepared["close"].iloc[-2])
    prev_swing_low = _recent_swing_low(prepared)
    prev_swing_high = _recent_swing_high(prepared)

    if direction == "LONG":
        body = abs(candle["close"] - candle["open"])
        lower_wick = min(candle["open"], candle["close"]) - candle["low"]
        wick_ratio = lower_wick / max(body, 1e-9)
        swept = candle["low"] < prev_swing_low
        reclaimed = candle["close"] >= prev_swing_low * 0.999
        confirmation = candle["close"] > candle["open"] and candle["close"] > prev_close
        passed = swept and reclaimed and confirmation and wick_ratio >= MIN_WICK_PERCENT * 0.8
        return {
            "type": "SFP",
            "direction": "LONG",
            "passed": passed,
            "sweep_level": prev_swing_low,
            "wick_ratio": wick_ratio,
            "reason": "Liquidity sweep with bullish reclaim" if passed else "No valid bullish SFP",
        }

    if direction == "SHORT":
        body = abs(candle["close"] - candle["open"])
        upper_wick = candle["high"] - max(candle["open"], candle["close"])
        wick_ratio = upper_wick / max(body, 1e-9)
        swept = candle["high"] > prev_swing_high
        reclaimed = candle["close"] <= prev_swing_high * 1.001
        confirmation = candle["close"] < candle["open"] and candle["close"] < prev_close
        passed = swept and reclaimed and confirmation and wick_ratio >= MIN_WICK_PERCENT * 0.8
        return {
            "type": "SFP",
            "direction": "SHORT",
            "passed": passed,
            "sweep_level": prev_swing_high,
            "wick_ratio": wick_ratio,
            "reason": "Liquidity sweep with bearish reclaim" if passed else "No valid bearish SFP",
        }
    return None


def detect_mss(df: pd.DataFrame, direction: str) -> dict[str, Any] | None:
    prepared = prepare_dataframe(df)
    if len(prepared) < 5:
        return None
    current = prepared.iloc[-1]
    previous = prepared.iloc[-2]
    prev_swing_high = _recent_swing_high(prepared)
    prev_swing_low = _recent_swing_low(prepared)
    if direction == "LONG":
        breakout = current["close"] > prev_swing_high * 0.999 and current["high"] > prev_swing_high * 0.999
        confirmation = current["close"] > previous["close"] and current["close"] > current["open"]
        structure = current["close"] > previous["close"] and current["low"] >= prev_swing_low * 0.999
        passed = breakout and confirmation and structure and current["close"] > current["open"]
        return {
            "type": "MSS",
            "direction": "LONG",
            "passed": passed,
            "break_level": prev_swing_high,
            "reason": "Bullish structure break" if passed else "No valid bullish MSS",
        }
    if direction == "SHORT":
        breakdown = current["close"] < prev_swing_low * 1.001 and current["low"] < prev_swing_low * 1.001
        confirmation = current["close"] < previous["close"] and current["close"] < current["open"]
        structure = current["close"] < previous["close"] and current["high"] <= prev_swing_high * 1.001
        passed = breakdown and confirmation and structure and current["close"] < current["open"]
        return {
            "type": "MSS",
            "direction": "SHORT",
            "passed": passed,
            "break_level": prev_swing_low,
            "reason": "Bearish structure break" if passed else "No valid bearish MSS",
        }
    return None
