# ============================================================
# core/scanner.py
# SFP MSS Scanner + TOP100 + Quality Filters + HTF
# ============================================================


from core.okx import OKXClient


from core.indicators import (
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss,
    volume_confirmation,
    signal_score
)


from core.filters import (
    ema200_trend,
    quality_check
)


from config import (
    CANDLE_LIMIT,
    MIN_SIGNAL_SCORE,
    HTF_TIMEFRAME,
    USE_HTF_FILTER
)





okx = OKXClient()



# кэш старшего тренда

htf_cache = {}





# ============================================================
# GET HTF TREND
# ============================================================


def get_higher_trend(symbol):


    if symbol in htf_cache:

        return htf_cache[symbol]



    candles = okx.get_ohlcv(

        symbol,

        HTF_TIMEFRAME,

        CANDLE_LIMIT

    )



    if candles is None:

        return None



    if len(candles) < 200:

        return None



    trend = ema200_trend(

        candles

    )



    htf_cache[symbol] = trend



    return trend





# ============================================================
# SCAN MARKET
# ============================================================


def scan_market(timeframe):


    signals = []



    global htf_cache

    htf_cache = {}



    print(

        f"\nScanning {timeframe}"

    )




    symbols = okx.get_top_symbols()



    if not symbols:


        print(

            "No symbols loaded"

        )


        return []





    print(

        "Analysing symbols:",

        len(symbols)

    )






    for symbol in symbols:



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



        if len(candles) < 200:

            continue






        # =================================================
        # HTF FILTER
        # =================================================


        higher_trend = None



        if (

            USE_HTF_FILTER

            and

            timeframe != HTF_TIMEFRAME

        ):


            higher_trend = get_higher_trend(

                symbol

            )


            print(

                "HTF:",

                higher_trend

            )






        # =================================================
        # CONDITIONS
        # =================================================


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






        # =================================================
        # ENTRY LOGIC
        # =================================================


        if long_sfp and long_mss:


            direction = "LONG"



        elif short_sfp and short_mss:


            direction = "SHORT"




        elif long_mss and volume_ok:


            direction = "LONG"



        elif short_mss and volume_ok:


            direction = "SHORT"





        if direction is None:

            continue






        # =================================================
        # QUALITY FILTER
        # =================================================


        passed, filter_score = quality_check(

            candles,

            direction,

            higher_trend

        )



        print(

            "Filter score:",

            filter_score

        )



        if not passed:


            print(

                "Rejected by filters"

            )


            continue






        # =================================================
        # FINAL SCORE
        # =================================================


        base_score = signal_score(

            candles,

            direction

        )



        final_score = (

            base_score

            +

            filter_score

        )




        print(

            "Final score:",

            final_score

        )





        if final_score < MIN_SIGNAL_SCORE:

            continue





        signals.append(

            create_signal(

                symbol,

                candles,

                direction,

                final_score

            )

        )






    return signals







# ============================================================
# CREATE SIGNAL
# ============================================================


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

            round(score),



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
