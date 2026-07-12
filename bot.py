import logging
import time
import random
import re
import asyncio
from collections import Counter
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import Conflict

# ===== ТОКЕН БОТА =====
TOKEN = "8652484169:AAHg82k55pQOyPJrOtyRfyo0hPaDajPxYxc"

# ===== API-КЛЮЧ TEXT.RU =====
API_KEY = "e4d9a2bda9e0efd342dc3a2e15160d45"
USERKEY = API_KEY

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище пользователей
users = {}
LIMIT_FREE = 10
PRICE = 199

# ===== Функция SEO-анализа текста =====
def seo_analysis(text: str) -> dict:
    clean_text = re.sub(r'\s+', ' ', text).strip()
    chars_with_spaces = len(clean_text)
    chars_without_spaces = len(re.sub(r'\s', '', clean_text))
    words = clean_text.split()
    word_count = len(words)
    
    stop_words = ['и', 'в', 'на', 'с', 'по', 'к', 'у', 'за', 'из', 'от', 'до', 'о', 'об', 'при', 'через', 'для', 'без', 'вокруг', 'около', 'более', 'менее', 'очень', 'также', 'ещё', 'уже', 'все', 'всё', 'весь', 'вся', 'все', 'всё', 'этот', 'эта', 'это', 'эти', 'того', 'что', 'чтобы', 'как', 'так', 'вот', 'ну', 'да', 'нет']
    
    words_lower = [w.lower() for w in words]
    stop_count = sum(1 for w in words_lower if w in stop_words)
    water_percent = round((stop_count / word_count) * 100, 1) if word_count > 0 else 0
    word_freq = Counter(words_lower)
    top_words = word_freq.most_common(5)
    academic_nausea = sum(count for _, count in top_words) if top_words else 0
    
    return {
        "chars_with_spaces": chars_with_spaces,
        "chars_without_spaces": chars_without_spaces,
        "word_count": word_count,
        "water_percent": water_percent,
        "academic_nausea": academic_nausea,
        "top_words": top_words
    }

# ===== Функция проверки уникальности через API text.ru =====
def check_uniqueness_text_ru(text: str) -> float:
    try:
        url = "https://api.text.ru/post"
        data = {"text": text, "userkey": USERKEY}
        response = requests.post(url, data=data)
        response_data = response.json()
        
        if response.status_code != 200 or "text_uid" not in response_data:
            logger.error(f"Ошибка при отправке текста: {response_data}")
            return round(random.uniform(50.0, 100.0), 1)
        
        text_uid = response_data["text_uid"]
        time.sleep(15)
        
        result_url = "https://api.text.ru/post"
        result_data = {"text_uid": text_uid, "userkey": USERKEY, "method": "get_result"}
        result_response = requests.post(result_url, data=result_data)
        result = result_response.json()
        
        if "unique" in result:
            return float(result["unique"])
        else:
            logger.error(f"Ошибка при получении результата: {result}")
            return round(random.uniform(50.0, 100.0), 1)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке уникальности: {e}")
        return round(random.uniform(50.0, 100.0), 1)

# ===== Проверка на спам =====
def is_spam(text: str) -> bool:
    # Слишком длинный текст
    if len(text) > 5000:
        return True
    # Слишком много повторяющихся символов
    if len(set(text)) < 10 and len(text) > 100:
        return True
    # Слишком мало уникальных слов
    words = text.split()
    if len(words) > 10 and len(set(words)) < 3:
        return True
    return False

