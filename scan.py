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

def check_15m_mss(candles_15m, direction):
    """
    Проверяет слом структуры (MSS) на 15м таймфрейме после SFP на 1H.
    Использует предпоследнюю свечу [-2], чтобы избежать перерисовки текущей формирующейся свечи.
    """
    if len(candles_15m) < 10:
        return False, 0
    
    highs = [c[2] for c in candles_15m]
    lows = [c[3] for c in candles_15m]
    closes = [c[4] for c in candles_15m]
    
    if direction == 'SHORT':
        # 1. Находим максимум (шип SFP) в последних 4-5 свечах (это и есть 1H свеча с SFP)
        wick_high = max(highs[-5:-1])
        # 2. Находим структурный минимум ПЕРЕД этим шипом (диапазон от -9 до -5 свечей)
        structural_low = min(lows[-9:-5])
        # 3. Проверяем, закрылась ли последняя ПОЛНАЯ 15м свеча [-2] НИЖЕ структурного минимума
        mss_confirmed = closes[-2] < structural_low
        return mss_confirmed, structural_low
        
    elif direction == 'LONG':
        # 1. Находим минимум (шип SFP) в последних 4-5 свечах
        wick_low = min(lows[-5:-1])
        # 2. Находим структурный максимум ПЕРЕД этим шипом
        structural_high = max(highs[-9:-5])
        # 3. Проверяем, закрылась ли последняя ПОЛНАЯ 15м свеча [-2] ВЫШЕ структурного максимума
        mss_confirmed = closes[-2] > structural_high
        return mss_confirmed, structural_high

def scan():
    logging.info("--- 🚀 НАЧАЛО УМНОГО СКАНИРОВАНИЯ (OKX: SFP 1H + MSS 15m + Тренд 4H) ---")
    
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
            # --- ШАГ 1: Проверка SFP на 1H ---
            candles_1h = exchange.fetch_ohlcv(symbol, '1h', limit=20)
            if len(candles_1h) < 10:
                continue
                
            closes_1h = [c[4] for c in candles_1h]
            highs_1h = [c[2] for c in candles_1h]
            lows_1h = [c[3] for c in candles_1h]
            
            recent_high_1h = max(highs_1h[-10:-1])
            recent_low_1h = min(lows_1h[-10:-1])
            
            last_high_1h = highs_1h[-1]
            last_low_1h = lows_1h[-1]
            last_close_1h = closes_1h[-1]
            
            is_short_sfp = (last_high_1h > recent_high_1h) and (last_close_1h < recent_high_1h)
            is_long_sfp = (last_low_1h < recent_low_1h) and (last_close_1h > recent_low_1h)
            
            if not (is_short_sfp or is_long_sfp):
                continue # Если нет SFP, дальше не проверяем, экономим запросы
            
            # Расчет среднего диапазона для оценки фитиля
            ranges_1h = [h - l for h, l in zip(highs_1h[-10:-1], lows_1h[-10:-1])]
            avg_range_1h = sum(ranges_1h) / len(ranges_1h) if ranges_1h else 1
            
            # --- ШАГ 2: Проверка тренда на 4H ---
            candles_4h = exchange.fetch_ohlcv(symbol, '4h', limit=50)
            closes_4h = [c[4] for c in candles_4h]
            sma_20_4h = sum(closes_4h[-20:]) / 20
            current_price_4h = closes_4h[-1]
            
            # --- ШАГ 3: Проверка MSS на 15m (ТОЛЬКО если прошли 1H и 4H) ---
            candles_15m = exchange.fetch_ohlcv(symbol, '15m', limit=20)
            
            # ЛОГИКА ДЛЯ SHORT
            if is_short_sfp:
                current_wick = last_high_1h - last_close_1h
                is_good_wick = (current_wick > avg_range_1h * 1.2) # Чуть смягчил для 1H, главное наличие
                is_bearish_4h = current_price_4h < sma_20_4h
                
                if is_good_wick and is_bearish_4h:
                    mss_confirmed, struct_level = check_15m_mss(candles_15m, 'SHORT')
                    
                    if mss_confirmed:
                        logging.info(f"🎯 [{i}/{len(top_symbols)}] НАЙДЕН СЕТАП НА SHORT: {symbol}")
                        logging.info(f"   [DEBUG] SFP: high={last_high_1h:.2f}, close={last_close_1h:.2f} | 15m MSS: пробит уровень {struct_level:.2f}")
                        
                        entry = last_close_1h
                        stop = last_high_1h * 1.005 
                        dist = abs(stop - entry)
                        
                        risk_amount = balance * (risk_percent / 100)
                        pos_size = (risk_amount / dist) * entry
                        leverage = int(min(max(pos_size / balance, 1), 10))
                        coin_name = symbol.split('/')[0]
                        
                        found_signals.append({
                            'type': 'SHORT',
                            'symbol': coin_name,
                            'entry': entry,
                            'stop': stop,
                            'pos_size': pos_size,
                            'leverage': leverage,
                            'risk': risk_amount,
                            'trend': 'Медвежий 4H + MSS 15m подтвержден',
                            'volume_usd': volume_usd
                        })
                    else:
                        logging.debug(f"   [SKIP SHORT] {symbol}: SFP есть, но MSS на 15m еще не сформирован.")

            # ЛОГИКА ДЛЯ LONG
            elif is_long_sfp:
                current_wick = last_close_1h - last_low_1h
                is_good_wick = (current_wick > avg_range_1h * 1.2)
                is_bullish_4h = current_price_4h > sma_20_4h
                
                if is_good_wick and is_bullish_4h:
                    mss_confirmed, struct_level = check_15m_mss(candles_15m, 'LONG')
                    
                    if mss_confirmed:
                        logging.info(f"🎯 [{i}/{len(top_symbols)}] НАЙДЕН СЕТАП НА LONG: {symbol}")
                        logging.info(f"   [DEBUG] SFP: low={last_low_1h:.2f}, close={last_close_1h:.2f} | 15m MSS: пробит уровень {struct_level:.2f}")
                        
                        entry = last_close_1h
                        stop = last_low_1h * 0.995 
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
                            'trend': 'Бычий 4H + MSS 15m подтвержден',
                            'volume_usd': volume_usd
                        })
                    else:
                        logging.debug(f"   [SKIP LONG] {symbol}: SFP есть, но MSS на 15m еще не сформирован.")
                    
        except Exception as e:
            logging.warning(f"   [WARNING] Ошибка при обработке {symbol}: {e}")
            continue

    # 3. СОРТИРОВКА И ОТПРАВКА
    found_signals.sort(key=lambda x: x['volume_usd'], reverse=True)
    
    logging.info(f"\n--- ✅ СКАНИРОВАНИЕ ЗАВЕРШЕНО. Всего найдено сетапов: {len(found_signals)} ---")
    
    if len(found_signals) > 0:
        display_limit = 15
        signals_to_show = found_signals[:display_limit]
        
        msg = "🚨 *УМНЫЙ СКАН: SFP (1H) + MSS (15m) + ТРЕНД (4H)*\n\n"
        msg += "📊 Отсортировано по объему 24ч. MSS уже подтвержден ботом!\n"
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
            msg += f"⚠️ _Показаны топ-{display_limit} из {len(found_signals)}._\n\n"
            
        msg += "✅ _Сигналы уже прошли проверку слома структуры на 15м. Можно рассматривать вход!_"
        
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
            "Четких сигналов *SFP (1H)* с подтверждением *MSS (15m)* и трендом *4H* не найдено.\n\n"
            "✅ Это хорошо: рынок в шуме или боковике. Бот спас твой депозит.\n\n"
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

