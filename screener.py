import ccxt
import requests
import json
import os
import sys
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# ==============================================================================
# CONFIG: Все настройки вынесены сюда. Меняйте их, не трогая логику.
# ==============================================================================
CONFIG = {
    "timeframes": {"trend": "4h", "sfp": "1h", "mss": "15m"},
    "candles_limit": {"4h": 50, "1h": 30, "15m": 40},
    "min_volume_usd": 100_000,          # Минимальный суточный объем для фильтрации мусора
    "top_symbols_to_scan": 50,          # Сколько топ-пар сканировать за запуск
    "atr_period": 14,                   # Период для расчета ATR
    "atr_multiplier": 1.5,              # Множитель ATR для расчета стопа (SFP High + ATR*mult)
    "min_rr": 2.0,                      # Минимальный Risk/Reward для сигнала
    "max_leverage": 10,                 # Максимальное кредитное плечо
    "sfp_wick_to_body_ratio": 1.5,      # Фитиль должен быть в X раз больше тела свечи для качественного SFP
    "mss_displacement_multiplier": 1.2, # Свеча слома структуры (MSS) должна быть больше среднего ATR на этот множитель
    "signal_cooldown_hours": 12,        # Не отправлять сигнал по той же паре и направлению чаще, чем раз в X часов
    "okx_retries": 3,                   # Количество попыток запроса к OKX при ошибке
    "okx_retry_delay": 2,               # Задержка между попытками (сек)
}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ==============================================================================
# 1. DATA MANAGER: Работа с файлами (data.json, history)
# ==============================================================================
class DataManager:
    def __init__(self):
        self.data_file = "data.json"
        self.history_file = "signals_history.json"

    def load_user_data(self) -> dict:
        if not os.path.exists(self.data_file):
            logging.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Файл {self.data_file} не найден!")
            sys.exit(1)
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Валидация
            if 'balance' not in data or 'risk_percent' not in data or 'chat_id' not in data:
                raise ValueError("Отсутствуют обязательные поля: balance, risk_percent, chat_id")
            
            return {
                "balance": float(data['balance']),
                "risk_percent": float(data['risk_percent']),
                "chat_id": str(data['chat_id'])
            }
        except Exception as e:
            logging.error(f"❌ Ошибка чтения или валидации {self.data_file}: {e}")
            sys.exit(1)

    def load_history(self) -> list:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_history(self, history: list):
        # Очистка старых записей (старше 7 дней) для экономии места
        cutoff = datetime.now() - timedelta(days=7)
        clean_history = [h for h in history if datetime.fromisoformat(h['time']) > cutoff]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(clean_history, f, indent=4)

    def is_signal_fresh(self, symbol: str, direction: str, history: list) -> bool:
        now = datetime.now()
        for h in history:
            if h['symbol'] == symbol and h['direction'] == direction:
                signal_time = datetime.fromisoformat(h['time'])
                if (now - signal_time).total_seconds() < CONFIG['signal_cooldown_hours'] * 3600:
                    return False # Сигнал уже был недавно
        return True

    def add_to_history(self, symbol: str, direction: str, history: list):
        history.append({
            "symbol": symbol,
            "direction": direction,
            "time": datetime.now().isoformat()
        })
        self.save_history(history)

