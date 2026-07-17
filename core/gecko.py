import requests
import pandas as pd
import time


BASE_URL = "https://api.geckoterminal.com/api/v2"



class GeckoTerminal:


    def __init__(self):

        self.headers = {
            "accept": "application/json"
        }



    # ==================================
    # Получение OHLCV свечей
    # ==================================

    def get_ohlcv(
        self,
        network,
        pool_address,
        timeframe="minute_15",
        limit=100
    ):


        url = (
            f"{BASE_URL}/networks/"
            f"{network}/pools/"
            f"{pool_address}/ohlcv/{timeframe}"
        )


        params = {

            "limit": limit

        }


        try:


            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )


            if response.status_code != 200:

                print(
                    "Gecko API error:",
                    response.status_code
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


            # приводим типы

            numeric = [
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]


            for col in numeric:

                df[col] = (
                    pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )
                )



            df = df.sort_values(
                "timestamp"
            )



            return df



        except Exception as e:


            print(
                "Gecko OHLCV error:",
                e
            )


            return None



    # ==================================
    # Информация о пуле
    # ==================================


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
                timeout=10
            )



            if response.status_code != 200:

                return None



            data = response.json()



            attributes = (
                data
                .get("data", {})
                .get("attributes", {})
            )



            return {

                "name":
                    attributes.get(
                        "name"
                    ),


                "liquidity":
                    float(
                        attributes
                        .get(
                            "reserve_in_usd",
                            0
                        )
                    ),


                "volume24h":
                    float(
                        attributes
                        .get(
                            "volume_usd",
                            0
                        )
                    )

            }



        except Exception as e:


            print(
                "Pool error:",
                e
            )


            return None
