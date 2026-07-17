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
# MARKET SCANNER
# =====================================

def scan_market(timeframe):

    signals = []


    print(
        f"\nScanning {timeframe}"
    )


    for symbol in SYMBOLS:


        print(
            "\nChecking",
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




        volume_ok = volume_confirmation(
            candles
        )


        long_sfp = bullish_sfp(
            candles
        )

        short_sfp = bearish_sfp(
            candles
        )


        long_mss = bullish_mss(
            candles
        )

        short_mss = bearish_mss(
            candles
        )



        print(
            "Volume:",
            volume_ok
        )


        print(
            "LONG:",
            long_sfp,
            long_mss
        )


        print(
            "SHORT:",
            short_sfp,
            short_mss
        )



        direction = None



        # =========================
        # LONG
        # =========================

        if long_sfp and long_mss:

            direction = "LONG"



        # =========================
        # SHORT
        # =========================

        elif short_sfp and short_mss:

            direction = "SHORT"




        # если нет полного сетапа
        # но есть MSS + объём
        # даём шанс через score

        elif long_mss and volume_ok:

            direction = "LONG"



        elif short_mss and volume_ok:

            direction = "SHORT"



        if direction is None:

            continue




        score = signal_score(
            candles,
            direction
        )


        print(
            "Score:",
            score
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
# CREATE SIGNAL
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

            (entry - stop)

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

            (stop - entry)

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
            round(entry,8),


        "stop":
            round(stop,8),


        "target":
            round(target,8),


        "volume":
            round(
                float(
                    df.iloc[-1]["volume"]
                ),
                2
            )

    }