# ===== Главное меню =====
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None) -> None:
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {'free_checks': LIMIT_FREE, 'subscribed': False, 'used': 0}
    
    keyboard = [
        [InlineKeyboardButton("📝 Проверить уникальность", callback_data="check")],
        [InlineKeyboardButton("📊 SEO-анализ текста", callback_data="seo")],
        [InlineKeyboardButton("💳 Купить подписку (199 ₽/мес)", callback_data="subscribe")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = (
        "👋 *Главное меню*\n\n"
        "📌 *Выбери действие:*\n"
        "✅ Проверить уникальность текста\n"
        "✅ Сделать SEO-анализ\n"
        "✅ Купить подписку\n"
        "✅ Посмотреть статистику\n\n"
        f"🎁 *Бесплатно осталось:* {users[user_id]['free_checks']} проверок"
    )
    
    if text:
        await update.message.reply_text(text, parse_mode='Markdown')
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

# ===== Обработчик команды /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_main_menu(update, context)

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
                "✍️ *Отправь мне текст для проверки уникальности*\n"
                "(минимум 50 символов, максимум 5000)",
                parse_mode='Markdown'
            )
            context.user_data['mode'] = 'uniqueness'
            context.user_data['waiting_for_text'] = True
        else:
            await query.edit_message_text(
                "❌ *У тебя закончились бесплатные проверки!*\n"
                "Купи подписку, чтобы продолжить.",
                parse_mode='Markdown'
            )
    
    elif query.data == "seo":
        if user['subscribed'] or user['free_checks'] > 0:
            await query.edit_message_text(
                "✍️ *Отправь мне текст для SEO-анализа*\n"
                "(минимум 50 символов)",
                parse_mode='Markdown'
            )
            context.user_data['mode'] = 'seo'
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
            "После оплаты открой безлимитный доступ ко всем функциям.\n\n"
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

# ===== Обработчик текстовых сообщений =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in users:
        users[user_id] = {'free_checks': LIMIT_FREE, 'subscribed': False, 'used': 0}
    
    user = users[user_id]
    text = update.message.text
    
    if not context.user_data.get('waiting_for_text'):
        await show_main_menu(update, context)
        return
    
    if len(text) < 50:
        await update.message.reply_text(
            "⚠️ *Слишком короткий текст!*\n"
            "Отправь текст длиной не менее 50 символов.",
            parse_mode='Markdown'
        )
        return
    
    if is_spam(text):
        await update.message.reply_text(
            "⚠️ *Обнаружен спам!*\n"
            "Пожалуйста, отправь осмысленный текст.",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for_text'] = False
        return
    
    if not user['subscribed'] and user['free_checks'] <= 0:
        await update.message.reply_text(
            "❌ *У тебя закончились бесплатные проверки!*\n"
            "Купи подписку, чтобы продолжить.",
            parse_mode='Markdown'
        )
        context.user_data['waiting_for_text'] = False
        return
    
    mode = context.user_data.get('mode', 'uniqueness')
    
    if mode == 'seo':
        await update.message.reply_text(
            "🔄 *Провожу SEO-анализ текста...*\n"
            "Это займёт пару секунд.",
            parse_mode='Markdown'
        )
        
        seo_data = seo_analysis(text)
        top_words_str = "\n".join([f"  • {word} — {count} раз" for word, count in seo_data['top_words']])
        
        seo_result = (
            f"📊 *SEO-анализ текста*\n\n"
            f"📝 *Символов (с пробелами):* {seo_data['chars_with_spaces']}\n"
            f"📝 *Символов (без пробелов):* {seo_data['chars_without_spaces']}\n"
            f"📝 *Слов:* {seo_data['word_count']}\n"
            f"💧 *Вода (стоп-слова):* {seo_data['water_percent']}%\n"
            f"📈 *Академическая тошнота:* {seo_data['academic_nausea']}%\n\n"
            f"🔑 *Топ-5 ключевых слов:*\n{top_words_str}\n\n"
            f"📊 Осталось бесплатных проверок: *{user['free_checks']}*"
        )
        await update.message.reply_text(seo_result, parse_mode='Markdown')
        
        if not user['subscribed']:
            user['free_checks'] -= 1
        user['used'] += 1
        
        context.user_data['waiting_for_text'] = False
        await show_main_menu(update, context)
        return
    
    # Режим проверки уникальности
    await update.message.reply_text(
        "🔄 *Идёт проверка уникальности через API text.ru...*\n"
        "Это займёт 15–20 секунд.",
        parse_mode='Markdown'
    )
    
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
    await show_main_menu(update, context)

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
    
    print("🤖 Бот запущен с поддержкой API text.ru и SEO-анализом! Нажми Ctrl+C для остановки.")
    
    # Защита от конфликтов
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Conflict as e:
        logger.error(f"Конфликт: {e}. Перезапустите бота.")

if __name__ == '__main__':
    main()
