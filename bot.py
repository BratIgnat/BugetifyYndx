import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text
from yandex_disk import save_to_yadisk, is_user_authenticated, get_auth_link, set_auth_code, ExpenseParseError

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    format="%(asctime)s [%(levelname)s]: %(message)s",
)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("👋 Привет! Я бот для учёта расходов. Отправь голосовое сообщение или текст с расходом.")

@dp.message_handler(commands=['login'])
async def handle_login(message: types.Message):
    auth_link = get_auth_link(message.from_user.id)
    await message.reply(
        f"🔑 Для работы с Яндекс.Диском, пожалуйста, авторизуйтесь:\n"
        f"1. Перейдите по ссылке: {auth_link}\n"
        f"2. Введите полученный код командой /code <код>"
    )

@dp.message_handler(commands=['code'])
async def handle_code(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Пожалуйста, введите код после команды /code.")
        return
    code = parts[1]
    if set_auth_code(message.from_user.id, code):
        await message.reply("✅ Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
    else:
        await message.reply("❌ Не удалось авторизоваться. Попробуйте ещё раз.")

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    if not is_user_authenticated(user_id):
        await message.reply("❗ Чтобы сохранять расходы на Яндекс.Диск, нужно авторизоваться. Введите команду /login")
        return

    await message.reply("⏳ Обрабатываю голосовое сообщение...")
    voice = await message.voice.get_file()
    file_path = voice.file_path
    ogg_data = await bot.download_file(file_path)
    ogg_bytes = ogg_data.read()
    try:
        text = speech_to_text(ogg_bytes)
        await message.reply(f"📝 Распознано:\n{text}")
        save_to_yadisk(user_id, text, message_date=int(message.date.timestamp()))
        await message.reply("✅ Расход сохранён и отправлен на ваш Яндекс.Диск!")
    except ExpenseParseError as e:
        logging.warning(f"ExpenseParseError: {e}")
        await message.reply(f"⚠️ {str(e)}")
    except Exception as e:
        logging.error(f"Ошибка при обработке голоса: {e}")
        await message.reply("⚠️ Ошибка при обработке голосового сообщения.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
