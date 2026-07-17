import json
import os
from datetime import datetime

from config import (
    TIMEFRAMES,
    HISTORY_FILE
)

from core.scanner import scan_market

from notifications.telegram import TelegramBot



telegram = TelegramBot()



# =====================================
# Работа с историей сигналов
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
        ) as file:

            return json.load(file)



    except Exception:


        return []





def save_history(history):


    os.makedirs(

        os.path.dirname(
            HISTORY_FILE
        ),

        exist_ok=True

    )


    with open(

        HISTORY_FILE,

        "w",

        encoding="utf-8"

    ) as file:


        json.dump(

            history,

            file,

            indent=4,

            ensure_ascii=False

        )





# =====================================
# Проверка дубликатов
# =====================================


def is_new_signal(
        signal,
        history
):


    for old in history:


        if (

            old["pair"] ==
            signal["pair"]

            and

            old["direction"] ==
            signal["direction"]

            and

            old["entry"] ==
            signal["entry"]

        ):


            return False



    return True





# =====================================
# Добавление истории
# =====================================


def add_history(
        signal,
        history
):


    signal_copy = signal.copy()


    signal_copy["time"] = (

        datetime.utcnow()
        .isoformat()

    )


    history.append(
        signal_copy
    )



    # храним последние 500

    history = history[-500:]



    return history





# =====================================
# Основной запуск
# =====================================


def main():


    print(
        "======================"
    )

    print(
        " SFP + MSS BOT START "
    )

    print(
        "======================"
    )



    history = load_history()



    for timeframe in TIMEFRAMES:



        print(

            f"Scanning {timeframe}"

        )



        signals = scan_market(
            timeframe
        )



        if not signals:


            print(
                "No signals"
            )


            continue




        for signal in signals:



            if is_new_signal(

                signal,

                history

            ):


                print(
                    "NEW SIGNAL:",
                    signal
                )



                telegram.send_signal(
                    signal
                )



                history = add_history(

                    signal,

                    history

                )



            else:


                print(
                    "Duplicate signal skipped"
                )




    save_history(
        history
    )



    print(
        "SCAN COMPLETE"
    )





if __name__ == "__main__":

    main()
