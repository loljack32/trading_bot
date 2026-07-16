import ccxt
import numpy as np

def detect_sfp_mss(candles, direction='short'):
    """
    Определяет SFP + MSS паттерн
    Возвращает: entry, stop, tp1, tp2 или None
    """
    if len(candles) < 20:
        return None
    
    closes = [c[4] for c in candles]  # Цены закрытия
    highs = [c[2] for c in candles]   # Максимумы
    lows = [c[3] for c in candles]    # Минимумы
    
    if direction == 'short':
        # Ищем SFP для шорта: цена пробила максимум и вернулась
        recent_high = max(highs[-10:])
        last_close = closes[-1]
        last_high = highs[-1]
        
        # SFP: свеча пробила уровень, но закрылась ниже
        if last_high > recent_high and last_close < recent_high:
            # MSS: цена начала падать
            if len(closes) >= 3 and closes[-1] < closes[-2]:
                entry = last_close
                stop = last_high * 1.005  # Стоп чуть выше хая
                distance_to_stop = stop - entry
                
                # Тейки на основе R:R
                tp1 = entry - (distance_to_stop * 1.5)
                tp2 = entry - (distance_to_stop * 2.5)
                
                return {
                    'entry': entry,
                    'stop': stop,
                    'tp1': tp1,
                    'tp2': tp2,
                    'distance_to_stop': distance_to_stop
                }
    
    elif direction == 'long':
        # Ищем SFP для лонга: цена пробила минимум и вернулась
        recent_low = min(lows[-10:])
        last_close = closes[-1]
        last_low = lows[-1]
        
        # SFP: свеча пробила уровень, но закрылась выше
        if last_low < recent_low and last_close > recent_low:
            # MSS: цена начала расти
            if len(closes) >= 3 and closes[-1] > closes[-2]:
                entry = last_close
                stop = last_low * 0.995  # Стоп чуть ниже лоя
                distance_to_stop = entry - stop
                
                # Тейки на основе R:R
                tp1 = entry + (distance_to_stop * 1.5)
                tp2 = entry + (distance_to_stop * 2.5)
                
                return {
                    'entry': entry,
                    'stop': stop,
                    'tp1': tp1,
                    'tp2': tp2,
                    'distance_to_stop': distance_to_stop
                }
    
    return None

def calculate_position(balance, risk_percent, entry, stop, tp1, tp2, direction):
    """
    Рассчитывает размер позиции и плечо
    """
    risk_amount = balance * (risk_percent / 100)
    distance_to_stop = abs(entry - stop)
    
    # Размер позиции в монетах
    position_size_coins = risk_amount / distance_to_stop
    
    # Стоимость позиции
    position_value = position_size_coins * entry
    
    # Плечо (минимум 1x, максимум 10x для безопасности)
    leverage = min(max(position_value / balance, 1), 10)
    
    # Округляем до целого
    leverage = round(leverage)
    if leverage < 1:
        leverage = 1
    
    # R:R
    distance_to_tp1 = abs(tp1 - entry)
    distance_to_tp2 = abs(tp2 - entry)
    rr_tp1 = distance_to_tp1 / distance_to_stop
    rr_tp2 = distance_to_tp2 / distance_to_stop
    
    return {
        'position_size': position_value,
        'leverage': leverage,
        'risk_amount': risk_amount,
        'rr_tp1': rr_tp1,
        'rr_tp2': rr_tp2
    }

def scan_market(balance, risk_percent):
    """
    Сканирует топ-20 монет на наличие SFP+MSS
    """
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'  # Фьючерсы
        }
    })
    
    # Топ-20 монет по объему
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'MATIC/USDT',
        'LINK/USDT', 'UNI/USDT', 'LTC/USDT', 'ATOM/USDT', 'ETC/USDT',
        'XLM/USDT', 'FIL/USDT', 'APT/USDT', 'NEAR/USDT', 'ARB/USDT'
    ]
    
    results = []
    
    for symbol in symbols:
        try:
            # Получаем свечи 1Ч (20 последних)
            candles = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            
            # Проверяем оба направления
            for direction in ['short', 'long']:
                sfp_mss = detect_sfp_mss(candles, direction)
                
                if sfp_mss:
                    # Рассчитываем позицию
                    calc = calculate_position(
                        balance, risk_percent,
                        sfp_mss['entry'], sfp_mss['stop'],
                        sfp_mss['tp1'], sfp_mss['tp2'],
                        direction
                    )
                    
                    result = {
                        'symbol': symbol,
                        'direction': 'ШОРТ' if direction == 'short' else 'ЛОНГ',
                        'entry': sfp_mss['entry'],
                        'stop': sfp_mss['stop'],
                        'tp1': sfp_mss['tp1'],
                        'tp2': sfp_mss['tp2'],
                        'position_size': calc['position_size'],
                        'leverage': calc['leverage'],
                        'risk_amount': calc['risk_amount'],
                        'rr_tp1': calc['rr_tp1'],
                        'rr_tp2': calc['rr_tp2']
                    }
                    
                    results.append(result)
        
        except Exception as e:
            print(f"Ошибка при сканировании {symbol}: {e}")
            continue
    
    return results

