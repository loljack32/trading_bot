# ============================================================
# core/filters.py
# Advanced Quality Filters
# ============================================================

import pandas as pd

from config import (
    EMA_PERIOD,
    RSI_PERIOD,
    ATR_PERIOD
)



# ============================================================
# EMA TREND
# ============================================================

def ema200_trend(df):


    ema = (
        df["close"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False
        )
        .mean()
    )


    price = df["close"].iloc[-1]


    if price >= ema.iloc[-1]:

        return "LONG"


    return "SHORT"





# ============================================================
# RSI
# ============================================================

def calculate_rsi(df):


    delta = df["close"].diff()


    gain = (
        delta
        .clip(lower=0)
        .rolling(RSI_PERIOD)
        .mean()
    )


    loss = (
        -delta
        .clip(upper=0)
        .rolling(RSI_PERIOD)
        .mean()
    )


    rs = gain / loss


    rsi = 100 - (
        100 /
        (1 + rs)
    )


    value = rsi.iloc[-1]


    if pd.isna(value):

        return 50


    return float(value)





# ============================================================
# ATR
# ============================================================

def calculate_atr(df):


    high_low = (
        df["high"]
        -
        df["low"]
    )


    high_close = abs(
        df["high"]
        -
        df["close"].shift()
    )


    low_close = abs(
        df["low"]
        -
        df["close"].shift()
    )


    tr = pd.concat(
        [
            high_low,
            high_close,
            low_close
        ],
        axis=1
    ).max(axis=1)


    atr = (
        tr
        .rolling(ATR_PERIOD)
        .mean()
        .iloc[-1]
    )


    if pd.isna(atr):

        return 0


    return float(atr)





# ============================================================
# RSI FILTER
# ============================================================

def rsi_check(df, direction):


    rsi = calculate_rsi(df)



    if direction == "LONG":

        return (
            30 <= rsi <= 75
        )



    if direction == "SHORT":

        return (
            25 <= rsi <= 70
        )


    return False






# ============================================================
# ATR FILTER
# ============================================================

def atr_check(df):


    atr = calculate_atr(df)


    price = float(
        df["close"].iloc[-1]
    )


    if price == 0:

        return False



    volatility = atr / price


    return volatility >= 0.0015





# ============================================================
# QUALITY CHECK
# ============================================================

def quality_check(
        df,
        direction,
        higher_trend=None
):


    score = 0



    # EMA

    trend = ema200_trend(df)



    if trend == direction:

        score += 30



    # RSI

    if rsi_check(
        df,
        direction
    ):

        score += 20




    # ATR

    if atr_check(df):

        score += 20




    # HTF

    if higher_trend:


        if higher_trend == direction:

            score += 30


        else:

            score += 0




    if score > 100:

        score = 100



    return (
        score >= 50,
        score
    )
