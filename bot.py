import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text
from yandex_disk import save_to_yadisk, is_user_authenticated, get_auth_link, set_auth_code, ExpenseParseError, save_timezone, parse_expense
import pytz

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    format="%(asctime)s [%(levelname)s]: %(message)s",
)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ======== Универсальная функция защиты от длинных сообщений =======
MAX_MSG_LEN = 4000

async def safe_reply(message, text, **kwargs):
    """Отправляет текст частями, если он слишком длинный для Telegram."""
    for i in range(0, len(text), MAX_MSG_LEN):
        await message.reply(text[i:i+MAX_MSG_LEN], **kwargs)

# ======== Таймзоны: список самых популярных =======
POPULAR_TIMEZONES = [
    "Europe/Moscow", "Europe/Kaliningrad", "Asia/Yekaterinburg", "Asia/Novosibirsk",
    "Asia/Krasnoyarsk", "Asia/Irkutsk", "Asia/Yakutsk", "Asia/Vladivostok",
    "Asia/Almaty", "Asia/Aqtobe", "Asia/Bishkek", "Asia/Tbilisi",
    "Asia/Baku", "Europe/Minsk", "Asia/Sakhalin", "Europe/Kiev"
]
# Можно расширять список при необходимости

# ========== Команды ===================

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await safe_reply(
        message,
        "👋 Привет! Я бот для учёта расходов.\n"
        "Отправь голосовое сообщение или текст с расходом.\n"
        "Для корректного времени расходов установи свой часовой пояс: /set_timezone"
    )

@dp.message_handler(commands=['login'])
async def handle_login(message: types.Message):
    auth_link = get_auth_link(message.from_user.id)
    await safe_reply(
        message,
        f"🔑 Для работы с Яндекс.Диском, пожалуйста, авторизуйтесь:\n"
        f"1. Перейдите по ссылке: {auth_link}\n"
        f"2. Введите полученный код командой /code <код>"
    )

@dp.message_handler(commands=['code'])
async def handle_code(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await safe_reply(message, "Пожалуйста, введите код после команды /code.")
        return
    code = parts[1]
    if set_auth_code(message.from_user.id, code):
        await safe_reply(message, "✅ Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
    else:
        await safe_reply(message, "❌ Не удалось авторизоваться. Попробуйте ещё раз.")

@dp.message_handler(commands=['set_timezone'])
async def set_timezone_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(0, len(POPULAR_TIMEZONES), 2):
        row = POPULAR_TIMEZONES[i:i+2]
        keyboard.row(*row)
    keyboard.row("Показать все таймзоны")
    await safe_reply(
        message,
        "Выберите ваш часовой пояс (или нажмите 'Показать все таймзоны' для полного списка):",
        reply_markup=keyboard
    )

@dp.message_handler(lambda msg: msg.text in POPULAR_TIMEZONES)
async def handle_timezone_popular(message: types.Message):
    save_timezone(message.from_user.id, message.text)
    await safe_reply(message, f"Ваш часовой пояс установлен: {message.text}", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text == "Показать все таймзоны")
async def handle_show_all_timezones(message: types.Message):
    await safe_reply(
        message,
        "Полный список таймзон можно найти здесь:\n"
        "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones\n\n"
        "Скопируйте и отправьте нужную таймзону сообщением.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message_handler(lambda msg: msg.text in pytz.all_timezones)
async def handle_timezone_text(message: types.Message):
    save_timezone(message.from_user.id, message.text)
    await safe_reply(message, f"Ваш часовой пояс установлен: {message.text}", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    if not is_user_authenticated(user_id):
        await safe_reply(message, "❗ Чтобы сохранять расходы на Яндекс.Диск, нужно авторизоваться. Введите команду /login")
        return

    await safe_reply(message, "⏳ Обрабатываю голосовое сообщение...")
    voice = await message.voice.get_file()
    file_path = voice.file_path
    ogg_data = await bot.download_file(file_path)
    ogg_bytes = ogg_data.read()
    try:
        text = speech_to_text(ogg_bytes)
        amount, category = parse_expense(text)
        if amount is None or category is None:
            raise ExpenseParseError("Сообщение должно содержать сумму и категорию. Пример: '100 рублей такси', '150 кефир'.")
        await safe_reply(message, f"📝 Распознано:\n{text}")
        save_to_yadisk(user_id, text, message_date=int(message.date.timestamp()))
        await safe_reply(message, "✅ Расход сохранён и отправлен на ваш Яндекс.Диск!")
    except ExpenseParseError as e:
        logging.warning(f"ExpenseParseError: {e}")
        await safe_reply(message, f"⚠️ {str(e)}")
    except Exception as e:
        logging.error(f"Ошибка при обработке голоса: {e}")
        await safe_reply(message, "⚠️ Ошибка при обработке голосового сообщения.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
