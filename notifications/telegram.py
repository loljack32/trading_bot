# ============================================================
# notifications/telegram.py
# Telegram notifier
# ============================================================

import requests


class TelegramBot:


    def __init__(self, config):

        self.config = config

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



    # --------------------------------------------------------

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
                "Telegram timeout"
            )

            return False



        except requests.exceptions.ConnectionError:


            print(
                "Telegram network error"
            )

            return False



        except Exception as e:


            print(
                "Telegram error:",
                e
            )

            return False



    # --------------------------------------------------------

    def send_signal(self, signal):


        text = f"""

<b>SFP MSS SIGNAL</b>


Pair: {signal['pair']}

Direction: {signal['direction']}

Confidence: {signal['confidence']}%


Entry: {signal['entry']}

Stop: {signal['stop']}

Target: {signal['target']}


Volume: {signal['volume']}

"""


        return self.send(
            text.strip()
        )
