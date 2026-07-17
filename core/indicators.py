import pandas as pd

from config import (
    SWING_LOOKBACK,
    MIN_WICK_PERCENT,
    VOLUME_MULTIPLIER
)



# ==========================================
# Поиск Swing High / Swing Low
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



        previous_highs = (
            df.iloc[
                i-SWING_LOOKBACK:i
            ]["high"]
        )


        next_highs = (
            df.iloc[
                i+1:
                i+1+SWING_LOOKBACK
            ]["high"]
        )



        previous_lows = (
            df.iloc[
                i-SWING_LOOKBACK:i
            ]["low"]
        )


        next_lows = (
            df.iloc[
                i+1:
                i+1+SWING_LOOKBACK
            ]["low"]
        )



        # Swing High

        if (
            high >
            previous_highs.max()
            and
            high >
            next_highs.max()
        ):

            swing_highs.append(
                {
                    "index": i,
                    "price": high
                }
            )



        # Swing Low

        if (
            low <
            previous_lows.min()
            and
            low <
            next_lows.min()
        ):

            swing_lows.append(
                {
                    "index": i,
                    "price": low
                }
            )



    return (
        swing_highs,
        swing_lows
    )




# ==========================================
# Проверка объёма
# ==========================================


def volume_confirmation(df):


    current_volume = (
        df.iloc[-1]["volume"]
    )


    average_volume = (
        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )



    if (
        current_volume >
        average_volume *
        VOLUME_MULTIPLIER
    ):

        return True



    return False




# ==========================================
# Поиск Bullish SFP
# ==========================================


def bullish_sfp(df):


    swings = find_swings(df)

    lows = swings[1]


    if not lows:

        return False



    last_low = lows[-1]


    level = last_low["price"]


    candle = df.iloc[-1]



    # свеча пробила минимум
    # но закрылась выше


    wick_size = (
        level -
        candle["low"]
    )


    candle_range = (
        candle["high"]
        -
        candle["low"]
    )



    if candle_range == 0:

        return False



    wick_percent = (
        wick_size /
        candle_range
    )



    if (

        candle["low"] < level

        and

        candle["close"] > level

        and

        wick_percent >=
        MIN_WICK_PERCENT

    ):

        return True



    return False




# ==========================================
# Поиск Bearish SFP
# ==========================================


def bearish_sfp(df):


    swings = find_swings(df)


    highs = swings[0]


    if not highs:

        return False



    last_high = highs[-1]


    level = last_high["price"]


    candle = df.iloc[-1]



    wick_size = (
        candle["high"]
        -
        level
    )



    candle_range = (
        candle["high"]
        -
        candle["low"]
    )



    if candle_range == 0:

        return False



    wick_percent = (
        wick_size /
        candle_range
    )



    if (

        candle["high"] > level

        and

        candle["close"] < level

        and

        wick_percent >=
        MIN_WICK_PERCENT

    ):

        return True



    return False




# ==========================================
# MSS проверка
# ==========================================


def bullish_mss(df):


    highs, lows = find_swings(df)


    if len(highs) < 2:

        return False



    last_high = highs[-1]["price"]


    previous_high = highs[-2]["price"]



    current_close = (
        df.iloc[-1]["close"]
    )



    # пробой структуры вверх


    if (

        current_close >
        last_high

        and

        last_high >
        previous_high

    ):

        return True



    return False




def bearish_mss(df):


    highs, lows = find_swings(df)



    if len(lows) < 2:

        return False



    last_low = lows[-1]["price"]


    previous_low = lows[-2]["price"]



    current_close = (
        df.iloc[-1]["close"]
    )



    if (

        current_close <
        last_low

        and

        last_low <
        previous_low

    ):

        return True



    return False
