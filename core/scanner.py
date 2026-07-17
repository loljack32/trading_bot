# ============================================================
# core/scanner.py
# SFP MSS Scanner
# TOP100
# HTF Filter
# Quality Filter
# Score Ranking
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



# кеш HTF тренда

htf_cache = {}





# ============================================================
# GET HIGHER TIMEFRAME TREND
# ============================================================

def get_higher_trend(symbol):


    if symbol in htf_cache:

        return htf_cache[symbol]



    try:


        candles = okx.get_ohlcv(

            symbol,

            HTF_TIMEFRAME,

            CANDLE_LIMIT

        )



        if candles is None:

            return None



        if len(candles) < 100:

            return None



        trend = ema200_trend(

            candles

        )



        htf_cache[symbol] = trend



        return trend



    except Exception as e:


        print(

            "HTF ERROR",

            symbol,

            e

        )


        return None







# ============================================================
# SCAN MARKET
# ============================================================


def scan_market(timeframe):


    global htf_cache


    htf_cache = {}



    signals = []



    print()

    print(

        "Scanning",

        timeframe

    )




    try:


        symbols = okx.get_top_symbols()



    except Exception as e:


        print(

            "SYMBOL ERROR",

            e

        )


        return []





    if not symbols:


        print(

            "No symbols"

        )


        return []





    print(

        "Symbols:",

        len(symbols)

    )





    checked = 0

    setups = 0

    rejected = 0





    for symbol in symbols:



        try:



            candles = okx.get_ohlcv(

                symbol,

                timeframe,

                CANDLE_LIMIT

            )



            if candles is None:

                continue



            if len(candles) < 100:

                continue




            checked += 1





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







            # =================================================
            # INDICATORS
            # =================================================


            vol = volume_confirmation(

                candles

            )



            bull_sfp = bullish_sfp(

                candles

            )


            bear_sfp = bearish_sfp(

                candles

            )



            bull_mss = bullish_mss(

                candles

            )


            bear_mss = bearish_mss(

                candles

            )






            direction = None






            # =================================================
            # ENTRY LOGIC
            # =================================================


            if bull_sfp and bull_mss:


                direction = "LONG"



            elif bear_sfp and bear_mss:


                direction = "SHORT"




            elif bull_mss and vol:


                direction = "LONG"



            elif bear_mss and vol:


                direction = "SHORT"





            if direction is None:


                continue





            setups += 1



            print()

            print(

                "SETUP",

                symbol,

                direction

            )





            # =================================================
            # QUALITY
            # =================================================


            passed, filter_score = quality_check(

                candles,

                direction,

                higher_trend

            )




            print(

                "QUALITY",

                filter_score,

                "PASS",

                passed

            )





            if not passed:


                rejected += 1

                continue






            # =================================================
            # SCORE
            # =================================================


            base_score = signal_score(

                candles,

                direction

            )




            final_score = round(

                (

                    base_score * 0.6

                )

                +

                (

                    filter_score * 0.4

                )

            )




            print(

                "SCORE",

                base_score,

                final_score

            )





            if final_score < MIN_SIGNAL_SCORE:


                print(

                    "LOW SCORE"

                )


                continue







            signal = create_signal(

                symbol,

                candles,

                direction,

                final_score,

                timeframe

            )



            signals.append(

                signal

            )



        except Exception as e:


            print(

                "SCAN ERROR",

                symbol,

                e

            )




    # =================================================
    # SORT
    # =================================================


    signals.sort(

        key=lambda x:

        x["confidence"],

        reverse=True

    )





    print()

    print(

        "Checked:",

        checked

    )


    print(

        "Setups:",

        setups

    )


    print(

        "Rejected:",

        rejected

    )


    print(

        "Signals found:",

        len(signals)

    )



    return signals







# ============================================================
# CREATE SIGNAL
# ============================================================


def create_signal(

        symbol,

        df,

        direction,

        score,

        timeframe

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



        risk = entry - stop




        if risk <= 0:


            stop = entry * 0.99


            risk = entry - stop




        target = (

            entry

            +

            risk * 2

        )





    else:



        stop = float(

            df["high"]

            .tail(10)

            .max()

        )



        risk = stop - entry




        if risk <= 0:


            stop = entry * 1.01


            risk = stop - entry




        target = (

            entry

            -

            risk * 2

        )








    return {


        "pair":

            symbol,



        "exchange":

            "OKX",



        "timeframe":

            timeframe,



        "direction":

            direction,



        "confidence":

            int(score),



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
