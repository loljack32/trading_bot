from core.gecko import GeckoTerminal
from core.market import MarketScanner

from core.indicators import (
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss,
    volume_confirmation
)

from config import MIN_LIQUIDITY


gecko = GeckoTerminal()
market = MarketScanner()



# =====================================
# Основной сканер рынка
# =====================================

def scan_market(timeframe):

    signals = []


    # Получаем топовые пулы автоматически

    pools = market.get_top_pools(
        "solana",
        100
    )


    for coin in pools:


        liquidity = coin.get(
            "liquidity",
            0
        )


        # фильтр ликвидности

        if liquidity < MIN_LIQUIDITY:

            continue



        candles = gecko.get_ohlcv(

            coin["network"],

            coin["pool"],

            timeframe

        )



        if candles is None:

            continue



        if len(candles) < 50:

            continue



        volume_ok = volume_confirmation(
            candles
        )



        if not volume_ok:

            continue




        # ==========================
        # LONG SIGNAL
        # ==========================


        if (

            bullish_sfp(candles)

            and

            bullish_mss(candles)

        ):


            signals.append(

                create_signal(

                    coin,

                    candles,

                    "LONG",

                    liquidity

                )

            )





        # ==========================
        # SHORT SIGNAL
        # ==========================


        if (

            bearish_sfp(candles)

            and

            bearish_mss(candles)

        ):


            signals.append(

                create_signal(

                    coin,

                    candles,

                    "SHORT",

                    liquidity

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

        liquidity

):


    price = float(
        df.iloc[-1]["close"]
    )



    if direction == "LONG":


        stop = float(
            df["low"]
            .tail(10)
            .min()
        )


        target = (
            price
            +
            (
                price - stop
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
            price
            -
            (
                stop - price
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


        "entry":
            round(
                price,
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
