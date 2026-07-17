from config import (
    SWING_LOOKBACK,
    MIN_WICK_PERCENT,
    VOLUME_MULTIPLIER,
    ATR_PERIOD
)



# =====================================
# Swing High / Swing Low
# =====================================


def find_swings(df):

    highs = []
    lows = []


    for i in range(
        SWING_LOOKBACK,
        len(df) - SWING_LOOKBACK
    ):

        high = df.iloc[i]["high"]
        low = df.iloc[i]["low"]


        left = df.iloc[
            i - SWING_LOOKBACK:i
        ]

        right = df.iloc[
            i + 1:i + 1 + SWING_LOOKBACK
        ]


        if (

            high > left["high"].max()

            and

            high > right["high"].max()

        ):

            highs.append({

                "index": i,

                "price": float(high)

            })


        if (

            low < left["low"].min()

            and

            low < right["low"].min()

        ):

            lows.append({

                "index": i,

                "price": float(low)

            })


    return highs, lows





# =====================================
# ATR
# =====================================


def calculate_atr(
        df,
        period=ATR_PERIOD
):

    data = df.copy()


    data["prev_close"] = (
        data["close"]
        .shift(1)
    )


    data["tr"] = data.apply(

        lambda x: max(

            x["high"] - x["low"],

            abs(
                x["high"] -
                x["prev_close"]
            ),

            abs(
                x["low"] -
                x["prev_close"]
            )

        ),

        axis=1

    )


    return (

        data["tr"]
        .rolling(period)
        .mean()
        .iloc[-1]

    )





# =====================================
# Volume
# =====================================


def volume_strength(df):


    current = df.iloc[-1]["volume"]


    average = (

        df["volume"]
        .rolling(20)
        .mean()
        .iloc[-1]

    )


    if average == 0:

        return 0


    return current / average





# =====================================
# Volume confirmation
# =====================================


def volume_confirmation(df):


    return (

        volume_strength(df)

        >=

        VOLUME_MULTIPLIER

    )





# =====================================
# Bullish SFP
# =====================================


def bullish_sfp(df):


    highs, lows = find_swings(df)


    if len(lows) < 2:

        return False



    level = lows[-2]["price"]


    candle = df.iloc[-1]


    size = (

        candle["high"]

        -

        candle["low"]

    )


    if size <= 0:

        return False



    wick = (

        level

        -

        candle["low"]

    )


    return (

        candle["low"] < level

        and

        candle["close"] > level

        and

        (wick / size) >= MIN_WICK_PERCENT

    )





# =====================================
# Bearish SFP
# =====================================


def bearish_sfp(df):


    highs, lows = find_swings(df)


    if len(highs) < 2:

        return False



    level = highs[-2]["price"]


    candle = df.iloc[-1]


    size = (

        candle["high"]

        -

        candle["low"]

    )


    if size <= 0:

        return False



    wick = (

        candle["high"]

        -

        level

    )


    return (

        candle["high"] > level

        and

        candle["close"] < level

        and

        (wick / size) >= MIN_WICK_PERCENT

    )





# =====================================
# Bullish MSS
# =====================================


def bullish_mss(df):


    highs, lows = find_swings(df)


    if len(highs) == 0:

        return False



    return (

        df.iloc[-1]["close"]

        >

        highs[-1]["price"]

    )





# =====================================
# Bearish MSS
# =====================================


def bearish_mss(df):


    highs, lows = find_swings(df)


    if len(lows) == 0:

        return False



    return (

        df.iloc[-1]["close"]

        <

        lows[-1]["price"]

    )





# =====================================
# Signal Score
# =====================================


def signal_score(
        df,
        direction
):


    score = 0



    if direction == "LONG":


        if bullish_sfp(df):

            score += 35


        if bullish_mss(df):

            score += 35



    else:


        if bearish_sfp(df):

            score += 35


        if bearish_mss(df):

            score += 35





    if volume_confirmation(df):

        score += 15





    atr = calculate_atr(df)


    price = df.iloc[-1]["close"]



    if price > 0:


        if (

            atr / price

            >=

            0.003

        ):

            score += 15





    return min(
        score,
        100
    )
