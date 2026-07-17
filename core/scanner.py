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



# ============================================================
# HTF TREND
# ============================================================


def get_higher_trend(symbol):


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



        return ema200_trend(

            candles

        )



    except Exception as e:


        print(

            "HTF error",

            symbol,

            e

        )


        return None







# ============================================================
# SCAN MARKET
# ============================================================


def scan_market(timeframe):


    signals = []



    print(

        f"Scanning {timeframe}"

    )



    try:


        symbols = okx.get_top_symbols()



    except Exception as e:


        print(

            "Symbol loading error",

            e

        )


        return []





    if not symbols:


        return []





    print(

        "Symbols:",

        len(symbols)

    )





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






            # ==========================
            # HTF
            # ==========================


            higher_trend = None



            if (

                USE_HTF_FILTER

                and

                timeframe != HTF_TIMEFRAME

            ):


                higher_trend = get_higher_trend(

                    symbol

                )






            # ==========================
            # CONDITIONS
            # ==========================


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






            # ==========================
            # FILTER
            # ==========================


            passed, filter_score = quality_check(

                candles,

                direction,

                higher_trend

            )



            if not passed:

                continue







            # ==========================
            # FINAL SCORE
            # ==========================


            base_score = signal_score(

                candles,

                direction

            )



            final_score = round(

                base_score * 0.6

                +

                filter_score * 0.4

            )




            if final_score < MIN_SIGNAL_SCORE:

                continue






            signals.append(

                create_signal(

                    symbol,

                    candles,

                    direction,

                    final_score,

                    timeframe

                )

            )




        except Exception as e:


            print(

                "Scan error",

                symbol,

                e

            )


            continue





    # лучшие сверху


    signals.sort(

        key=lambda x:

        x["confidence"],

        reverse=True

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



        target = entry + risk * 2



    else:


        stop = float(

            df["high"]

            .tail(10)

            .max()

        )


        risk = stop - entry



        target = entry - risk * 2







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
