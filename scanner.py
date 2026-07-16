import ccxt
import requests
import json
import os

def scan():
    # Читаем данные, которые обновил Cloudflare Worker
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    balance = float(data.get('balance', 0))
    risk_percent = float(data.get('risk_percent', 1))
    chat_id = data.get('chat_id')
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if balance == 0 or not chat_id:
        print("Баланс равен 0 или нет chat_id. Пропуск.")
        return

    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
    
    for symbol in symbols:
        try:
            candles = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            closes = [c[4] for c in candles]
            highs = [c[2] for c in candles]
            
            # Простая проверка SFP для шорта (пример)
            recent_high = max(highs[-10:])
            last_high = highs[-1]
            last_close = closes[-1]
            
            if last_high > recent_high and last_close < recent_high and last_close < closes[-2]:
                entry = last_close
                stop = last_high * 1.005
                dist = stop - entry
                
                # Расчет позиции
                risk_amount = balance * (risk_percent / 100)
                pos_size = (risk_amount / dist) * entry
                leverage = min(max(round(pos_size / balance), 1), 10)
                
                msg = (f"🚨 СЕТУП SFP+MSS\n"
                       f"💎 {symbol} | ШОРТ\n"
                       f"📍 Вход: {entry:.2f} | Стоп: {stop:.2f}\n"
                       f"💰 Позиция: ${pos_size:.2f} | Плечо: {leverage}x\n"
                       f"⚠️ Риск: ${risk_amount:.2f}")
                
                requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                              json={'chat_id': chat_id, 'text': msg})
                break # Нашли один сетап, отправили, хватит
        except Exception as e:
            continue

if __name__ == "__main__":
    scan()

