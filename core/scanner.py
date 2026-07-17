from core.okx import OKXClient

from core.indicators import (
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss,
    volume_confirmation,
    signal_score
)

from config import (
    SYMBOLS,
    CANDLE_LIMIT,
    MIN_SIGNAL_SCORE
)



okx = OKXClient()





# =====================================
# Сканирование рынка OKX
# =====================================


def scan_market(timeframe):


    signals = []



    print(
        f"Scanning {timeframe}"
    )



    for symbol in SYMBOLS:



        print(

            "Checking",

            symbol

        )



        candles = okx.get_ohlcv(

            symbol,

            timeframe,

            CANDLE_LIMIT

        )



        if candles is None:

            continue



        if len(candles) < 100:

            continue




        if not volume_confirmation(candles):

            continue





        direction = None




        # =============================
        # LONG
        # =============================


        if (

            bullish_sfp(candles)

            and

            bullish_mss(candles)

        ):


            direction = "LONG"






        # =============================
        # SHORT
        # =============================


        elif (

            bearish_sfp(candles)

            and

            bearish_mss(candles)

        ):


            direction = "SHORT"






        if direction is None:

            continue





        score = signal_score(

            candles,

            direction

        )





        if score < MIN_SIGNAL_SCORE:

            continue





        signal = create_signal(

            symbol,

            candles,

            direction,

            score

        )



        signals.append(

            signal

        )



    return signals






# =====================================
# Формирование сигнала
# =====================================


def create_signal(

        symbol,

        df,

        direction,

        score

):


    entry = float(

        df.iloc[-1]["close"]

    )



    if direction == "LONG":


        stop = float(

            df["low"]

            .tail(10)

            .min()

        )



        target = (

            entry

            +

            (

                entry - stop

            )

            *

            2

        )



    else:



        stop = float(

            df["high"]

            .tail(10)

            .max()

        )



        target = (

            entry

            -

            (

                stop - entry

            )

            *

            2

        )





    return {


        "pair":

            symbol,



        "exchange":

            "OKX",



        "direction":

            direction,



        "confidence":

            score,



        "entry":

            round(

                entry,

                8

            ),



        "stop":

            round(

                stop,

                8

            ),



        "target":

            round(

                target,

                8

            ),



        "volume":

            round(

                float(

                    df.iloc[-1]["volume"]

                ),

                2

            )

    }
