# ============================================================
# core/quality.py
# Signal Quality Filter
# ============================================================

import pandas as pd



# ============================================================
# EMA 200 TREND
# ============================================================

def ema_trend(df, period=200):

    ema = (
        df["close"]
        .ewm(
            span=period,
            adjust=False
        )
        .mean()
    )


    price = float(
        df["close"].iloc[-1]
    )


    ema_value = float(
        ema.iloc[-1]
    )


    if price > ema_value:

        return "LONG"


    return "SHORT"





# ============================================================
# RSI
# ============================================================

def rsi_filter(
        df,
        period=14
):


    delta = (
        df["close"]
        .diff()
    )


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


    rsi = (
        100
        -
        (
            100 /
            (1 + rs)
        )
    )


    return float(
        rsi.iloc[-1]
    )





# ============================================================
# ATR
# ============================================================

def atr(
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
# QUALITY CHECK
# ============================================================

def quality_check(
        df,
        direction,
        higher_trend=None
):


    quality = 0



    # -----------------------------
    # EMA 200
    # -----------------------------

    trend = ema_trend(df)



    if direction == trend:

        quality += 25

        print(
            "EMA200: OK"
        )


    else:

        quality -= 15

        print(
            "EMA200: AGAINST TREND"
        )





    # -----------------------------
    # RSI
    # -----------------------------

    rsi = rsi_filter(df)


    print(
        "RSI:",
        round(rsi,2)
    )



    if 35 <= rsi <= 65:

        quality += 25

        print(
            "RSI: OK"
        )


    elif direction == "LONG" and rsi < 35:

        quality -= 10

        print(
            "RSI: OVERSOLD"
        )


    elif direction == "SHORT" and rsi > 65:

        quality -= 10

        print(
            "RSI: OVERBOUGHT"
        )


    else:

        quality += 5





    # -----------------------------
    # ATR
    # -----------------------------

    current_atr = atr(df)


    if current_atr > 0:

        quality += 25

        print(
            "ATR: OK"
        )





    # -----------------------------
    # HIGHER TIMEFRAME TREND
    # -----------------------------

    if higher_trend:


        if direction == higher_trend:

            quality += 25

            print(
                "HTF TREND: OK"
            )


        else:

            quality -= 25

            print(
                "HTF TREND: AGAINST"
            )




    # минимум качества

    if quality >= 40:

        return True, quality



    return False, quality
