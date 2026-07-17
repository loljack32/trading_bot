import time

from config import TIMEFRAMES

from core.scanner import scan_market



def main():


    print("======================")
    print(" SFP + MSS BOT START ")
    print("======================")


    for tf in TIMEFRAMES:


        print(
            f"Scanning timeframe: {tf}"
        )


        signals = scan_market(tf)


        if signals:


            for signal in signals:

                print(signal)


        else:

            print(
                "No signals"
            )



if __name__ == "__main__":

    main()
