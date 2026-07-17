# ============================================================
# core/indicators.py
# SFP MSS BOT
# Advanced Market Structure Indicators
# ============================================================


import pandas as pd
import numpy as np


from config import (
    SWING_LOOKBACK,
    MIN_WICK_PERCENT,
    VOLUME_MULTIPLIER
)





# ============================================================
# VOLUME CONFIRMATION
# ============================================================


def volume_confirmation(df):


    if len(df) < 20:

        return False



    avg_volume = (

        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-2]

    )



    current_volume = (

        df["volume"]
        .iloc[-1]

    )



    if pd.isna(avg_volume):

        return False



    return (

        current_volume

        >=

        avg_volume * VOLUME_MULTIPLIER

    )







# ============================================================
# SWING LEVELS
# ============================================================


def get_swing_high(df, lookback=SWING_LOOKBACK):


    return (

        df["high"]
        .iloc[-lookback-1:-1]
        .max()

    )





def get_swing_low(df, lookback=SWING_LOOKBACK):


    return (

        df["low"]
        .iloc[-lookback-1:-1]
        .min()

    )







# ============================================================
# SFP
# ============================================================


def bullish_sfp(df):


    if len(df) < 30:

        return False



    candle = df.iloc[-2]



    swing_low = (

        df["low"]
        .iloc[-22:-2]
        .min()

    )



    body = abs(

        candle["close"]

        -

        candle["open"]

    )



    lower_wick = (

        min(

            candle["open"],

            candle["close"]

        )

        -

        candle["low"]

    )



    if body <= 0:

        return False



    wick_ratio = lower_wick / body



    return (

        candle["low"]

        <

        swing_low

        and

        candle["close"]

        >

        candle["open"]

        and

        wick_ratio

        >=

        MIN_WICK_PERCENT

    )







def bearish_sfp(df):


    if len(df) < 30:

        return False



    candle = df.iloc[-2]



    swing_high = (

        df["high"]
        .iloc[-22:-2]
        .max()

    )



    body = abs(

        candle["close"]

        -

        candle["open"]

    )



    upper_wick = (

        candle["high"]

        -

        max(

            candle["open"],

            candle["close"]

        )

    )



    if body <= 0:

        return False



    wick_ratio = upper_wick / body



    return (

        candle["high"]

        >

        swing_high

        and

        candle["close"]

        <

        candle["open"]

        and

        wick_ratio

        >=

        MIN_WICK_PERCENT

    )








# ============================================================
# MARKET STRUCTURE SHIFT
# ============================================================


def bullish_mss(df):


    if len(df) < 20:

        return False



    last = df.iloc[-1]



    swing_high = get_swing_high(

        df,

        10

    )



    previous_close = (

        df["close"]

        .iloc[-2]

    )



    return (

        previous_close

        <=

        swing_high

        and

        last["close"]

        >

        swing_high

    )







def bearish_mss(df):


    if len(df) < 20:

        return False



    last = df.iloc[-1]



    swing_low = get_swing_low(

        df,

        10

    )



    previous_close = (

        df["close"]

        .iloc[-2]

    )



    return (

        previous_close

        >=

        swing_low

        and

        last["close"]

        <

        swing_low

    )







# ============================================================
# IMPULSE CANDLE
# ============================================================


def impulse_confirmation(df):


    candle = df.iloc[-1]



    body = abs(

        candle["close"]

        -

        candle["open"]

    )



    size = (

        candle["high"]

        -

        candle["low"]

    )



    if size <= 0:

        return False



    return (

        body / size >= 0.5

    )







# ============================================================
# SIGNAL SCORE
# ============================================================


def signal_score(df, direction):


    score = 0



    # -------------------------
    # MSS
    # -------------------------


    if direction == "LONG":


        if bullish_mss(df):

            score += 35



    else:


        if bearish_mss(df):

            score += 35






    # -------------------------
    # SFP
    # -------------------------


    if direction == "LONG":


        if bullish_sfp(df):

            score += 25



    else:


        if bearish_sfp(df):

            score += 25






    # -------------------------
    # Volume
    # -------------------------


    if volume_confirmation(df):

        score += 20






    # -------------------------
    # Impulse
    # -------------------------


    if impulse_confirmation(df):

        score += 20






    return min(

        score,

        100

    )
