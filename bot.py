import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text
from yandex_disk import save_to_yadisk, is_user_authenticated, get_auth_link, set_auth_code

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, filename="bot.log",
                    format="%(asctime)s [%(levelname)s]: %(message)s")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ФУНКЦИЯ ПАРСИНГА ---
import re
def parse_expense(text):
    """
    Парсит строку типа '301 рубль 50 копеек мороженое' -> (301.50, 'мороженое')
    Возвращает (float, str) либо (None, None) если не удалось распарсить.
    """
    pattern = r"(\d+)\s*(?:руб(?:лей|ль|ля|\.|)?|р|руб\.)?(?:\s*(\d+)\s*(?:коп(?:еек|ей|\.|)?))?\s*(.*)"
    match = re.match(pattern, text.strip().lower())
    if not match:
        return None, None

    rub = match.group(1)
    kop = match.group(2)
    category = match.group(3).strip()

    amount = float(rub)
    if kop:
        amount += float(kop) / 100

    return amount, category or ""

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("👋 Привет! Я бот для учёта расходов. Просто отправь голосовое сообщение с суммой и категорией.")

@dp.message_handler(commands=["login"])
async def login(message: types.Message):
    user_id = message.from_user.id
    link = get_auth_link(user_id)
    await message.reply(f"🔑 Для работы с Яндекс.Диском, пожалуйста, авторизуйтесь:\n1. Перейдите по ссылке: {link}\n2. Введите полученный код командой /code <код>")

@dp.message_handler(commands=["code"])
async def code(message: types.Message):
    user_id = message.from_user.id
    try:
        auth_code = message.text.split(maxsplit=1)[1].strip()
        if set_auth_code(user_id, auth_code):
            await message.reply("✅ Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
        else:
            await message.reply("❗️ Ошибка авторизации. Попробуйте ещё раз.")
    except Exception:
        await message.reply("❗️ Введите код в формате: /code <код>")

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id

    if not is_user_authenticated(user_id):
        await message.reply("❗️ Чтобы сохранять расходы на Яндекс.Диск, нужно авторизоваться. Введите команду /login")
        return

    # Скачиваем голосовое сообщение
    file_info = await bot.get_file(message.voice.file_id)
    ogg_path = f"{user_id}.ogg"
    await bot.download_file(file_info.file_path, ogg_path)

    try:
        text = speech_to_text(ogg_path)
        amount, category = parse_expense(text)
        if amount is None:
            await message.reply("❗️ Не удалось распознать сумму расхода. Попробуйте ещё раз.")
            return

        await message.reply(f"✅ Расход распознан:\nСумма: {amount}\nКатегория: {category}")

        # Сохраняем в Excel на Яндекс.Диске
        save_to_yadisk(user_id, amount, category)
        await message.reply("✅ Расход сохранён и загружен на Яндекс.Диск!")

    except Exception as e:
        logging.error(f"Ошибка при обработке голоса: {e}")
        await message.reply("⚠️ Ошибка при обработке голосового сообщения.")

    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
