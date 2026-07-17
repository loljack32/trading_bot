from core.gecko import GeckoTerminal

from core.indicators import (
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss,
    volume_confirmation
)

from config import MIN_LIQUIDITY



gecko = GeckoTerminal()



# =====================================
# Список монет для сканирования
# =====================================

# Пока тестовый список.
# Позже сделаем автоматический поиск
# всех пулов через GeckoTerminal.


WATCHLIST = [

    {
        "name": "TEST",
        "network": "solana",
        "pool": "POOL_ADDRESS"
    }

]





# =====================================
# Основной сканер
# =====================================


def scan_market(timeframe):


    signals = []



    for coin in WATCHLIST:



        pool_data = gecko.get_pool_data(

            coin["network"],

            coin["pool"]

        )



        if not pool_data:

            continue



        liquidity = (
            pool_data["liquidity"]
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





        volume_ok = (
            volume_confirmation(
                candles
            )
        )



        if not volume_ok:

            continue





        # ==========================
        # LONG
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
        # SHORT
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


    price = (
        df.iloc[-1]["close"]
    )



    if direction == "LONG":


        stop = (
            df["low"]
            .tail(10)
            .min()
        )


        target = (
            price +
            (
                price-stop
            )
            *
            2
        )



    else:


        stop = (
            df["high"]
            .tail(10)
            .max()
        )


        target = (
            price -
            (
                stop-price
            )
            *
            2
        )





    return {


        "pair":
            coin["name"],


        "network":
            coin["network"],


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
            )

    }
