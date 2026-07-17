import requests

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID
)



# =====================================
# Telegram отправка сообщений
# =====================================


class TelegramBot:



    def __init__(self):

        self.token = TELEGRAM_TOKEN

        self.chat_id = TELEGRAM_CHAT_ID



    # =================================
    # Отправка сообщения
    # =================================


    def send_message(
            self,
            text
    ):


        if not self.token or not self.chat_id:

            print(
                "Telegram credentials missing"
            )

            return False



        url = (

            f"https://api.telegram.org/"
            f"bot{self.token}/sendMessage"

        )



        payload = {


            "chat_id":
                self.chat_id,


            "text":
                text,


            "parse_mode":
                "HTML"

        }



        try:


            response = requests.post(

                url,

                json=payload,

                timeout=10

            )



            if response.status_code == 200:

                return True



            print(

                "Telegram error:",
                response.text

            )



            return False



        except Exception as e:


            print(
                "Telegram exception:",
                e
            )


            return False




    # =================================
    # Форматирование сигнала
    # =================================


    def send_signal(
            self,
            signal
    ):



        if signal["direction"] == "LONG":

            emoji = "🟢"

        else:

            emoji = "🔴"




        message = f"""

🔥 <b>SFP + MSS SIGNAL</b>


{emoji} <b>{signal['direction']}</b>


<b>PAIR:</b>
{signal['pair']}


<b>NETWORK:</b>
{signal['network']}


<b>ENTRY:</b>
<code>{signal['entry']}</code>


<b>STOP:</b>
<code>{signal['stop']}</code>


<b>TARGET:</b>
<code>{signal['target']}</code>


<b>LIQUIDITY:</b>
${signal['liquidity']}


<b>VOLUME:</b>
${signal.get('volume', 0)}


<b>STRATEGY:</b>
SFP + MSS


"""


        return self.send_message(
            message
        )
