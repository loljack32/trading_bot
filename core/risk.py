from __future__ import annotations

import pandas as pd

from config import ATR_STOP_MULTIPLIER, MIN_RR, MIN_RISK_PCT, STOP_LOOKBACK
from core.indicators import prepare_dataframe
from core.models import RiskResult


def build_risk(df, direction: str, entry: float, atr: float) -> RiskResult:
    prepared = prepare_dataframe(df)
    if prepared.empty:
        return RiskResult(entry=entry, stop=entry, target=entry, risk=0.0, rr=0.0, valid=False, reason="No data")

    recent_low = float(prepared["low"].iloc[-STOP_LOOKBACK - 1 : -1].min())
    recent_high = float(prepared["high"].iloc[-STOP_LOOKBACK - 1 : -1].max())

    if direction == "LONG":
        stop = recent_low - atr * ATR_STOP_MULTIPLIER
        if stop >= entry:
            stop = entry - max(atr * ATR_STOP_MULTIPLIER, entry * MIN_RISK_PCT)
        risk = entry - stop
        target = entry + risk * 2
    else:
        stop = recent_high + atr * ATR_STOP_MULTIPLIER
        if stop <= entry:
            stop = entry + max(atr * ATR_STOP_MULTIPLIER, entry * MIN_RISK_PCT)
        risk = stop - entry
        target = entry - risk * 2

    if risk <= entry * MIN_RISK_PCT:
        return RiskResult(entry=entry, stop=stop, target=target, risk=risk, rr=0.0, valid=False, reason="Risk too small")
    rr = (target - entry) / risk if direction == "LONG" else (entry - target) / risk
    valid = rr >= MIN_RR
    return RiskResult(entry=entry, stop=stop, target=target, risk=risk, rr=rr, valid=valid, reason="" if valid else "RR too low")
