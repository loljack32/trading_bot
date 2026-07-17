import pandas as pd


def ema_trend(df, period=200):

    ema = (
        df["close"]
        .ewm(span=period)
        .mean()
    )


    price = df["close"].iloc[-1]


    if price > ema.iloc[-1]:

        return "LONG"


    return "SHORT"





def rsi_filter(df):


    delta = df["close"].diff()


    gain = (
        delta.clip(lower=0)
        .rolling(14)
        .mean()
    )


    loss = (
        -delta.clip(upper=0)
        .rolling(14)
        .mean()
    )


    rs = gain / loss


    rsi = 100 - (
        100 /
        (1 + rs)
    )


    value = rsi.iloc[-1]


    return value





def atr(df, period=14):


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



    return (
        tr
        .rolling(period)
        .mean()
        .iloc[-1]
    )





def quality_check(
        df,
        direction,
        higher_trend=None
):


    score = 0



    # EMA TREND

    trend = ema_trend(df)



    if direction == trend:

        score += 25

    else:

        return False, score





    # RSI


    rsi = rsi_filter(df)



    if 35 < rsi < 65:

        score += 25



    else:

        return False, score





    # ATR


    current_atr = atr(df)



    if current_atr > 0:

        score += 25





    # HIGHER TF


    if higher_trend:


        if direction != higher_trend:

            return False, score


        score += 25




    return True, score
