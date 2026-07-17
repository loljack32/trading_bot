import os
import json

from datetime import datetime


# =====================================
# DEBUG IMPORT CHECK
# =====================================

print("======================")
print("INDICATORS CHECK")
print("======================")


try:

    import core.indicators as indicators


    print("Indicators loaded:")
    print(indicators.__file__)


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


from config import (
    HISTORY_FILE
)


from core.scanner import scan_market


from notifications.telegram import TelegramBot




# =====================================
# TELEGRAM
# =====================================


telegram = TelegramBot()




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
# DUPLICATE CHECK
# =====================================


def is_new_signal(signal, history):


    for old in history:


        same_pair = (
            old.get("pair")
            ==
            signal.get("pair")
        )


        same_direction = (
            old.get("direction")
            ==
            signal.get("direction")
        )


        same_timeframe = (
            old.get("timeframe")
            ==
            signal.get("timeframe")
        )



        if (
            same_pair
            and
            same_direction
            and
            same_timeframe
        ):

            return False



    return True





# =====================================
# ADD HISTORY
# =====================================


def add_history(signal, history):


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
    print(" SFP MSS BOT START ")
    print("======================")


    history = load_history()



    # приоритет анализа

    priority_timeframes = [

        "4H",

        "1H",

        "15m"

    ]



    selected_signals = []

    selected_tf = None



    # =====================================
    # SEARCH BEST TIMEFRAME
    # =====================================


    for timeframe in priority_timeframes:


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



        if signals:


            print(
                "Signals found:",
                timeframe
            )


            selected_signals = signals

            selected_tf = timeframe


            break



        else:


            print(
                "No signals"
            )




    # =====================================
    # NO SIGNALS
    # =====================================


    if not selected_signals:


        print(
            "No signals anywhere"
        )


        save_history(history)


        print(
            "SCAN COMPLETE"
        )

        return





    # =====================================
    # SEND SIGNALS
    # =====================================


    for signal in selected_signals:



        signal["timeframe"] = selected_tf



        print(
            "FOUND:",
            signal
        )



        if is_new_signal(
            signal,
            history
        ):



            sent = telegram.send_signal(
                signal
            )


            if sent:

                print(
                    "Telegram sent"
                )



            history = add_history(
                signal,
                history
            )



        else:


            print(
                "Duplicate signal"
            )





    save_history(
        history
    )



    print()

    print(
        "SCAN COMPLETE"
    )





if __name__ == "__main__":

    main()
