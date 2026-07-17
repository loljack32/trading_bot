from core.gecko import GeckoTerminal



gecko = GeckoTerminal()



# пример Solana пула

data = gecko.get_pool_data(
    "solana",
    "POOL_ADDRESS"
)



print(data)
