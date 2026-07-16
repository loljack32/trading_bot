import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загрузка данных
def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"balance": 0, "risk_percent": 1, "chat_id": None, "last_scan": None}

# Сохранение данных
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data['chat_id'] = update.effective_chat.id
    save_data(data)
    
    await update.message.reply_text(
        f"👋 Привет! Я твой торговый ассистент.\n\n"
        f"📊 Текущий баланс: ${data['balance']}\n"
        f"⚠️ Риск: {data['risk_percent']}%\n\n"
        f"Команды:\n"
        f"/баланс - показать баланс\n"
        f"/баланс X - установить баланс (например, /баланс 1000)\n"
        f"/% - показать текущий риск\n"
        f"/% X - установить риск (например, /% 2)\n"
        f"/скан - запустить сканирование рынка\n"
        f"/помощь - показать все команды"
    )

# Команда /баланс
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if context.args:
        try:
            new_balance = float(context.args[0])
            data['balance'] = new_balance
            save_data(data)
            await update.message.reply_text(f"✅ Баланс установлен: ${new_balance}")
        except ValueError:
            await update.message.reply_text("❌ Ошибка: введите число. Пример: /баланс 1000")
    else:
        await update.message.reply_text(f"💰 Текущий баланс: ${data['balance']}")

# Команда /%
async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if context.args:
        try:
            new_risk = float(context.args[0])
            if 0 < new_risk <= 100:
                data['risk_percent'] = new_risk
                save_data(data)
                await update.message.reply_text(f"✅ Риск установлен: {new_risk}%")
            else:
                await update.message.reply_text("❌ Риск должен быть от 0 до 100")
        except ValueError:
            await update.message.reply_text("❌ Ошибка: введите число. Пример: /% 2")
    else:
        await update.message.reply_text(f"⚠️ Текущий риск: {data['risk_percent']}%")

# Команда /скан
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Запускаю сканирование рынка...")
    
    # Импортируем сканер
    from scanner import scan_market
    
    data = load_data()
    if data['balance'] == 0:
        await update.message.reply_text("❌ Сначала установи баланс командой /баланс X")
        return
    
    results = scan_market(data['balance'], data['risk_percent'])
    
    if results:
        for result in results[:3]:  # Показываем только топ-3
            message = (
                f"🚨 <b>СЕТУП SFP+MSS</b>\n\n"
                f"💎 Монета: {result['symbol']}\n"
                f" Направление: {result['direction']}\n"
                f"📍 Вход: ${result['entry']:.2f}\n"
                f"🛑 Стоп: ${result['stop']:.2f}\n"
                f"🎯 TP1: ${result['tp1']:.2f}\n"
                f"🎯 TP2: ${result['tp2']:.2f}\n\n"
                f"💰 Размер позиции: ${result['position_size']:.2f}\n"
                f" Плечо: {result['leverage']}x\n"
                f" Риск: ${result['risk_amount']:.2f}\n\n"
                f"📊 R:R TP1: {result['rr_tp1']:.2f}\n"
                f"📊 R:R TP2: {result['rr_tp2']:.2f}"
            )
            await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("😴 Сетапов не найдено. Попробуй позже.")

# Команда /помощь
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>Команды бота:</b>\n\n"
        "/баланс - показать текущий баланс\n"
        "/баланс X - установить баланс (например, /баланс 1000)\n"
        "/% - показать текущий риск\n"
        "/% X - установить риск (например, /% 2)\n"
        "/скан - запустить сканирование рынка\n"
        "/помощь - показать эту справку\n\n"
        "⚙️ <b>Как это работает:</b>\n"
        "1. Установи баланс: /баланс 1000\n"
        "2. Установи риск: /% 2\n"
        "3. Запусти скан: /скан\n"
        "4. Бот найдет сетапы и рассчитает позицию",
        parse_mode='HTML'
    )

# Главная функция
def main():
    # Токен бота (получи у @BotFather в Telegram)
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("баланс", balance))
    application.add_handler(CommandHandler("%", risk))
    application.add_handler(CommandHandler("скан", scan))
    application.add_handler(CommandHandler("помощь", help))
    
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

