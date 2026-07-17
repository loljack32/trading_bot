import requests
import time


BASE_URL = "https://api.geckoterminal.com/api/v2"



class MarketScanner:


    def __init__(self):

        self.headers = {
            "accept": "application/json"
        }

        self.cache = {}




    def get_top_pools(
            self,
            network="solana",
            limit=100
    ):


        cache_key = network



        # используем кэш
        if cache_key in self.cache:

            return self.cache[cache_key][:limit]



        url = (
            f"{BASE_URL}/networks/"
            f"{network}/pools"
        )



        params = {
            "page": 1
        }




        for attempt in range(3):


            try:


                response = requests.get(

                    url,

                    headers=self.headers,

                    params=params,

                    timeout=15

                )



                if response.status_code == 429:


                    wait = 10 * (attempt + 1)

                    print(
                        f"Rate limit. Waiting {wait}s"
                    )

                    time.sleep(wait)

                    continue



                if response.status_code != 200:


                    print(

                        "Gecko pools error:",

                        response.status_code

                    )


                    return []



                data = response.json()



                pools = []



                for item in data.get(
                    "data",
                    []
                ):


                    attr = item.get(
                        "attributes",
                        {}
                    )



                    address = attr.get(
                        "address"
                    )


                    if not address:

                        continue



                    liquidity = self.safe_float(

                        attr.get(
                            "reserve_in_usd"
                        )

                    )



                    volume = self.safe_float(

                        attr.get(
                            "volume_usd"
                        )

                    )



                    pools.append(

                        {

                        "name":
                            attr.get(
                                "name",
                                "UNKNOWN"
                            ),


                        "network":
                            network,


                        "pool":
                            address,


                        "liquidity":
                            liquidity,


                        "volume":
                            volume

                        }

                    )



                pools.sort(

                    key=lambda x:
                    x["liquidity"],

                    reverse=True

                )



                self.cache[network] = pools



                return pools[:limit]



            except Exception as e:


                print(
                    "Market error:",
                    e
                )


                time.sleep(5)



        return []





    def safe_float(
            self,
            value
    ):


        try:

            return float(
                value or 0
            )

        except:

            return 0
