import requests

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID
)



class TelegramBot:


    def __init__(self):

        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID



    def send_message(self, text):


        if not self.token or not self.chat_id:

            print(
                "Telegram config missing"
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


            return response.status_code == 200



        except Exception as e:


            print(
                "Telegram error:",
                e
            )


            return False




    def send_signal(self, signal):


        direction = signal["direction"]



        if direction == "LONG":

            emoji = "🟢"

        else:

            emoji = "🔴"





        message = f"""

🔥 <b>SFP + MSS SIGNAL</b>


{emoji} <b>{direction}</b>


<b>PAIR:</b>
{signal['pair']}


<b>NETWORK:</b>
{signal['network']}


<b>CONFIDENCE:</b>
{signal.get('confidence', 0)}%



<b>ENTRY:</b>
<code>{signal['entry']}</code>


<b>STOP LOSS:</b>
<code>{signal['stop']}</code>


<b>TAKE PROFIT:</b>
<code>{signal['target']}</code>



<b>LIQUIDITY:</b>
${signal['liquidity']}



<b>VOLUME 24H:</b>
${signal.get('volume', 0)}



<b>STRATEGY:</b>
SFP + MSS


"""


        return self.send_message(
            message
        )
