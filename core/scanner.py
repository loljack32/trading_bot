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
    MIN_SIGNAL_SCORE
)



okx = OKXClient()



# =====================================
# Список инструментов OKX
# =====================================

WATCHLIST = [

    "BTC-USDT",

    "ETH-USDT",

    "SOL-USDT",

    "XRP-USDT",

    "DOGE-USDT",

    "AVAX-USDT",

    "LINK-USDT",

    "ADA-USDT",

    "DOT-USDT"

]




# =====================================
# Сканирование рынка
# =====================================


def scan_market(timeframe):


    signals = []



    for symbol in WATCHLIST:



        candles = okx.get_ohlcv(

            symbol,

            timeframe,

            200

        )



        if candles is None:

            continue



        if len(candles) < 100:

            continue




        if not volume_confirmation(candles):

            continue




        direction = None




        # LONG

        if (

            bullish_sfp(candles)

            and

            bullish_mss(candles)

        ):

            direction = "LONG"




        # SHORT

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




        signals.append(

            create_signal(

                symbol,

                candles,

                direction,

                score

            )

        )



    return signals






# =====================================
# Создание сигнала
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


        "network":

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



        "liquidity":

            "N/A",



        "volume":

            round(

                df.iloc[-1]["volume"],

                2

            )

    }
