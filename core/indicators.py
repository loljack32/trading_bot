from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import (
    ATR_PERIOD,
    MIN_WICK_PERCENT,
    RSI_PERIOD,
    SWING_LOOKBACK,
    SWING_LEFT,
    SWING_RIGHT,
    SFP_SWEEP_ATR_FACTOR,
    MSS_LOOKBACK_SWINGS,
)
from utils.helpers import safe_float
from utils.logger import get_logger

logger = get_logger("indicators")


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
    # Wilder's ATR (EMA of TR with alpha=1/period)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean().iloc[-1]
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
    # Find the most recent local swing high (local maximum)
    # Use a pivot with left/right window to reduce noise (require stronger pivot)
    left = SWING_LEFT
    right = SWING_RIGHT
    start = max(left, len(df) - lookback - 1)
    end = len(df) - right
    for i in range(end - 1, start - 1, -1):
        if i <= left - 1 or i + right >= len(df):
            continue
        left_max = df["high"].iloc[i - left : i].max()
        right_max = df["high"].iloc[i + 1 : i + 1 + right].max()
        if df["high"].iloc[i] > left_max and df["high"].iloc[i] > right_max:
            return float(df["high"].iloc[i])
    # fallback to max in window
    return float(df["high"].iloc[max(0, len(df) - lookback - 1) : len(df) - 1].max())


def _recent_swing_low(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> float:
    # Find the most recent local swing low (local minimum)
    left = SWING_LEFT
    right = SWING_RIGHT
    start = max(left, len(df) - lookback - 1)
    end = len(df) - right
    for i in range(end - 1, start - 1, -1):
        if i <= left - 1 or i + right >= len(df):
            continue
        left_min = df["low"].iloc[i - left : i].min()
        right_min = df["low"].iloc[i + 1 : i + 1 + right].min()
        if df["low"].iloc[i] < left_min and df["low"].iloc[i] < right_min:
            return float(df["low"].iloc[i])
    # fallback to min in window
    return float(df["low"].iloc[max(0, len(df) - lookback - 1) : len(df) - 1].min())


def detect_sfp(df: pd.DataFrame, direction: str) -> dict[str, Any] | None:
    prepared = prepare_dataframe(df)
    if len(prepared) < 3:
        return None
    candle = prepared.iloc[-1]
    prev_swing_low = _recent_swing_low(prepared)
    prev_swing_high = _recent_swing_high(prepared)

    if direction == "LONG":
        candle_range = max(candle["high"] - candle["low"], 1e-9)
        lower_wick = min(candle["open"], candle["close"]) - candle["low"]
        wick_percent = lower_wick / candle_range
        swept = candle["low"] < prev_swing_low
        # reclaimed: closed back inside or above the sweep level (tolerance)
        reclaimed = candle["close"] >= prev_swing_low * 0.999
        # ATR based sweep distance filter to avoid huge impulsive moves
        atr = calculate_atr(prepared)
        sweep_distance = abs(prev_swing_low - candle["low"]) if not pd.isna(prev_swing_low) else float("inf")
        sweep_ok = (atr <= 0) or (sweep_distance <= atr * 0.3)
        # confirmation: reclaimed is required; wick must also be meaningful
        passed = swept and reclaimed and (wick_percent >= MIN_WICK_PERCENT * 0.8) and sweep_ok
        return {
            "type": "SFP",
            "direction": "LONG",
            "passed": passed,
            "sweep_level": prev_swing_low,
            "wick_percent": wick_percent,
            "reason": "Liquidity sweep with bullish reclaim" if passed else "No valid bullish SFP",
        }

    if direction == "SHORT":
        candle_range = max(candle["high"] - candle["low"], 1e-9)
        upper_wick = candle["high"] - max(candle["open"], candle["close"])
        wick_percent = upper_wick / candle_range
        swept = candle["high"] > prev_swing_high
        reclaimed = candle["close"] <= prev_swing_high * 1.001
        atr = calculate_atr(prepared)
        sweep_distance = abs(prev_swing_high - candle["high"]) if not pd.isna(prev_swing_high) else float("inf")
        sweep_ok = (atr <= 0) or (sweep_distance <= atr * 0.3)
        passed = swept and reclaimed and (wick_percent >= MIN_WICK_PERCENT * 0.8) and sweep_ok
        return {
            "type": "SFP",
            "direction": "SHORT",
            "passed": passed,
            "sweep_level": prev_swing_high,
            "wick_percent": wick_percent,
            "reason": "Liquidity sweep with bearish reclaim" if passed else "No valid bearish SFP",
        }
    return None


def detect_mss(df: pd.DataFrame, direction: str) -> dict[str, Any] | None:
    """Detect Multiple Swing Structure (MSS): simplified hybrid approach.
    
    MSS indicates potential continuation after liquidity hunt.
    We check:
    1. Swing extremes: higher highs for bearish, lower lows for bullish
    2. Current candle breaks these extremes
    3. Directional alignment with requested direction
    """
    prepared = prepare_dataframe(df)
    if len(prepared) < 5:
        return None
    
    current = prepared.iloc[-1]
    close = float(current["close"])
    
    # Get recent swing extremes (last 10-20 swings)
    recent_high = _recent_swing_high(prepared, lookback=20)
    recent_low = _recent_swing_low(prepared, lookback=20)
    
    # Check for structure pattern: higher highs OR lower lows in last few candles
    if len(prepared) >= 10:
        recent_highs = prepared["high"].iloc[-10:].values
        recent_lows = prepared["low"].iloc[-10:].values
        
        # Detect higher highs or lower lows
        has_hh = len(recent_highs) >= 3 and recent_highs[-1] > recent_highs[-3]
        has_ll = len(recent_lows) >= 3 and recent_lows[-1] < recent_lows[-3]
    else:
        has_hh = False
        has_ll = False
    
    passed = False
    reason = "No valid MSS"
    break_level = None
    
    if direction == "LONG":
        # LONG: look for lower lows (bearish structure) that gets broken on upside
        # Current should close above recent high or break above recent significant level
        if has_ll and close > recent_high * 0.9995:
            passed = True
            reason = "Bullish MSS: lower lows + break above recent high"
            break_level = recent_high
        elif close > recent_high and has_ll:
            passed = True
            reason = "Bullish MSS: break of recent high with lower lows"
            break_level = recent_high
            
    elif direction == "SHORT":
        # SHORT: look for higher highs (bullish structure) that gets broken on downside
        # Current should close below recent low or break below recent significant level
        if has_hh and close < recent_low * 1.0005:
            passed = True
            reason = "Bearish MSS: higher highs + break below recent low"
            break_level = recent_low
        elif close < recent_low and has_hh:
            passed = True
            reason = "Bearish MSS: break of recent low with higher highs"
            break_level = recent_low
    
    return {
        "type": "MSS",
        "direction": direction,
        "passed": passed,
        "break_level": break_level,
        "reason": reason,
    }
