import requests
import pandas as pd
import time


BASE_URL = "https://www.okx.com"



class OKXClient:


    def __init__(self):

        self.headers = {

            "Accept":
            "application/json"

        }




    # =====================================
    # OHLCV
    # =====================================


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
                limit

        }




        for attempt in range(3):


            try:


                response = requests.get(

                    url,

                    headers=self.headers,

                    params=params,

                    timeout=15

                )



                if response.status_code != 200:


                    print(
                        "OKX HTTP ERROR:",
                        response.status_code
                    )


                    time.sleep(2)

                    continue




                data = response.json()



                if data.get("code") != "0":


                    print(
                        "OKX API ERROR:",
                        data
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

                    df["timestamp"],

                    unit="ms"

                )






                # старая -> новая

                df = df.sort_values(

                    "timestamp"

                )



                df = df.reset_index(

                    drop=True

                )






                # убираем текущую незакрытую свечу

                if len(df) > 1:

                    df = df.iloc[:-1]





                return df





            except Exception as e:


                print(

                    "OKX ERROR:",

                    e

                )


                time.sleep(2)





        return None






    # =====================================
    # Ticker
    # =====================================


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
