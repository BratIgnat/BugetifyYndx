import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

from speechkit import speech_to_text
from yandex_disk import get_user_token, save_expense_to_excel

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="a", 
                    format="%(asctime)s [%(levelname)s]: %(message)s")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Авторизация (упрощено, подробности опущены для MVP)
@dp.message_handler(commands=['login'])
async def login(message: types.Message):
    await message.reply("Авторизация больше не требуется, у вас уже есть доступ.")

# Основная обработка голосовых
@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    user_token = get_user_token(user_id)
    if not user_token:
        await message.reply("⚠️ Сначала авторизуйтесь через /login")
        return

    voice = await message.voice.get_file()
    ogg_data = await bot.download_file(voice.file_path)
    ogg_bytes = ogg_data.read()

    try:
        text = speech_to_text(ogg_bytes)
        await message.reply(f"📝 Распознано:\n{text}")

        # Суперпростое разбиение на сумму и категорию
        # Пример: "200 метро" -> сумма=200, категория=метро
        parts = text.split()
        if len(parts) >= 2 and parts[0].replace(",", "").replace(".", "").isdigit():
            amount = parts[0]
            category = " ".join(parts[1:])
        else:
            amount = text
            category = ""

        save_expense_to_excel(user_token, user_id, amount, category)
        await message.reply("✅ Расход сохранён в Excel на вашем Яндекс.Диске!")

    except Exception as e:
        logging.error(f"Ошибка при обработке голоса: {e}")
        await message.reply("❌ Ошибка при обработке голосового сообщения.")

# Старт
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
