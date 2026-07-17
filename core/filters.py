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
# EMA 200 TREND
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


    if price > ema.iloc[-1]:

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


    return float(
        rsi.iloc[-1]
    )



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


    return float(
        tr
        .rolling(ATR_PERIOD)
        .mean()
        .iloc[-1]
    )



# ============================================================
# RSI FILTER
# ============================================================

def rsi_check(df, direction):


    rsi = calculate_rsi(df)


    if direction == "LONG":

        return 35 <= rsi <= 70


    if direction == "SHORT":

        return 30 <= rsi <= 65


    return False



# ============================================================
# ATR FILTER
# ============================================================

def atr_check(df):


    atr = calculate_atr(df)


    price = (
        df["close"]
        .iloc[-1]
    )


    return (
        atr / price >= 0.0025
    )



# ============================================================
# QUALITY SCORE
# ============================================================

def quality_check(
        df,
        direction,
        higher_trend=None
):


    score = 0



    # EMA200

    trend = ema200_trend(df)


    if trend == direction:

        score += 25


    else:

        score -= 10



    # RSI

    if rsi_check(
        df,
        direction
    ):

        score += 20



    else:

        score -= 10



    # ATR

    if atr_check(df):

        score += 15



    else:

        score -= 10



    # HTF

    if higher_trend:


        if direction == higher_trend:

            score += 25


        else:

            score -= 15



    # ограничение

    if score < 0:

        score = 0



    return (
        score >= 40,
        score
    )
