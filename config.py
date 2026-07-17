import os
from dataclasses import dataclass
from typing import Optional


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID", "")

TIMEFRAMES = ["15m", "1H", "4H"]
HTF_TIMEFRAME = "4H"
USE_HTF_FILTER = True

QUOTE_CURRENCY = "USDT"
TOP_SYMBOLS_LIMIT = 100
CANDLE_LIMIT = 200
REQUEST_DELAY = 0.15

SWING_LOOKBACK = 5
MIN_WICK_PERCENT = 0.25
VOLUME_MULTIPLIER = 1.2
ATR_PERIOD = 14
EMA_PERIOD = 200
RSI_PERIOD = 14
MIN_SIGNAL_SCORE = 70
RR_RATIO = 2.0
ATR_STOP_MULTIPLIER = 1.5
STOP_LOOKBACK = 10
MAX_SIGNALS_PER_SCAN = 10

MIN_RISK_PCT = 0.003
MIN_RR = 2.0
MIN_VOLUME_RATIO = 1.2
MIN_ATR_RATIO = 0.0015
MIN_CANDLE_STRENGTH = 0.75

HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
BALANCE_FILE = os.path.join(DATA_DIR, "balance_requests.json")
POSITION_STATE_FILE = os.path.join(DATA_DIR, "position_state.json")
WORKER_URL = os.getenv("WORKER_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


@dataclass(frozen=True)
class AppConfig:
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    timeframes: tuple[str, ...] = ("15m", "1H", "4H")
    htf_timeframe: str = "4H"
    quote_currency: str = "USDT"
    top_symbols_limit: int = 100
    candle_limit: int = 200
    request_delay: float = 0.15
    min_signal_score: int = 85
    min_rr: float = 2.0
    min_risk_pct: float = 0.003
    min_volume_ratio: float = 1.2
    min_atr_ratio: float = 0.0015
    min_candle_strength: float = 0.75


APP_CONFIG = AppConfig(
    telegram_token=TELEGRAM_TOKEN or None,
    telegram_chat_id=TELEGRAM_CHAT_ID or None,
    timeframes=tuple(TIMEFRAMES),
    htf_timeframe=HTF_TIMEFRAME,
    quote_currency=QUOTE_CURRENCY,
    top_symbols_limit=TOP_SYMBOLS_LIMIT,
    candle_limit=CANDLE_LIMIT,
    request_delay=REQUEST_DELAY,
    min_signal_score=MIN_SIGNAL_SCORE,
    min_rr=RR_RATIO,
    min_risk_pct=MIN_RISK_PCT,
    min_volume_ratio=VOLUME_MULTIPLIER,
    min_atr_ratio=MIN_ATR_RATIO,
    min_candle_strength=MIN_CANDLE_STRENGTH,
)
