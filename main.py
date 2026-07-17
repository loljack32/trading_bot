import json
import os

from datetime import datetime


# DEBUG ПРОВЕРКА IMPORT
import core.indicators


print("======================")
print("INDICATORS DEBUG")
print("======================")

print(
    "Indicators file:",
    core.indicators.__file__
)

print(
    "volume_confirmation exists:",
    hasattr(
        core.indicators,
        "volume_confirmation"
    )
)

print("======================")



from config import (
    TIMEFRAMES,
    HISTORY_FILE
)


from core.scanner import scan_market


from notifications.telegram import TelegramBot



telegram = TelegramBot()





# =====================================
# Загрузка истории
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



    except Exception as e:


        print(
            "History load error:",
            e
        )


        return []







# =====================================
# Сохранение истории
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

    ) as file:



        json.dump(

            history,

            file,

            indent=4,

            ensure_ascii=False

        )







# =====================================
# Проверка дублей
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
# Добавление истории
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


    # максимум 500 сигналов

    return history[-500:]








# =====================================
# Основной запуск
# =====================================


def main():


    print()

    print("======================")

    print(" SFP MSS BOT START ")

    print("======================")


    history = load_history()



    for timeframe in TIMEFRAMES:


        print()

        print(
            "Scanning:",
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





        for signal in signals:



            print(
                "Signal found:",
                signal
            )



            if is_new_signal(

                signal,

                history

            ):



                print(
                    "NEW SIGNAL"
                )



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
                    "Duplicate skipped"
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
