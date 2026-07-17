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


from config import (
    TIMEFRAMES,
    HISTORY_FILE,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID
)


from core.scanner import scan_market


from notifications.telegram import TelegramBot



# =====================================
# TELEGRAM INIT
# =====================================


telegram = TelegramBot()



# =====================================
# LOAD HISTORY
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







# =====================================
# SAVE HISTORY
# =====================================


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
# CHECK DUPLICATE
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

            old.get("entry")
            ==
            signal.get("entry")

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


    # приоритет таймфреймов
    priority_timeframes = [

        "4H",

        "1H",

        "15m"

    ]


    selected_signals = []



    # =====================================
    # SCAN WITH PRIORITY
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
                f"Signals found on {timeframe}"
            )


            selected_signals = signals


            break



        else:


            print(
                "No signals"
            )



    # =====================================
    # SEND ONLY BEST TIMEFRAME
    # =====================================


    if not selected_signals:


        print(
            "No signals anywhere"
        )


    else:


        for signal in selected_signals:


            print(
                "FOUND:",
                signal
            )



            if is_new_signal(

                signal,

                history

            ):


                try:


                    telegram.send_signal(
                        signal
                    )


                except Exception as e:


                    print(
                        "Telegram error:",
                        e
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