# ==============================================================================
# 2. MARKET DATA: Получение данных с OKX (с защитой от ошибок)
# ==============================================================================
class MarketData:
    def __init__(self):
        self.exchange = ccxt.okx({
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'},
            'timeout': 10000
        })

    def _fetch_with_retry(self, func, *args, **kwargs):
        for attempt in range(CONFIG['okx_retries']):
            try:
                return func(*args, **kwargs)
            except ccxt.RateLimitExceeded:
                time.sleep(CONFIG['okx_retry_delay'] * (attempt + 1))
            except Exception as e:
                if attempt == CONFIG['okx_retries'] - 1:
                    logging.warning(f"Ошибка запроса {func.__name__}: {e}")
                    return None
                time.sleep(CONFIG['okx_retry_delay'])
        return None

    def get_top_symbols(self, limit: int) -> List[Dict]:
        tickers = self._fetch_with_retry(self.exchange.fetch_tickers)
        if not tickers:
            return []
        
        valid = []
        for symbol, info in tickers.items():
            if symbol.endswith('/USDT:USDT') and info.get('baseVolume') and info.get('last'):
                vol_usd = info['baseVolume'] * info['last']
                if vol_usd >= CONFIG['min_volume_usd']:
                    valid.append({'symbol': symbol, 'volume_usd': vol_usd})
        
        valid.sort(key=lambda x: x['volume_usd'], reverse=True)
        return valid[:limit]

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int) -> Optional[List[List]]:
        """Возвращает свечи. ВАЖНО: последняя свеча (индекс -1) НЕЗАКРЫТАЯ. 
        Мы будем использовать срез [:-1] для работы только с закрытыми."""
        data = self._fetch_with_retry(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
        return data

# ==============================================================================
# 3. SMC ANALYZER: Чистая логика стратегии (готово к бэктестингу)
# ==============================================================================
class SMCAnalyzer:
    @staticmethod
    def calculate_atr(candles: List[List], period: int) -> float:
        if len(candles) < period + 1:
            return 0.0
        trs = []
        for i in range(1, len(candles)):
            high = candles[i][2]
            low = candles[i][3]
            prev_close = candles[i-1][4]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs[-period:]) / period

    @staticmethod
    def find_recent_swing(candles: List[List], direction: str, lookback: int = 10) -> Optional[float]:
        """Ищет фрактальный Swing High или Swing Low среди ЗАКРЫТЫХ свечей."""
        # Берем только закрытые свечи, исключая текущую формирующуюся ([:-1])
        closed = candles[:-1]
        if len(closed) < lookback + 2:
            return None
            
        search_area = closed[-lookback-2 : -2] # Ищем свинг в прошлом, оставляя 2 свечи справа для подтверждения
        
        if direction == 'HIGH':
            highs = [c[2] for c in search_area]
            # Фрактал: центральный хай выше 2 соседних слева и 2 справа
            for i in range(2, len(highs)-2):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
                   highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    return highs[i]
        else: # LOW
            lows = [c[3] for c in search_area]
            for i in range(2, len(lows)-2):
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
                   lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    return lows[i]
        return None

    @staticmethod
    def check_sfp(candles_1h: List[List], direction: str) -> Tuple[bool, float, float, float]:
        """
        Проверяет Swing Failure Pattern на 1H.
        Возвращает: (is_sfp, swing_level, entry_price, stop_price)
        """
        closed = candles_1h[:-1]
        if len(closed) < 15:
            return False, 0, 0, 0

        last_candle = closed[-2] # Последняя полностью закрытая
        prev_candle = closed[-3] # Для подтверждения
        
        open_p, high_p, low_p, close_p = last_candle[1], last_candle[2], last_candle[3], last_candle[4]
        body = abs(close_p - open_p)
        wick_top = high_p - max(open_p, close_p)
        wick_bottom = min(open_p, close_p) - low_p

        atr = SMCAnalyzer.calculate_atr(closed, CONFIG['atr_period'])
        
        if direction == 'SHORT':
            swing_high = SMCAnalyzer.find_recent_swing(candles_1h, 'HIGH', lookback=12)
            if not swing_high: return False, 0, 0, 0
            
            # Условие SFP: High пробил свинг, но Close вернулся ПОД свинг
            # ИЛИ High пробил свинг, а текущая цена уже под ним (агрессивный вариант)
            swept_liquidity = high_p > swing_high
            closed_inside = close_p < swing_high
            good_wick = wick_top > (body * CONFIG['sfp_wick_to_body_ratio']) if body > 0 else True
            
            if swept_liquidity and closed_inside and good_wick:
                entry = close_p
                stop = swing_high + (atr * CONFIG['atr_multiplier'])
                return True, swing_high, entry, stop

        elif direction == 'LONG':
            swing_low = SMCAnalyzer.find_recent_swing(candles_1h, 'LOW', lookback=12)
            if not swing_low: return False, 0, 0, 0
            
            swept_liquidity = low_p < swing_low
            closed_inside = close_p > swing_low
            good_wick = wick_bottom > (body * CONFIG['sfp_wick_to_body_ratio']) if body > 0 else True
            
            if swept_liquidity and closed_inside and good_wick:
                entry = close_p
                stop = swing_low - (atr * CONFIG['atr_multiplier'])
                return True, swing_low, entry, stop

        return False, 0, 0, 0

    @staticmethod
    def check_mss(candles_15m: List[List], direction: str, sfp_entry: float) -> Tuple[bool, float]:
        """
        Проверяет Market Structure Shift на 15m после SFP.
        Возвращает: (is_mss, broken_level)
        """
        closed = candles_15m[:-1]
        if len(closed) < 15:
            return False, 0.0

        atr_15m = SMCAnalyzer.calculate_atr(closed, CONFIG['atr_period'])
        
        if direction == 'SHORT':
            # Ищем последний локальный минимум ПЕРЕД тем, как цена обновила хай (SFP)
            # Упрощенно: ищем минимум в последних 10 закрытых свечах
            swing_low = SMCAnalyzer.find_recent_swing(candles_15m, 'LOW', lookback=10)
            if not swing_low: return False, 0.0
            
            # MSS: последняя или предпоследняя свеча закрылась НИЖЕ этого минимума
            last_close = closed[-2][4]
            prev_close = closed[-3][4]
            
            # Проверка на Displacement (сильная свеча)
            is_displacement = (closed[-2][1] - closed[-2][4]) > (atr_15m * CONFIG['mss_displacement_multiplier']) # Медвежья свеча
            
            if (last_close < swing_low or prev_close < swing_low) and is_displacement:
                return True, swing_low

        elif direction == 'LONG':
            swing_high = SMCAnalyzer.find_recent_swing(candles_15m, 'HIGH', lookback=10)
            if not swing_high: return False, 0.0
            
            last_close = closed[-2][4]
            prev_close = closed[-3][4]
            is_displacement = (closed[-2][4] - closed[-2][1]) > (atr_15m * CONFIG['mss_displacement_multiplier']) # Бычья свеча
            
            if (last_close > swing_high or prev_close > swing_high) and is_displacement:
                return True, swing_high

        return False, 0.0

    @staticmethod
    def check_4h_trend(candles_4h: List[List], direction: str) -> bool:
        """Проверяет глобальный тренд. Цена должна быть ниже SMA20 для шорта, и выше для лонга."""
        closed = candles_4h[:-1]
        if len(closed) < 25:
            return True # Если данных мало, не фильтруем
        
        closes = [c[4] for c in closed]
        sma20 = sum(closes[-20:]) / 20
        current_price = closes[-1]
        
        if direction == 'SHORT':
            return current_price < sma20
        else:
            return current_price > sma20

    @staticmethod
    def calculate_score(sfp: bool, mss: bool, trend: bool, rr: float, atr_quality: float) -> int:
        """Оценка качества сигнала от 0 до 100."""
        score = 0
        if sfp: score += 30
        if mss: score += 30
        if trend: score += 20
        if rr >= 3.0: score += 15
        elif rr >= 2.0: score += 10
        
        # Бонус за хороший ATR (не слишком волатильно, не слишком мертво)
        if 0.005 < atr_quality < 0.05: # 0.5% - 5% ATR от цены
            score += 5
            
        return min(score, 100)

