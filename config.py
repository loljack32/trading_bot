import os


# =====================================
# TELEGRAM
# =====================================

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN",
    ""
)

TELEGRAM_CHAT_ID = os.getenv(
    "CHAT_ID",
    ""
)



# =====================================
# NETWORKS
# =====================================

NETWORKS = [

    "solana"

]



# =====================================
# TIMEFRAMES
# =====================================

TIMEFRAMES = [

    "minute_5",
    "minute_15",
    "hour"

]



# =====================================
# MARKET FILTERS
# =====================================


# минимальная ликвидность пула

MIN_LIQUIDITY = 50000



# минимальный объём

MIN_VOLUME = 100000




# =====================================
# STRATEGY
# =====================================


SWING_LOOKBACK = 5



MIN_WICK_PERCENT = 0.3



VOLUME_MULTIPLIER = 1.5



RR_RATIO = 2




# =====================================
# SIGNAL FILTER
# =====================================


MIN_SIGNAL_SCORE = 70




# =====================================
# DATABASE
# =====================================


HISTORY_FILE = "data/history.json"
