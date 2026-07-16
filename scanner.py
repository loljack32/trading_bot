import ccxt
import requests
import json
import os
import sys

def scan():
    print("--- 🚀 НАЧАЛО СКАНИРОВАНИЯ (OKX ТОП-100) ---")
    
    # 1. Читаем настройки
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
    
    print(f"⚙️ Параметры: Баланс=${balance}, Риск={risk_percent}%, Chat_ID='{chat_id}'")

    if balance == 0:
        print("⚠️ СТОП: Баланс равен 0. Напиши боту /баланс [сумма]")
        return
    if not chat_id or not chat_id.isdigit():
        print("⚠️ СТОП: chat_id не установлен или указан неверно.")
        return
    if not bot_token:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден в Secrets GitHub.")
        return

    print("🔍 Подключаюсь к OKX и получаю Топ-100 пар по объему...\n")
    
    try:
        exchange = ccxt.okx({
            'enableRateLimit': True, 
            'options': {'defaultType': 'swap'} # Бессрочные фьючерсы
        })
        
        # Получаем тикеры всех пар
        tickers = exchange.fetch_tickers()
        
        # Фильтруем только USDT бессрочные фьючерсы, у которых есть объем
        usdt_swaps = {
            symbol: info for symbol, info in tickers.items() 
            if symbol.endswith('/USDT:USDT') and info.get('quoteVolume') is not None
        }
        
        # Сортируем по объему торгов (quoteVolume) по убыванию и берем топ-100
        sorted_pairs = sorted(usdt_swaps.keys(), key=lambda x: usdt_swaps[x]['quoteVolume'], reverse=True)
        top_100_symbols = sorted_pairs[:100]
        
        print(f"✅ Успешно получено {len(top_100_symbols)} пар. Начинаю сканирование...\n")
        
    except Exception as e:
        print(f"❌ Критическая ошибка при получении данных с OKX: {e}")
        return

    found = 0
    
    # 2. Цикл сканирования с ЭХОМ в логи
    for i, symbol in enumerate(top_100_symbols, 1):
        try:
            print(f"🔄 [{i}/100] Проверяю {symbol:<12} ...", end=" ")
            
            candles = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            closes = [c[4] for c in candles]
            highs = [c[2] for c in candles]
            
            recent_high = max(highs[-10:])
            last_high = highs[-1]
            last_close = closes[-1]
            
            # Условие SFP + MSS для шорта
            if last_high > recent_high and last_close < recent_high and last_close < closes[-2]:
                print("🎯 НАЙДЕН СЕТАП!")
                
                entry = last_close
                stop = last_high * 1.005
                dist = stop - entry
                
                risk_amount = balance * (risk_percent / 100)
                pos_size = (risk_amount / dist) * entry
                leverage = min(max(round(pos_size / balance), 1), 10)
                
                coin_name = symbol.split('/')[0]
                
                msg = (f"🚨 <b>СЕТУП SFP+MSS</b>\n"
                       f"💎 <b>{coin_name}</b> | ШОРТ\n"
                       f"📍 Вход: {entry:.2f} | Стоп: {stop:.2f}\n"
                       f"💰 Позиция: ${pos_size:.2f} | Плечо: {leverage}x\n"
                       f"⚠️ Риск: ${risk_amount:.2f}")
                
                print(f"   📤 Отправка в Telegram...", end=" ")
                response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                              json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'})
                
                if response.status_code == 200:
                    print("✅ Отправлено!")
                else:
                    print(f"❌ Ошибка Telegram: {response.text}")
                
                found += 1
                if found >= 3: 
                    print("   ⏹️ Достигнут лимит в 3 сообщения. Остановка сканирования.")
                    break
            else:
                print("нет сетапа")
                
        except Exception as e:
            print(f"⚠️ Ошибка: {str(e)[:50]}")
            continue

    # 3. Итоговое сообщение в Telegram, если ничего не найдено
    print(f"\n--- ✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО. Всего найдено сетапов: {found} ---")
    
    if found == 0:
        no_signal_msg = (
            "🔍 <b>Сканирование завершено</b>\n\n"
            "На данный момент четких сигналов <b>SFP+MSS</b> на Топ-100 парах OKX не найдено.\n\n"
            "Это хорошая новость: рынок либо в сильном тренде без ложных пробоев, либо в узком боковике. Лучше переждать, чем торговать мусор.\n\n"
            "⏳ Жди следующего обновления через 30 минут!"
        )
        print("📤 Отправляю сообщение 'Нет сигналов' в Telegram...")
        requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                      json={'chat_id': chat_id, 'text': no_signal_msg, 'parse_mode': 'HTML'})

if __name__ == "__main__":
    scan()

