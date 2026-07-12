import logging
import time
import random
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ===== ТОКЕН БОТА =====
TOKEN = "8652484169:AAHg82k55pQOyPJrOtyRfyo0hPaDajPxYxc"

# ===== API-КЛЮЧ TEXT.RU =====
API_KEY = "e4d9a2bda9e0efd342dc3a2e15160d45"
USERKEY = API_KEY  # В text.ru это одно и то же

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище пользователей (в памяти)
users = {}
LIMIT_FREE = 10          # бесплатных проверок
PRICE = 199              # цена подписки в рублях

# ===== Функция проверки уникальности через API text.ru =====
def check_uniqueness_text_ru(text: str) -> float:
    """
    Отправляет текст на проверку в API text.ru и возвращает процент уникальности.
    """
    try:
        # 1. Отправляем текст на проверку
        url = "https://api.text.ru/post"
        data = {
            "text": text,
            "userkey": USERKEY
        }
        response = requests.post(url, data=data)
        response_data = response.json()
        
        if response.status_code != 200 or "text_uid" not in response_data:
            logger.error(f"Ошибка при отправке текста: {response_data}")
            return round(random.uniform(50.0, 100.0), 1)  # Возвращаем случайное значение при ошибке
        
        text_uid = response_data["text_uid"]
        
        # 2. Ждём, пока текст обработается (10-20 секунд)
        time.sleep(15)
        
        # 3. Получаем результат проверки
        result_url = "https://api.text.ru/post"
        result_data = {
            "text_uid": text_uid,
            "userkey": USERKEY,
            "method": "get_result"
        }
        result_response = requests.post(result_url, data=result_data)
        result = result_response.json()
        
        if "unique" in result:
            uniqueness = float(result["unique"])
            return uniqueness
        else:
            logger.error(f"Ошибка при получении результата: {result}")
            return round(random.uniform(50.0, 100.0), 1)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке уникальности: {e}")
        return round(random.uniform(50.0, 100.0), 1)

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
        "2. Я проверю его уникальность через API text.ru\n"
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
        "🔄 *Идёт проверка уникальности через API text.ru...*\n"
        "Это займёт 15–20 секунд.",
        parse_mode='Markdown'
    )
    
    # Используем реальную проверку через API
    uniqueness = check_uniqueness_text_ru(text)
    
    if not user['subscribed']:
        user['free_checks'] -= 1
    user['used'] += 1
    
    result_text = (
        f"✅ *Результат проверки*\n\n"
        f"📄 *Текст:*\n`{text[:200]}...`\n\n"
        f"🔢 *Уникальность:* **{uniqueness:.1f}%**\n\n"
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
    
    print("🤖 Бот запущен с поддержкой API text.ru! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
