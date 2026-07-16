import ccxt
import requests
import json
import os
import sys

def scan():
    print("--- 🚀 НАЧАЛО СКАНИРОВАНИЯ (OKX) ---")
    
    # 1. Читаем файл
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        print(f"✅ Успешно прочитан data.json: {data}")
    except Exception as e:
        print(f"❌ ОШИБКА чтения data.json: {e}")
        sys.exit(1)

    balance = float(data.get('balance', 0))
    risk_percent = float(data.get('risk_percent', 1))
    chat_id = str(data.get('chat_id', ''))
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    print(f"⚙️ Параметры: Баланс={balance}, Риск={risk_percent}%, Chat_ID='{chat_id}'")

    # 2. Проверки
    if balance == 0:
        print("⚠️ СТОП: Баланс равен 0.")
        return
        
    if not chat_id or chat_id == "ТВОЙ_CHAT_ID_ЦИФРАМИ" or not chat_id.isdigit():
        print("⚠️ СТОП: chat_id не установлен.")
        return

    if not bot_token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден.")
        return

    print("🔍 Начинаем опрос биржи OKX...")
    
    # ИСПОЛЬЗУЕМ OKX. Для бессрочных фьючерсов в ccxt используется тип 'swap'
    exchange = ccxt.okx({
        'enableRateLimit': True, 
        'options': {
            'defaultType': 'swap'  
        }
    })
    
    # Формат символов для OKX swap в ccxt
    symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT', 'ADA/USDT:USDT', 'DOGE/USDT:USDT', 'AVAX/USDT:USDT', 'LINK/USDT:USDT', 'NEAR/USDT:USDT']
    
    found = 0
    for symbol in symbols:
        try:
            # Получаем свечи (1 час, 20 штук)
            candles = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            closes = [c[4] for c in candles]
            highs = [c[2] for c in candles]
            
            # Простая проверка SFP для шорта
            recent_high = max(highs[-10:])
            last_high = highs[-1]
            last_close = closes[-1]
            
            if last_high > recent_high and last_close < recent_high and last_close < closes[-2]:
                print(f"🎯 НАЙДЕН СЕТАП: {symbol}")
                entry = last_close
                stop = last_high * 1.005
                dist = stop - entry
                
                risk_amount = balance * (risk_percent / 100)
                pos_size = (risk_amount / dist) * entry
                leverage = min(max(round(pos_size / balance), 1), 10)
                
                # Форматируем имя монеты (убираем /USDT:USDT)
                coin_name = symbol.split('/')[0]
                
                msg = (f"🚨 СЕТУП SFP+MSS\n"
                       f"💎 {coin_name} | ШОРТ\n"
                       f"📍 Вход: {entry:.2f} | Стоп: {stop:.2f}\n"
                       f"💰 Позиция: ${pos_size:.2f} | Плечо: {leverage}x\n"
                       f"⚠️ Риск: ${risk_amount:.2f}")
                
                print(f"📤 Отправка сообщения в Telegram...")
                response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                              json={'chat_id': chat_id, 'text': msg})
                print(f"📬 Ответ Telegram: {response.status_code} - {response.text}")
                
                found += 1
                if found >= 3: 
                    print("Достигнут лимит в 3 сообщения. Остановка.")
                    break
        except Exception as e:
            print(f"⚠️ Ошибка при обработке {symbol}: {e}")
            continue

    print(f"--- ✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО. Найдено сетапов: {found} ---")

if __name__ == "__main__":
    scan()

