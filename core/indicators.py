import pandas as pd
import numpy as np

from config import (
    SWING_LOOKBACK,
    MIN_WICK_PERCENT,
    VOLUME_MULTIPLIER
)



# =====================================
# VOLUME CONFIRMATION
# =====================================

def volume_confirmation(df):


    avg_volume = (

        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]

    )


    current = df["volume"].iloc[-1]


    return current >= avg_volume * 0.8





# =====================================
# SFP
# =====================================

def bullish_sfp(df):


    candle = df.iloc[-2]


    lows = (

        df["low"]
        .iloc[-20:-2]
        .min()

    )


    wick = (

        candle["open"]

        -

        candle["low"]

    )



    body = abs(

        candle["close"]

        -

        candle["open"]

    )



    if body == 0:

        return False



    wick_ratio = wick / body



    return (

        candle["low"] < lows

        and

        candle["close"] > candle["open"]

        and

        wick_ratio >= MIN_WICK_PERCENT

    )




def bearish_sfp(df):


    candle = df.iloc[-2]


    highs = (

        df["high"]
        .iloc[-20:-2]
        .max()

    )



    wick = (

        candle["high"]

        -

        candle["close"]

    )


    body = abs(

        candle["close"]

        -

        candle["open"]

    )



    if body == 0:

        return False



    wick_ratio = wick / body



    return (

        candle["high"] > highs

        and

        candle["close"] < candle["open"]

        and

        wick_ratio >= MIN_WICK_PERCENT

    )






# =====================================
# MSS
# =====================================

def bullish_mss(df):


    last = df.iloc[-1]


    previous_high = (

        df["high"]
        .iloc[-10:-1]
        .max()

    )


    return (

        last["close"]

        >

        previous_high

    )




def bearish_mss(df):


    last = df.iloc[-1]


    previous_low = (

        df["low"]
        .iloc[-10:-1]
        .min()

    )


    return (

        last["close"]

        <

        previous_low

    )






# =====================================
# SIGNAL SCORE
# =====================================


def signal_score(df, direction):


    score = 0



    # MSS
    if direction == "LONG":

        if bullish_mss(df):

            score += 35


    else:

        if bearish_mss(df):

            score += 35




    # SFP

    if direction == "LONG":

        if bullish_sfp(df):

            score += 30


    else:

        if bearish_sfp(df):

            score += 30





    # volume

    if volume_confirmation(df):

        score += 20





    # свеча импульс

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


    if size > 0:


        if body / size > 0.5:

            score += 15




    return min(score,100)
