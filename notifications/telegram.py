# ============================================================
# notifications/telegram.py
# Telegram notifier
# ============================================================

import requests

import config



class TelegramBot:


    def __init__(self):


        self.token = getattr(
            config,
            "TELEGRAM_TOKEN",
            None
        )


        self.chat_id = getattr(
            config,
            "TELEGRAM_CHAT_ID",
            None
        )



    # ========================================================
    # Отправка сообщения
    # ========================================================

    def send(self, message):


        if not self.token:

            print(
                "Telegram disabled: token missing"
            )

            return False



        if not self.chat_id:

            print(
                "Telegram disabled: chat id missing"
            )

            return False



        url = (
            f"https://api.telegram.org/"
            f"bot{self.token}/sendMessage"
        )



        payload = {

            "chat_id": self.chat_id,

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
                "Telegram error: network"
            )

            return False



        except Exception as e:


            print(
                "Telegram error:",
                e
            )

            return False




    # ========================================================
    # Сигнал
    # ========================================================

    def send_signal(self, signal):


        message = f"""

<b>⚡ SFP MSS SIGNAL</b>


<b>Pair:</b> {signal['pair']}

<b>Direction:</b> {signal['direction']}

<b>Confidence:</b> {signal['confidence']}%


<b>Entry:</b> {signal['entry']}

<b>Stop:</b> {signal['stop']}

<b>Target:</b> {signal['target']}


<b>Volume:</b> {signal['volume']}

"""


        return self.send(
            message.strip()
        )
