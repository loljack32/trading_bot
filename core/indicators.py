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
    if len(prepared) < 5:
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
    prepared = prepare_dataframe(df)
    if len(prepared) < 5:
        return None
    current = prepared.iloc[-1]

    # Build ordered swings using a stronger pivot (left/right window)
    def get_recent_swings(window: int = SWING_LOOKBACK + 10, left: int | None = None, right: int | None = None):
        swings: list[tuple[int, str, float]] = []  # (index, 'H'|'L', value)
        if left is None:
            left = SWING_LEFT
        if right is None:
            right = SWING_RIGHT
        start = max(left, len(prepared) - window - 1)
        end = len(prepared) - right
        for i in range(start, end):
            if i - left < 0 or i + right >= len(prepared):
                continue
            # check pivot high
            left_max = prepared["high"].iloc[i - left : i].max()
            right_max = prepared["high"].iloc[i + 1 : i + 1 + right].max()
            if prepared["high"].iloc[i] > left_max and prepared["high"].iloc[i] > right_max:
                swings.append((i, "H", float(prepared["high"].iloc[i])))
                continue
            # check pivot low
            left_min = prepared["low"].iloc[i - left : i].min()
            right_min = prepared["low"].iloc[i + 1 : i + 1 + right].min()
            if prepared["low"].iloc[i] < left_min and prepared["low"].iloc[i] < right_min:
                swings.append((i, "L", float(prepared["low"].iloc[i])))
        return swings

    swings = get_recent_swings()

    # analyze ordered swings for alternating structure (H L H L ...)
    def alternating_sequence(sw):
        # collapse consecutive same-type swings, keep the most extreme among them
        seq: list[tuple[int, str, float]] = []
        for s in sw:
            if not seq or seq[-1][1] != s[1]:
                seq.append(s)
            else:
                # same type as previous — keep the extreme
                prev_idx, prev_t, prev_v = seq[-1]
                _, cur_t, cur_v = s
                if cur_t == "H":
                    # keep the higher high
                    if cur_v > prev_v:
                        seq[-1] = s
                else:
                    # keep the lower low
                    if cur_v < prev_v:
                        seq[-1] = s
        return seq

    seq = alternating_sequence(swings)

    def detect_structure_from_seq(sq, lookback_windows: int = MSS_LOOKBACK_SWINGS):
        # scan recent subsequences (length 4) within the last `lookback_windows` swings
        if len(sq) < 4:
            return None
        start = max(0, len(sq) - lookback_windows)
        # iterate from newest subsequence to oldest to return freshest confirmed structure
        end = len(sq) - 4
        for i in range(end, start - 1, -1):
            tail = sq[i : i + 4]
            types = [t for (_, t, _) in tail]
            if types == ["H", "L", "H", "L"]:
                highs = [v for _, t, v in tail if t == "H"]
                lows = [v for _, t, v in tail if t == "L"]
                if len(highs) >= 2 and len(lows) >= 2 and highs[-1] > highs[-2] and lows[-1] > lows[-2]:
                    last_low = tail[-1][2]
                    return ("bullish", last_low)
            if types == ["L", "H", "L", "H"]:
                highs = [v for _, t, v in tail if t == "H"]
                lows = [v for _, t, v in tail if t == "L"]
                if len(highs) >= 2 and len(lows) >= 2 and highs[-1] < highs[-2] and lows[-1] < lows[-2]:
                    last_high = tail[-1][2]
                    return ("bearish", last_high)
        return None

    struct = detect_structure_from_seq(seq)
    strength = calculate_candle_strength(prepared)

    # displacement check to avoid small candles being considered MSS
    atr = calculate_atr(prepared)
    bodies = (prepared["close"] - prepared["open"]).abs()
    avg_body = bodies.rolling(10).mean().iloc[-2] if len(prepared) > 11 else float(bodies.mean())
    avg_body = float(avg_body) if not pd.isna(avg_body) else 0.0
    body = abs(current["close"] - current["open"])
    # stronger displacement: require significant body AND momentum
    displacement_pass = (body > max(atr * 0.8, avg_body * 1.2)) and (strength >= 0.3)

    passed = False
    reason = "No valid MSS"
    break_level = None

    if struct is not None:
        kind, level = struct
        break_level = level
        if kind == "bullish":
            # bullish prior structure -> look for breakdown of that HL (use close to avoid pokes)
            breakdown = current["close"] < level * 0.999
            passed = breakdown and displacement_pass
            reason = "Bearish MSS (break of HL)" if passed else "No valid bearish MSS"
        elif kind == "bearish":
            # use close for breakout as well
            breakout = current["close"] > level * 1.001
            passed = breakout and displacement_pass
            reason = "Bullish MSS (break of HH)" if passed else "No valid bullish MSS"

    if direction == "SHORT":
        return {"type": "MSS", "direction": "SHORT", "passed": passed and struct is not None and kind == "bullish", "break_level": break_level, "reason": reason}

    if direction == "LONG":
        return {"type": "MSS", "direction": "LONG", "passed": passed and struct is not None and kind == "bearish", "break_level": break_level, "reason": reason}
    return None
