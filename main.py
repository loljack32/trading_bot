import os
import json

from datetime import datetime



# =====================================
# DEBUG
# =====================================


print("======================")
print("INDICATORS CHECK")
print("======================")


try:

    import core.indicators as indicators


    print(
        "Indicators loaded:"
    )


    print(
        indicators.__file__
    )


    print(
        "volume_confirmation:",
        hasattr(
            indicators,
            "volume_confirmation"
        )
    )


except Exception as e:


    print(
        "Indicators import error:",
        e
    )

    raise



print("======================")





# =====================================
# IMPORTS
# =====================================


from config import HISTORY_FILE


from core.scanner import scan_market


from notifications.telegram import TelegramBot






telegram = TelegramBot()





# максимум сигналов за один запуск

MAX_SIGNALS_PER_SCAN = 10







# =====================================
# HISTORY
# =====================================


def load_history():


    if not os.path.exists(
        HISTORY_FILE
    ):

        return []



    try:


        with open(

            HISTORY_FILE,

            "r",

            encoding="utf-8"

        ) as f:


            return json.load(f)



    except Exception as e:


        print(
            "History read error:",
            e
        )


        return []







def save_history(history):


    folder = os.path.dirname(
        HISTORY_FILE
    )


    if folder:


        os.makedirs(

            folder,

            exist_ok=True

        )



    with open(

        HISTORY_FILE,

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            history,

            f,

            indent=4,

            ensure_ascii=False

        )








# =====================================
# DUPLICATE
# =====================================


def is_new_signal(

        signal,

        history

):


    for old in history:



        if (

            old.get("pair")
            ==
            signal.get("pair")

            and

            old.get("direction")
            ==
            signal.get("direction")

            and

            old.get("timeframe")
            ==
            signal.get("timeframe")

        ):


            return False



    return True







# =====================================
# ADD HISTORY
# =====================================


def add_history(

        signal,

        history

):


    item = signal.copy()



    item["time"] = (

        datetime.utcnow()

        .isoformat()

    )



    history.append(

        item

    )



    return history[-500:]









# =====================================
# MAIN
# =====================================


def main():



    print()

    print("======================")

    print(
        " SFP MSS BOT START "
    )

    print("======================")



    history = load_history()





    # рабочий порядок

    timeframes = [

        "15m",

        "1H",

        "4H"

    ]




    sent_count = 0





    for timeframe in timeframes:



        print()

        print(

            "Scanning",

            timeframe

        )



        try:


            signals = scan_market(

                timeframe

            )



        except Exception as e:


            print(

                "Scanner error:",

                e

            )


            continue





        if not signals:


            print(

                "No signals"

            )


            continue





        print(

            "Found:",

            len(signals)

        )





        for signal in signals:



            if sent_count >= MAX_SIGNALS_PER_SCAN:


                break





            signal["timeframe"] = timeframe





            print(

                "FOUND:",

                signal

            )





            if not is_new_signal(

                signal,

                history

            ):


                print(

                    "Duplicate signal"

                )


                continue






            try:


                result = telegram.send_signal(

                    signal

                )



                if result:


                    print(

                        "Telegram sent"

                    )


                    sent_count += 1



            except Exception as e:


                print(

                    "Telegram error:",

                    e

                )






            history = add_history(

                signal,

                history

            )







    save_history(

        history

    )



    print()

    print(

        "SCAN COMPLETE"

    )

    print(

        "Signals sent:",

        sent_count

    )







if __name__ == "__main__":

    main()
