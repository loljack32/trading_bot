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

from config import (
    NETWORKS,
    MIN_LIQUIDITY,
    MIN_SIGNAL_SCORE
)


gecko = GeckoTerminal()
market = MarketScanner()



def scan_market(timeframe):


    signals = []



    for network in NETWORKS:



        pools = market.get_top_pools(

            network,

            100

        )



        for coin in pools:



            if coin["liquidity"] < MIN_LIQUIDITY:

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



            if (

                bullish_sfp(candles)

                and

                bullish_mss(candles)

            ):

                direction = "LONG"



            elif (

                bearish_sfp(candles)

                and

                bearish_mss(candles)

            ):

                direction = "SHORT"




            if not direction:

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

                    score

                )

            )



    return signals





def create_signal(

        coin,

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

            entry +

            (

                entry - stop

            )

            * 2

        )


    else:


        stop = float(

            df["high"]
            .tail(10)
            .max()

        )


        target = (

            entry -

            (

                stop - entry

            )

            * 2

        )



    return {


        "pair":

            coin["name"],


        "network":

            coin["network"],


        "pool":

            coin["pool"],


        "direction":

            direction,


        "confidence":

            score,


        "entry":

            round(entry, 8),


        "stop":

            round(stop, 8),


        "target":

            round(target, 8),


        "liquidity":

            round(
                coin["liquidity"],
                2
            ),


        "volume":

            round(
                coin["volume"],
                2
            )

    }
