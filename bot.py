import logging
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ===== ТОКЕН БОТА (ЗАМЕНИ НА СВОЙ) =====
TOKEN = "8652484169:AAHg82k55pQOyPJrOtyRfyo0hPaDajPxYxc"

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище пользователей (в памяти)
users = {}
LIMIT_FREE = 10          # бесплатных проверок
PRICE = 199              # цена подписки в рублях

# ===== Функция "антиплагиат" (симуляция) =====
def check_uniqueness(text: str) -> float:
    """
    Упрощённая проверка уникальности.
    Для демонстрации возвращает случайное число от 50 до 100%.
    """
    uniqueness = round(random.uniform(50.0, 100.0), 1)
    time.sleep(1)  # Имитация задержки
    return uniqueness

# ===== Обработчик команды /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {'free_checks': LIMIT_FREE, 'subscribed': False, 'used': 0}
    
    keyboard = [
        [InlineKeyboardButton("📝 Проверить текст", callback_data="check")],
        [InlineKeyboardButton("💳 Купить подписку (199 ₽/мес)", callback_data="subscribe")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "👋 *Привет! Я UniqBot — твой персональный антиплагиат.*\n\n"
        "📌 *Как я работаю:*\n"
        "1. Пришли мне любой текст (от 50 символов)\n"
        "2. Я проверю его уникальность за пару секунд\n"
        "3. Ты получишь результат в процентах\n\n"
        f"🎁 *Бесплатный лимит:* {LIMIT_FREE} проверок\n"
        f"💎 *Подписка:* {PRICE} ₽/мес — безлимит\n\n"
        "👇 *Нажми на кнопку, чтобы начать*"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ===== Обработчик нажатий на кнопки =====
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id not in users:
        users[user_id] = {'free_checks': LIMIT_FREE, 'subscribed': False, 'used': 0}
    
    user = users[user_id]
    
    if query.data == "check":
        if user['subscribed'] or user['free_checks'] > 0:
            await query.edit_message_text(
                "✍️ *Отправь мне текст для проверки*\n"
                "(минимум 50 символов)",
                parse_mode='Markdown'
            )
            context.user_data['waiting_for_text'] = True
        else:
            await query.edit_message_text(
                "❌ *У тебя закончились бесплатные проверки!*\n"
                "Купи подписку, чтобы продолжить.",
                parse_mode='Markdown'
            )
    
    elif query.data == "subscribe":
        await query.edit_message_text(
            f"💳 *Оплата подписки*\n\n"
            f"Стоимость: *{PRICE} ₽/мес*\n"
            "После оплаты открой безлимитный доступ к проверкам.\n\n"
            "🚧 *Способ оплаты:*\n"
            "Пока что это демо-версия. Для реальной оплаты нужно подключить платежный шлюз.\n\n"
            "Нажми /start, чтобы вернуться в меню.",
            parse_mode='Markdown'
        )
    
    elif query.data == "stats":
        free_left = user['free_checks']
        sub_status = "✅ Активна" if user['subscribed'] else "❌ Неактивна"
        total_used = user['used']
        await query.edit_message_text(
            f"📊 *Твоя статистика*\n\n"
            f"• Бесплатных проверок осталось: *{free_left}*\n"
            f"• Подписка: *{sub_status}*\n"
            f"• Всего использовано проверок: *{total_used}*\n\n"
            "Нажми /start, чтобы вернуться в меню.",
            parse_mode='Markdown'
        )

# ===== Обработчик текстовых сообщений (проверка текста) =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {'free_checks': LIMIT_FREE, 'subscribed': False, 'used': 0}
    
    user = users[user_id]
    text = update.message.text
    
    if not context.user_data.get('waiting_for_text'):
        await update.message.reply_text(
            "Нажми /start, чтобы открыть меню и начать проверку."
        )
        return
    
    if len(text) < 50:
        await update.message.reply_text(
            "⚠️ *Слишком короткий текст!*\n"
            "Отправь текст длиной не менее 50 символов.",
            parse_mode='Markdown'
        )
        return
    
    if not user['subscribed'] and user['free_checks'] <= 0:
        await update.message.reply_text(
            "❌ *У тебя закончились бесплатные проверки!*\n"
            "Купи подписку, чтобы продолжить.",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for_text'] = False
        return
    
    await update.message.reply_text(
        "🔄 *Идёт проверка уникальности...*\n"
        "Это займёт пару секунд.",
        parse_mode='Markdown'
    )
    
    uniqueness = check_uniqueness(text)
    
    if not user['subscribed']:
        user['free_checks'] -= 1
    user['used'] += 1
    
    result_text = (
        f"✅ *Результат проверки*\n\n"
        f"📄 *Текст:*\n`{text[:200]}...`\n\n"
        f"🔢 *Уникальность:* **{uniqueness}%**\n\n"
        f"📊 Осталось бесплатных проверок: *{user['free_checks']}*"
    )
    await update.message.reply_text(result_text, parse_mode='Markdown')
    
    context.user_data['waiting_for_text'] = False

# ===== Команда /help =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *Команды бота:*\n"
        "/start — открыть главное меню\n"
        "/help — эта справка\n\n"
        "Просто нажми /start и следуй инструкциям!",
        parse_mode='Markdown'
    )

# ===== ЗАПУСК БОТА =====
def main() -> None:
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()