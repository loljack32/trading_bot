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
# OKX SETTINGS
# =====================================


TIMEFRAMES = [

    "15m",

    "1H",

    "4H"

]



# список монет для анализа

SYMBOLS = [

    "BTC-USDT",

    "ETH-USDT",

    "SOL-USDT",

    "XRP-USDT",

    "DOGE-USDT",

    "AVAX-USDT",

    "LINK-USDT",

    "ADA-USDT",

    "DOT-USDT"

]



# количество свечей

CANDLE_LIMIT = 200





# =====================================
# STRATEGY SETTINGS
# =====================================


# сколько свечей назад искать структуру

SWING_LOOKBACK = 5



# минимальный размер хвоста свечи

MIN_WICK_PERCENT = 0.25



# фильтр объёма

VOLUME_MULTIPLIER = 1.2



# ATR период

ATR_PERIOD = 14



# минимальный рейтинг сигнала

MIN_SIGNAL_SCORE = 68



# риск/прибыль

RR_RATIO = 2




# =====================================
# DATABASE
# =====================================


HISTORY_FILE = (

    "data/history.json"

)



# =====================================
# TELEGRAM CHECK
# =====================================

if not TELEGRAM_TOKEN:
    print("WARNING: TELEGRAM_TOKEN is empty")


if not TELEGRAM_CHAT_ID:
    print("WARNING: TELEGRAM_CHAT_ID is empty")
