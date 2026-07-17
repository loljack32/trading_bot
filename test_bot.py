from core.market import MarketScanner
from core.gecko import GeckoTerminal
from core.indicators import (
    signal_score,
    bullish_sfp,
    bearish_sfp,
    bullish_mss,
    bearish_mss
)

from config import NETWORKS



def main():


    print(
        "======================"
    )

    print(
        "SFP MSS BOT TEST"
    )

    print(
        "======================"
    )



    market = MarketScanner()

    gecko = GeckoTerminal()



    for network in NETWORKS:


        print(
            f"\nNETWORK: {network}"
        )



        pools = market.get_top_pools(

            network,

            5

        )



        if not pools:


            print(
                "No pools received"
            )

            continue



        for pool in pools:


            print(
                "\nPOOL:",
                pool["name"]
            )


            print(
                "Liquidity:",
                pool["liquidity"]
            )


            candles = gecko.get_ohlcv(

                pool["network"],

                pool["pool"],

                "minute_15"

            )



            if candles is None:


                print(
                    "No candles"
                )

                continue



            print(
                "Candles:",
                len(candles)
            )



            long_setup = (

                bullish_sfp(candles)

                and

                bullish_mss(candles)

            )



            short_setup = (

                bearish_sfp(candles)

                and

                bearish_mss(candles)

            )



            if long_setup:


                score = signal_score(

                    candles,

                    "LONG"

                )


                print(
                    "LONG SIGNAL",
                    score
                )



            elif short_setup:


                score = signal_score(

                    candles,

                    "SHORT"

                )


                print(
                    "SHORT SIGNAL",
                    score
                )



            else:


                print(
                    "No setup"
                )




if __name__ == "__main__":

    main()
