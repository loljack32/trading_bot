from core.gecko import GeckoTerminal
from core.market import MarketScanner

from core.indicators import (
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss,
    volume_confirmation,
    signal_score
)

from config import MIN_LIQUIDITY


gecko = GeckoTerminal()
market = MarketScanner()



# минимальный рейтинг сигнала

MIN_SIGNAL_SCORE = 70




# =====================================
# Сканирование рынка
# =====================================


def scan_market(timeframe):


    signals = []



    pools = market.get_top_pools(

        "solana",

        100

    )



    for coin in pools:



        liquidity = coin.get(

            "liquidity",

            0

        )



        if liquidity < MIN_LIQUIDITY:

            continue




        candles = gecko.get_ohlcv(

            coin["network"],

            coin["pool"],

            timeframe

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

                coin,

                candles,

                direction,

                liquidity,

                score

            )

        )



    return signals





# =====================================
# Создание сигнала
# =====================================


def create_signal(

        coin,

        df,

        direction,

        liquidity,

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

            coin.get(
                "name",
                "UNKNOWN"
            ),


        "network":

            coin.get(
                "network"
            ),


        "pool":

            coin.get(
                "pool"
            ),



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

            round(
                liquidity,
                2
            ),



        "volume":

            round(
                coin.get(
                    "volume",
                    0
                ),
                2
            )

    }