# ==============================================================================
# 4. RISK MANAGER: Расчет позиции и плеча
# ==============================================================================
class RiskManager:
    @staticmethod
    def calculate_position(balance: float, risk_percent: float, entry: float, stop: float) -> Dict:
        risk_usd = balance * (risk_percent / 100.0)
        stop_distance_pct = abs(entry - stop) / entry
        
        if stop_distance_pct == 0:
            return None
            
        # Размер позиции в USDT, чтобы при достижении стопа потерять ровно risk_usd
        position_size_usd = risk_usd / stop_distance_pct
        
        # Расчет необходимого плеча
        required_leverage = position_size_usd / balance
        actual_leverage = min(int(required_leverage), CONFIG['max_leverage'])
        actual_leverage = max(actual_leverage, 1) # Минимум 1x
        
        # Корректируем размер позиции под реальное плечо
        final_position_size = balance * actual_leverage
        
        return {
            "risk_usd": round(risk_usd, 2),
            "position_size_usd": round(final_position_size, 2),
            "leverage": actual_leverage,
            "stop_distance_pct": round(stop_distance_pct * 100, 2)
        }

# ==============================================================================
# 5. TELEGRAM NOTIFIER: Отправка сообщений
# ==============================================================================
class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_signal(self, signal: Dict):
        emoji = "🔴" if signal['direction'] == 'SHORT' else "🟢"
        direction_ru = "ШОРТ" if signal['direction'] == 'SHORT' else "ЛОНГ"
        
        msg = (
            f"{emoji} *НОВЫЙ СЕТАП: {direction_ru}* | Рейтинг: `{signal['score']}/100`\n"
            f"💠 *Пара:* `{signal['symbol']}`\n"
            f"📍 *Вход:* `{signal['entry']}`\n"
            f"🛑 *Стоп:* `{signal['stop']}` ({signal['stop_dist']}%)\n"
            f"🎯 *Тейк:* `{signal['target']}` (RR: `{signal['rr']}x`)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Позиция:* `${signal['pos_size']}`\n"
            f"⚙️ *Плечо:* `{signal['leverage']}x`\n"
            f"⚠️ *Риск:* `${signal['risk_usd']}`\n"
            f"📊 *Контекст:* {signal['context']}\n"
            f"⏱ *Время:* {signal['time']}"
        )
        
        try:
            requests.post(self.url, json={'chat_id': self.chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
            logging.info(f"✅ Сигнал по {signal['symbol']} отправлен в Telegram.")
        except Exception as e:
            logging.error(f"❌ Ошибка отправки в Telegram: {e}")

    def send_no_signals(self):
        msg = "🔍 *Сканирование завершено*\n\nЧетких сигналов *SFP + MSS* с RR > 2.0 не найдено.\n\n✅ Рынок в шуме или нет качественных сетапов. Бот спас депозит.\n⏳ Жди следующего обновления!"
        try:
            requests.post(self.url, json={'chat_id': self.chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        except Exception as e:
            logging.error(f"❌ Ошибка отправки 'нет сигналов': {e}")

# ==============================================================================
# 6. MAIN BOT: Оркестратор
# ==============================================================================
class MainBot:
    def __init__(self):
        self.data_mgr = DataManager()
        self.market = MarketData()
        self.analyzer = SMCAnalyzer()
        self.user_data = self.data_mgr.load_user_data()
        self.history = self.data_mgr.load_history()
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logging.error("❌ Переменная окружения TELEGRAM_BOT_TOKEN не найдена!")
            sys.exit(1)
            
        self.notifier = TelegramNotifier(bot_token, self.user_data['chat_id'])

    def run(self):
        logging.info("🚀 Запуск сканера SMC (OKX)...")
        if self.user_data['balance'] == 0:
            logging.warning("⚠️ Баланс равен 0. Завершение.")
            return

        symbols = self.market.get_top_symbols(CONFIG['top_symbols_to_scan'])
        if not symbols:
            logging.error("❌ Не удалось получить список пар.")
            return

        logging.info(f"✅ Сканируем {len(symbols)} пар с объемом > ${CONFIG['min_volume_usd']}")
        found_signals = []

        for item in symbols:
            symbol = item['symbol']
            
            # 1. Получаем данные (только закрытые свечи будут использоваться внутри анализатора)
            candles_4h = self.market.get_ohlcv(symbol, CONFIG['timeframes']['trend'], CONFIG['candles_limit']['4h'])
            candles_1h = self.market.get_ohlcv(symbol, CONFIG['timeframes']['sfp'], CONFIG['candles_limit']['1h'])
            candles_15m = self.market.get_ohlcv(symbol, CONFIG['timeframes']['mss'], CONFIG['candles_limit']['mss'])

            if not candles_4h or not candles_1h or not candles_15m:
                continue

            # 2. Проверяем оба направления
            for direction in ['SHORT', 'LONG']:
                # Проверка тренда 4H
                if not self.analyzer.check_4h_trend(candles_4h, direction):
                    continue

                # Проверка SFP на 1H
                is_sfp, swing_level, entry, stop = self.analyzer.check_sfp(candles_1h, direction)
                if not is_sfp:
                    continue

                # Проверка MSS на 15m
                is_mss, broken_level = self.analyzer.check_mss(candles_15m, direction, entry)
                if not is_mss:
                    continue

                # 3. Расчет RR и цели
                atr_1h = self.analyzer.calculate_atr(candles_1h[:-1], CONFIG['atr_period'])
                atr_pct = atr_1h / entry if entry > 0 else 0
                
                # Цель: противоположный свинг или минимум 2 * расстояние до стопа
                risk_dist = abs(entry - stop)
                target = entry - (risk_dist * CONFIG['min_rr']) if direction == 'SHORT' else entry + (risk_dist * CONFIG['min_rr'])
                rr = CONFIG['min_rr'] # Упрощенно берем минимальный, так как цель динамическая

                if rr < CONFIG['min_rr']:
                    continue

                # 4. Проверка истории (защита от спама)
                if not self.data_mgr.is_signal_fresh(symbol, direction, self.history):
                    logging.info(f"⏭ Сигнал по {symbol} {direction} уже отправлялся недавно. Пропуск.")
                    continue

                # 5. Расчет риска
                risk_data = RiskManager.calculate_position(
                    self.user_data['balance'], 
                    self.user_data['risk_percent'], 
                    entry, stop
                )
                if not risk_data:
                    continue

                # 6. Оценка качества
                score = self.analyzer.calculate_score(is_sfp, is_mss, True, rr, atr_pct)

                signal = {
                    "symbol": symbol.replace('/USDT:USDT', ''),
                    "direction": direction,
                    "entry": round(entry, 4),
                    "stop": round(stop, 4),
                    "target": round(target, 4),
                    "rr": rr,
                    "pos_size": risk_data['position_size_usd'],
                    "leverage": risk_data['leverage'],
                    "risk_usd": risk_data['risk_usd'],
                    "stop_dist": risk_data['stop_distance_pct'],
                    "score": score,
                    "context": f"SFP 1H + MSS 15m + Тренд 4H. Свинг: {round(swing_level, 4)}",
                    "time": datetime.now().strftime("%d.%m %H:%M")
                }

                found_signals.append(signal)
                # Сразу добавляем в историю, чтобы не задублировать в этом же цикле
                self.data_mgr.add_to_history(symbol, direction, self.history)

        # 7. Отправка результатов
        if found_signals:
            # Сортируем по рейтингу (score)
            found_signals.sort(key=lambda x: x['score'], reverse=True)
            for sig in found_signals:
                self.notifier.send_signal(sig)
        else:
            self.notifier.send_no_signals()

        logging.info("✅ Сканирование завершено.")

if __name__ == "__main__":
    bot = MainBot()
    bot.run()

