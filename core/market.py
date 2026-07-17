import requests


BASE_URL = "https://api.geckoterminal.com/api/v2"



class MarketScanner:


    def __init__(self):

        self.headers = {
            "accept": "application/json"
        }



    # =====================================
    # Получение топовых пулов сети
    # =====================================

    def get_top_pools(
            self,
            network="solana",
            limit=100
    ):


        url = (
            f"{BASE_URL}/networks/"
            f"{network}/pools"
        )


        params = {

            "page": 1

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
                    "Gecko pools error:",
                    response.status_code
                )


                return []



            result = response.json()



            pools = []



            for item in result.get(
                    "data",
                    []
            ):



                attributes = item.get(
                    "attributes",
                    {}
                )



                address = attributes.get(
                    "address"
                )



                if not address:

                    continue



                name = attributes.get(
                    "name",
                    "UNKNOWN"
                )



                liquidity = self.safe_float(

                    attributes.get(
                        "reserve_in_usd"
                    )

                )



                volume = self.safe_float(

                    attributes
                    .get(
                        "volume_usd",
                        0
                    )

                )



                price_change = attributes.get(
                    "price_change_percentage",
                    {}
                )



                pools.append(

                    {


                    "name":
                        name,


                    "network":
                        network,


                    "pool":
                        address,


                    "liquidity":
                        liquidity,


                    "volume":
                        volume,


                    "price_change":
                        price_change


                    }

                )




            # Сначала самые ликвидные

            pools.sort(

                key=lambda x:
                (
                    x["liquidity"],
                    x["volume"]
                ),

                reverse=True

            )



            return pools[:limit]



        except Exception as e:


            print(
                "Market scanner error:",
                e
            )


            return []





    # =====================================
    # Безопасное преобразование чисел
    # =====================================


    def safe_float(
            self,
            value
    ):


        try:

            return float(value or 0)


        except:


            return 0
