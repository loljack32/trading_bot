import requests
import pandas as pd


BASE_URL = "https://api.geckoterminal.com/api/v2"



class GeckoTerminal:


    def __init__(self):

        self.headers = {

            "accept":
            "application/json"

        }





    def get_ohlcv(

            self,

            network,

            pool_address,

            timeframe="15m",

            limit=200

    ):


        timeframe_map = {

            "minute_5": "minute",

            "minute_15": "minute",

            "hour": "hour"

        }



        aggregate_map = {

            "minute_5": 5,

            "minute_15": 15,

            "hour": 1

        }



        timeframe_type = timeframe_map.get(

            timeframe,

            "minute"

        )



        aggregate = aggregate_map.get(

            timeframe,

            15

        )



        url = (

            f"{BASE_URL}/networks/"
            f"{network}/pools/"
            f"{pool_address}/ohlcv/"
            f"{timeframe_type}"

        )



        params = {

            "aggregate":
            aggregate,


            "limit":
            limit

        }



        try:


            response = requests.get(

                url,

                headers=self.headers,

                params=params,

                timeout=15

            )



            if response.status_code != 200:


                print(

                    "OHLCV API ERROR:",

                    response.status_code,

                    response.text[:200]

                )


                return None




            data = response.json()



            candles = (

                data
                .get("data", {})
                .get("attributes", {})
                .get("ohlcv_list", [])

            )



            if not candles:


                return None




            df = pd.DataFrame(

                candles,

                columns=[

                    "timestamp",

                    "open",

                    "high",

                    "low",

                    "close",

                    "volume"

                ]

            )



            for col in [

                "open",

                "high",

                "low",

                "close",

                "volume"

            ]:


                df[col] = pd.to_numeric(

                    df[col],

                    errors="coerce"

                )



            df = df.dropna()



            df = df.sort_values(

                "timestamp"

            )



            df.reset_index(

                drop=True,

                inplace=True

            )



            return df



        except Exception as e:


            print(

                "OHLCV ERROR:",

                e

            )


            return None





    def get_pool_data(

            self,

            network,

            pool_address

    ):



        url = (

            f"{BASE_URL}/networks/"
            f"{network}/pools/"
            f"{pool_address}"

        )



        try:


            response = requests.get(

                url,

                headers=self.headers,

                timeout=15

            )



            if response.status_code != 200:

                return None



            data = response.json()



            attr = (

                data
                .get("data", {})
                .get("attributes", {})

            )



            return {

                "name":

                    attr.get(
                        "name"
                    ),


                "liquidity":

                    float(

                        attr.get(

                            "reserve_in_usd",

                            0

                        )

                    )

            }



        except Exception as e:


            print(

                "POOL ERROR:",

                e

            )


            return None
