# ============================================================
# core/okx.py
# OKX API CLIENT
# TOP100 SWAP VOLUME + VALIDATION
# ============================================================


import requests
import pandas as pd
import time


from config import (
    TOP_SYMBOLS_LIMIT,
    QUOTE_CURRENCY,
    REQUEST_DELAY
)



BASE_URL = "https://www.okx.com"





class OKXClient:



    def __init__(self):


        self.headers = {

            "Accept":
            "application/json"

        }





    # ========================================================
    # GET TOP SYMBOLS BY VOLUME
    # ========================================================


    def get_top_symbols(self):


        url = (

            f"{BASE_URL}/api/v5/market/tickers"

        )


        params = {


            "instType":

            "SWAP"

        }



        try:


            response = requests.get(

                url,

                headers=self.headers,

                params=params,

                timeout=15

            )



            data = response.json()



            if data.get("code") != "0":


                print(

                    "OKX ticker error:",

                    data

                )


                return []





            markets = []



            for item in data.get(
                "data",
                []
            ):



                symbol = item.get(
                    "instId"
                )



                if not symbol:

                    continue




                # только USDT perpetual

                if not symbol.endswith(

                    f"-{QUOTE_CURRENCY}-SWAP"

                ):

                    continue




                # пропускаем неактивные

                state = item.get("state", "live")

if state != "live":
    continue




                volume = float(

                    item.get(

                        "volCcy24h",

                        0

                    )

                )



                if volume <= 0:

                    continue





                markets.append(

                    (

                        symbol,

                        volume

                    )

                )





            markets.sort(

                key=lambda x:x[1],

                reverse=True

            )





            symbols = [

                x[0]

                for x in markets[

                    :TOP_SYMBOLS_LIMIT

                ]

            ]





            print(

                "Loaded symbols:",

                len(symbols)

            )



            return symbols





        except Exception as e:


            print(

                "Symbol loading error:",

                e

            )


            return []








    # ========================================================
    # OHLCV
    # ========================================================


    def get_ohlcv(

            self,

            symbol,

            timeframe="15m",

            limit=200

    ):



        url = (

            f"{BASE_URL}/api/v5/market/candles"

        )



        params = {


            "instId":

            symbol,


            "bar":

            timeframe,


            "limit":

            limit + 1

        }



        for attempt in range(3):


            try:



                response = requests.get(

                    url,

                    headers=self.headers,

                    params=params,

                    timeout=15

                )



                data = response.json()




                if data.get("code") != "0":


                    print(

                        "OKX candle error:",

                        symbol,

                        data.get("msg")

                    )


                    return None





                candles = data.get(

                    "data",

                    []

                )



                if not candles:


                    return None





                rows = []



                for candle in candles:



                    rows.append(

                        [

                            candle[0],

                            candle[1],

                            candle[2],

                            candle[3],

                            candle[4],

                            candle[5]

                        ]

                    )





                df = pd.DataFrame(

                    rows,

                    columns=[

                        "timestamp",

                        "open",

                        "high",

                        "low",

                        "close",

                        "volume"

                    ]

                )






                numeric = [

                    "open",

                    "high",

                    "low",

                    "close",

                    "volume"

                ]





                for col in numeric:


                    df[col] = pd.to_numeric(

                        df[col],

                        errors="coerce"

                    )





                df["timestamp"] = pd.to_datetime(

                    pd.to_numeric(

                        df["timestamp"]

                    ),

                    unit="ms"

                )





                df = df.sort_values(

                    "timestamp"

                )



                df = df.reset_index(

                    drop=True

                )






                # удаляем незакрытую свечу

                if len(df) > 1:

                    df = df.iloc[:-1]





                time.sleep(

                    REQUEST_DELAY

                )



                return df





            except Exception as e:



                print(

                    "OHLCV error:",

                    e

                )



                time.sleep(2)





        return None








    # ========================================================
    # TICKER
    # ========================================================


    def get_ticker(

            self,

            symbol

    ):



        url = (

            f"{BASE_URL}/api/v5/market/ticker"

        )



        params = {


            "instId":

            symbol

        }



        try:


            response = requests.get(

                url,

                params=params,

                timeout=10

            )



            data = response.json()



            if data.get("code") != "0":

                return None



            return data["data"][0]





        except Exception as e:


            print(

                "Ticker error:",

                e

            )


            return None
