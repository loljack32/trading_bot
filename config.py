import os


# ==========================
# TELEGRAM
# ==========================

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "CHAT_ID"
)


# ==========================
# MARKET SETTINGS
# ==========================

TIMEFRAMES = [
    "5m",
    "15m",
    "1h"
]


# Минимальная ликвидность пула

MIN_LIQUIDITY = 50000


# Объём должен быть выше среднего

VOLUME_MULTIPLIER = 1.5



# ==========================
# STRATEGY SETTINGS
# ==========================


# сколько свечей смотрим назад

SWING_LOOKBACK = 10



# Минимальный размер тени SFP

MIN_WICK_PERCENT = 0.3



# Risk Reward

RR_RATIO = 2



# ==========================
# DATABASE
# ==========================

HISTORY_FILE = "data/history.json"
