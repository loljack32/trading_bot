import ccxt
import requests
import json
import os
import sys
import logging

# Настройка логирования: вывод и в консоль, и в файл bot_log.txt
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def scan():
    logging.info("--- 🚀 НАЧАЛО УМНОГО СКАНИРОВАНИЯ (OKX LONG + SHORT) ---")
    
    # 1. Читаем настройки
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"✅ Успешно прочитан data.json: {data}")
    except Exception as e:
        logging.error(f"❌ ОШИБКА чтения data.json: {e}")
        sys.exit(1)

    balance = float(data.get('balance', 0))
    risk_percent = float(data.get('risk_percent', 1))
    chat_id = str(data.get('chat_id', ''))
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    logging.info(f"⚙️ Параметры: Баланс=${balance}, Риск={risk_percent}%, Chat_ID='{chat_id}'")

    if balance == 0:
        logging.warning("⚠️ СТОП: Баланс равен 0. Напиши боту /баланс [сумма]")
        return
    if not chat_id or not chat_id.isdigit():
        logging.warning("⚠️ СТОП: chat_id не установлен или указан неверно.")
        return
    if not bot_token:
        logging.error("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден в Secrets GitHub.")
        return

    logging.info("🔍 Получаю тикеры с OKX и фильтрую по объему...\n")
    
    try:
        exchange = ccxt.okx({
            'enableRateLimit': True, 
            'options': {'defaultType': 'swap'}
        })
        
        tickers = exchange.fetch_tickers()
        
        min_volume_usd = 50_000 
        
        valid_symbols = []
        for symbol, info in tickers.items():
            if symbol.endswith('/USDT:USDT') and info.get('baseVolume') is not None and info.get('last') is not None:
                volume_usd = info['baseVolume'] * info['last']
                if volume_usd > min_volume_usd:
                    valid_symbols.append({
                        'symbol': symbol,
                        'volume_usd': volume_usd,
                        'info': info
                    })
        
        valid_symbols.sort(key=lambda x: x['volume_usd'], reverse=True)
        top_symbols = valid_symbols[:100]
        
        logging.info(f"✅ Найдено {len(top_symbols)} пар с объемом > ${min_volume_usd} для сканирования")
        logging.info(f"   Топ-3 самых ликвидных: {[item['symbol'] for item in top_symbols[:3]]}\n")
        
    except Exception as e:
        logging.error(f"❌ Критическая ошибка при получении данных с OKX: {e}")
        return

    found_signals = []
    
    # 2. Цикл сканирования
    for i, item in enumerate(top_symbols, 1):
        symbol = item['symbol']
        volume_usd = item['volume_usd']
        
        try:
            candles_1h = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            if len(candles_1h) < 10:
                continue
                
            closes = [c[4] for c in candles_1h]
            highs = [c[2] for c in candles_1h]
            lows = [c[3] for c in candles_1h]
            
            recent_high = max(highs[-10:-1])
            recent_low = min(lows[-10:-1])
            
            last_high = highs[-1]
            last_low = lows[-1]
            last_close = closes[-1]
            
            # ИСПРАВЛЕННАЯ ЛОГИКА SFP (Swing Failure Pattern)
            # Для 1H таймфрейма сам факт закрытия свечи внутри диапазона после пробоя уже является сильным сигналом.
            # Проверка MSS на той же самой 1H свече математически противоречива, поэтому мы используем SFP + фильтр тренда 4H.
            
            is_short_sfp = (last_high > recent_high) and (last_close < recent_high)
            is_long_sfp = (last_low < recent_low) and (last_close > recent_low)
            
            if not (is_short_sfp or is_long_sfp):
                continue
            
            # Расчет среднего диапазона свечи для оценки качества фитиля
            ranges = [h - l for h, l in zip(highs[-10:-1], lows[-10:-1])]
            avg_range = sum(ranges) / len(ranges) if ranges else 1
            
            candles_4h = exchange.fetch_ohlcv(symbol, '4h', limit=50)
            closes_4h = [c[4] for c in candles_4h]
            sma_20_4h = sum(closes_4h[-20:]) / 20
            current_price_4h = closes_4h[-1]
            
            # ПРОВЕРКА НА SHORT
            if is_short_sfp:
                current_wick = last_high - last_close
                is_good_wick = (current_wick > avg_range * 1.5) and (current_wick < avg_range * 5.0)
                # Для шорта по SFP лучше, чтобы общий тренд 4H был медвежьим или нейтральным (цена ниже или около SMA)
                is_bearish_4h = current_price_4h < sma_20_4h
                
                if is_good_wick and is_bearish_4h:
                    logging.info(f"🎯 [{i}/{len(top_symbols)}] НАЙДЕН СЕТАП НА SHORT: {symbol}")
                    # Детальный лог для проверки
                    logging.info(f"   [DEBUG SHORT] last_high={last_high}, recent_high={recent_high}, last_close={last_close}")
                    logging.info(f"   [DEBUG SHORT] wick={current_wick}, avg_range={avg_range}, 4h_price={current_price_4h}, 4h_sma={sma_20_4h}")
                    
                    entry = last_close
                    stop = last_high * 1.005 # 0.5% выше максимума фитиля
                    dist = abs(stop - entry)
                    
                    risk_amount = balance * (risk_percent / 100)
                    pos_size = (risk_amount / dist) * entry
                    leverage = int(min(max(pos_size / balance, 1), 10)) # Гарантируем целое число
                    coin_name = symbol.split('/')[0]
                    
                    found_signals.append({
                        'type': 'SHORT',
                        'symbol': coin_name,
                        'entry': entry,
                        'stop': stop,
                        'pos_size': pos_size,
                        'leverage': leverage,
                        'risk': risk_amount,
                        'trend': 'Медвежий (цена < SMA20 4H)',
                        'volume_usd': volume_usd
                    })
                    continue

            # ПРОВЕРКА НА LONG
            if is_long_sfp:
                current_wick = last_close - last_low
                is_good_wick = (current_wick > avg_range * 1.5) and (current_wick < avg_range * 5.0)
                # Для лонга по SFP лучше, чтобы общий тренд 4H был бычьим (цена выше SMA)
                is_bullish_4h = current_price_4h > sma_20_4h
                
                if is_good_wick and is_bullish_4h:
                    logging.info(f"🎯 [{i}/{len(top_symbols)}] НАЙДЕН СЕТАП НА LONG: {symbol}")
                    # Детальный лог для проверки
                    logging.info(f"   [DEBUG LONG] last_low={last_low}, recent_low={recent_low}, last_close={last_close}")
                    logging.info(f"   [DEBUG LONG] wick={current_wick}, avg_range={avg_range}, 4h_price={current_price_4h}, 4h_sma={sma_20_4h}")
                    
                    entry = last_close
                    stop = last_low * 0.995 # 0.5% ниже минимума фитиля
                    dist = abs(stop - entry)
                    
                    risk_amount = balance * (risk_percent / 100)
                    pos_size = (risk_amount / dist) * entry
                    leverage = int(min(max(pos_size / balance, 1), 10))
                    coin_name = symbol.split('/')[0]
                    
                    found_signals.append({
                        'type': 'LONG',
                        'symbol': coin_name,
                        'entry': entry,
                        'stop': stop,
                        'pos_size': pos_size,
                        'leverage': leverage,
                        'risk': risk_amount,
                        'trend': 'Бычий (цена > SMA20 4H)',
                        'volume_usd': volume_usd
                    })
                    
        except Exception as e:
            logging.warning(f"   [WARNING] Ошибка при обработке {symbol}: {e}")
            continue

    # 3. СОРТИРОВКА И ОТПРАВКА
    found_signals.sort(key=lambda x: x['volume_usd'], reverse=True)
    
    logging.info(f"\n--- ✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО. Всего найдено сетапов: {len(found_signals)} ---")
    
    if len(found_signals) > 0:
        display_limit = 15
        signals_to_show = found_signals[:display_limit]
        
        msg = "🚨 *УМНЫЙ СКАН: ТОП СЕТАПЫ SFP + ТРЕНД 4H*\n\n"
        msg += "📊 Отсортировано по объему 24ч (чем выше, тем надежнее):\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, sig in enumerate(signals_to_show, 1):
            emoji = "🔴" if sig['type'] == 'SHORT' else "🟢"
            vol_formatted = f"{sig['volume_usd']:,.0f}".replace(',', ' ')
            
            msg += (f"{i}. *{sig['symbol']}* | {emoji} *{sig['type']}*\n"
                    f"   📍 Вход: `{sig['entry']:.2f}` | Стоп: `{sig['stop']:.2f}`\n"
                    f"   💰 Поз: `${sig['pos_size']:.0f}` | Плечо: `{sig['leverage']}x`\n"
                    f"   ⚠️ Риск: `${sig['risk']:.2f}` | 📊 {sig['trend']}\n"
                    f"   📈 Объем 24ч: `${vol_formatted}`\n\n")
            
        if len(found_signals) > display_limit:
            msg += f"⚠️ _Показаны топ-{display_limit} из {len(found_signals)}. Остальные отфильтрованы._\n\n"
            
        msg += "⚠️ _Не забывай про риск-менеджмент! Проверяй график на 15м перед входом (жди слом структуры)._"
        
        logging.info("📤 Отправляю сводный отчет в Telegram...")
        try:
            response = requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                          json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
            
            if response.status_code == 200:
                logging.info("✅ Успешно отправлено в Telegram!")
            else:
                logging.error(f"❌ Ошибка Telegram: {response.text}")
        except Exception as e:
            logging.error(f"❌ Ошибка сети при отправке в Telegram: {e}")

    else:
        no_signal_msg = (
            "🔍 *Сканирование завершено*\n\n"
            f"Проверено {len(top_symbols)} самых ликвидных пар на OKX.\n\n"
            "Четких сигналов *SFP* с подтверждением тренда 4H и правильным фитилем не найдено.\n\n"
            "✅ Это хорошо: рынок в шуме или боковике. Бот спас твой депозит от лишних сделок.\n\n"
            "⏳ Жди следующего обновления!"
        )
        logging.info("📤 Отправляю сообщение 'Нет сигналов' в Telegram...")
        try:
            requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', 
                          json={'chat_id': chat_id, 'text': no_signal_msg, 'parse_mode': 'Markdown'}, timeout=10)
        except Exception as e:
            logging.error(f"❌ Ошибка сети при отправке в Telegram: {e}")

if __name__ == "__main__":
    scan()

