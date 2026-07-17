import requests


BASE_URL = "https://api.geckoterminal.com/api/v2"



class MarketScanner:


    def __init__(self):

        self.headers = {
            "accept":
            "application/json"
        }




    # ===================================
    # Получение топовых пулов сети
    # ===================================


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


            "include":
            "base_token,quote_token",


            "page":
            1


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
                    "Pool API error",
                    response.status_code
                )

                return []




            data = response.json()



            pools = []



            for item in data.get(
                    "data",
                    []
            )[:limit]:


                attr = (
                    item
                    .get(
                        "attributes",
                        {}
                    )
                )



                pool_address = (
                    attr
                    .get(
                        "address"
                    )
                )



                name = (
                    attr
                    .get(
                        "name"
                    )
                )



                liquidity = float(

                    attr
                    .get(
                        "reserve_in_usd",
                        0
                    )

                )



                volume = float(

                    attr
                    .get(
                        "volume_usd",
                        0
                    )

                )



                if not pool_address:

                    continue




                pools.append(

                    {

                    "name":
                    name,


                    "network":
                    network,


                    "pool":
                    pool_address,


                    "liquidity":
                    liquidity,


                    "volume":
                    volume

                    }

                )



            return pools




        except Exception as e:


            print(
                "Market scanner error:",
                e
            )


            return []
