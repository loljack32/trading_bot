import pandas as pd

from config import (
    SWING_LOOKBACK,
    MIN_WICK_PERCENT,
    VOLUME_MULTIPLIER
)



# ==========================================
# Swing High / Swing Low
# ==========================================


def find_swings(df):

    swing_highs = []
    swing_lows = []


    for i in range(
        SWING_LOOKBACK,
        len(df) - SWING_LOOKBACK
    ):


        high = df.iloc[i]["high"]
        low = df.iloc[i]["low"]


        left = df.iloc[
            i-SWING_LOOKBACK:i
        ]

        right = df.iloc[
            i+1:i+1+SWING_LOOKBACK
        ]



        if (

            high > left["high"].max()

            and

            high > right["high"].max()

        ):

            swing_highs.append(
                {
                    "index": i,
                    "price": high
                }
            )



        if (

            low < left["low"].min()

            and

            low < right["low"].min()

        ):

            swing_lows.append(
                {
                    "index": i,
                    "price": low
                }
            )



    return swing_highs, swing_lows





# ==========================================
# ATR
# ==========================================


def calculate_atr(
        df,
        period=14
):


    data = df.copy()



    data["previous_close"] = (
        data["close"]
        .shift(1)
    )



    data["tr"] = data.apply(

        lambda x:

        max(

            x["high"] - x["low"],

            abs(
                x["high"]
                -
                x["previous_close"]
            ),

            abs(
                x["low"]
                -
                x["previous_close"]
            )

        ),

        axis=1

    )



    atr = (
        data["tr"]
        .rolling(period)
        .mean()
        .iloc[-1]
    )


    return atr





# ==========================================
# Объём
# ==========================================


def volume_confirmation(df):


    current = (
        df.iloc[-1]["volume"]
    )


    average = (

        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]

    )



    if current > average * VOLUME_MULTIPLIER:

        return True


    return False





# ==========================================
# Bullish SFP
# ==========================================


def bullish_sfp(df):


    highs, lows = find_swings(df)



    if not lows:

        return False



    level = lows[-1]["price"]



    candle = df.iloc[-1]



    wick = (
        level -
        candle["low"]
    )



    size = (
        candle["high"]
        -
        candle["low"]
    )



    if size == 0:

        return False



    wick_ratio = wick / size



    return (

        candle["low"] < level

        and

        candle["close"] > level

        and

        wick_ratio >= MIN_WICK_PERCENT

    )





# ==========================================
# Bearish SFP
# ==========================================


def bearish_sfp(df):


    highs, lows = find_swings(df)



    if not highs:

        return False



    level = highs[-1]["price"]



    candle = df.iloc[-1]



    wick = (
        candle["high"]
        -
        level
    )



    size = (
        candle["high"]
        -
        candle["low"]
    )



    if size == 0:

        return False



    wick_ratio = wick / size



    return (

        candle["high"] > level

        and

        candle["close"] < level

        and

        wick_ratio >= MIN_WICK_PERCENT

    )





# ==========================================
# MSS
# ==========================================


def bullish_mss(df):


    highs, lows = find_swings(df)



    if len(highs) < 2:

        return False



    return (

        df.iloc[-1]["close"]

        >

        highs[-1]["price"]

    )





def bearish_mss(df):


    highs, lows = find_swings(df)



    if len(lows) < 2:

        return False



    return (

        df.iloc[-1]["close"]

        <

        lows[-1]["price"]

    )





# ==========================================
# Confidence Score
# ==========================================


def signal_score(df, direction):


    score = 0



    # SFP

    if direction == "LONG":

        if bullish_sfp(df):

            score += 30


        if bullish_mss(df):

            score += 30



    else:


        if bearish_sfp(df):

            score += 30


        if bearish_mss(df):

            score += 30



    # Volume

    if volume_confirmation(df):

        score += 20



    # ATR

    atr = calculate_atr(df)

    price = df.iloc[-1]["close"]



    if atr / price > 0.005:

        score += 20



    return min(
        score,
        100
    )
