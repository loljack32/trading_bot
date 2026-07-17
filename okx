import ccxt
import json

# Подключаемся к OKX
exchange = ccxt.okx({
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

# Получаем тикер BTC
print("🔍 Получаю тикер BTC/USDT:USDT...\n")
ticker = exchange.fetch_ticker('BTC/USDT:USDT')

# Выводим ВСЕ поля тикера
print("📊 ВСЕ ПОЛЯ ТИКЕРА BTC:\n")
for key, value in ticker.items():
    print(f"{key:20} = {value}")

print("\n" + "="*50)
print("🔍 Теперь получаю ВСЕ тикеры и смотрю структуру...\n")

# Получаем все тикеры
tickers = exchange.fetch_tickers()

# Берем первый попавшийся USDT тикер для примера
for symbol, info in list(tickers.items())[:5]:
    if '/USDT:USDT' in symbol:
        print(f"\n📌 Пример тикера: {symbol}")
        print(f"   quoteVolume = {info.get('quoteVolume')}")
        print(f"   baseVolume  = {info.get('baseVolume')}")
        print(f"   volume      = {info.get('volume')}")
        
        # Показываем ВСЕ ключи
        print(f"   Все доступные ключи: {list(info.keys())}")
        break

print("\n✅ Готово! Теперь ты знаешь, какие поля есть.")

