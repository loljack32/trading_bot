# ============================================================
# core/filters.py
# Quality filters for SFP MSS BOT
# ============================================================

import pandas as pd



# ============================================================
# EMA 200 TREND
# ============================================================

def ema200_trend(df):

    ema = (
        df["close"]
        .ewm(
            span=200,
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

def calculate_rsi(
        df,
        period=14
):


    delta = df["close"].diff()


    gain = (
        delta
        .clip(lower=0)
        .rolling(period)
        .mean()
    )


    loss = (
        -delta
        .clip(upper=0)
        .rolling(period)
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

def calculate_atr(
        df,
        period=14
):


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
        .rolling(period)
        .mean()
        .iloc[-1]

    )





# ============================================================
# RSI FILTER
# ============================================================

def rsi_check(
        df,
        direction
):


    rsi = calculate_rsi(df)



    # LONG
    if direction == "LONG":


        if 40 <= rsi <= 65:

            return True



    # SHORT
    if direction == "SHORT":


        if 35 <= rsi <= 60:

            return True



    return False





# ============================================================
# ATR FILTER
# ============================================================

def atr_check(
        df
):


    atr = calculate_atr(df)


    price = (
        df["close"]
        .iloc[-1]
    )


    # волатильность минимум 0.3%

    if (
        atr / price
        >=
        0.003
    ):

        return True



    return False





# ============================================================
# COMPLETE QUALITY CHECK
# ============================================================

def quality_check(
        df,
        direction,
        higher_trend=None
):


    score = 0



    # -------------------------
    # EMA 200
    # -------------------------

    trend = ema200_trend(df)


    if trend == direction:

        score += 20


    else:

        return False, score





    # -------------------------
    # RSI
    # -------------------------

    if rsi_check(
        df,
        direction
    ):

        score += 10


    else:

        return False, score





    # -------------------------
    # ATR
    # -------------------------

    if atr_check(df):

        score += 10


    else:

        return False, score





    # -------------------------
    # HTF TREND
    # -------------------------

    if higher_trend:


        if direction != higher_trend:

            return False, score



        score += 20





    return True, score
