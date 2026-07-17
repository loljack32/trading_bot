# ============================================================
# core/telegram.py
# Надежная отправка сигналов в Telegram
# ============================================================

import requests

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)



# ============================================================
# Отправка сообщения
# ============================================================

def send_telegram(message: str):

    if not TELEGRAM_BOT_TOKEN:
        print("Telegram disabled: no token")
        return False


    if not TELEGRAM_CHAT_ID:
        print("Telegram disabled: no chat id")
        return False



    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )



    payload = {

        "chat_id": TELEGRAM_CHAT_ID,

        "text": message,

        "parse_mode": "HTML"

    }



    try:

        response = requests.post(

            url,

            json=payload,

            timeout=10

        )



        data = response.json()



        if not data.get("ok"):

            print(
                "Telegram API error:",
                data
            )

            return False



        return True



    except requests.exceptions.Timeout:

        print(
            "Telegram error: timeout"
        )

        return False



    except requests.exceptions.ConnectionError:

        print(
            "Telegram error: network connection"
        )

        return False



    except Exception as e:

        print(
            "Telegram error:",
            str(e)
        )

        return False





# ============================================================
# Форматирование торгового сигнала
# ============================================================

def format_signal(signal):


    direction_icon = (
        "🟢"
        if signal["direction"] == "LONG"
        else
        "🔴"
    )



    text = f"""

{direction_icon} <b>SFP MSS SIGNAL</b>


<b>Pair:</b> {signal['pair']}

<b>Exchange:</b> {signal['exchange']}

<b>Direction:</b> {signal['direction']}

<b>Confidence:</b> {signal['confidence']}%


<b>Entry:</b> {signal['entry']}

<b>Stop:</b> {signal['stop']}

<b>Target:</b> {signal['target']}


<b>Volume:</b> {signal['volume']}


⚡ Risk / Reward: 1:2

"""

    return text.strip()





# ============================================================
# Отправка торгового сигнала
# ============================================================

def send_signal(signal):


    message = format_signal(signal)


    return send_telegram(
        message
    )
