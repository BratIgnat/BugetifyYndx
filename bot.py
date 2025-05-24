import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InputFile
from dotenv import load_dotenv
from speechkit import speech_to_text
from yandex_disk import save_to_yadisk, is_user_authenticated, get_auth_link, set_auth_code

load_dotenv()
BOT_TOKEN = os.environ["BOT_TOKEN"]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()  # Вывод в консоль!

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("👋 Привет! Я Budgetify — твой ассистент по учёту расходов.\n\n"
                        "Отправь мне голосовое сообщение с тратой, например:\n"
                        "250 метро\n"
                        "или\n"
                        "127 рублей 25 копеек шоколадка.\n\n"
                        "❗ Чтобы сохранять расходы в Яндекс.Диск, нужно авторизоваться: /login")

@dp.message_handler(commands=["login"])
async def login(message: types.Message):
    link = get_auth_link(message.from_user.id)
    await message.reply(f"🔑 Для авторизации перейдите по ссылке:\n[Авторизоваться через Яндекс]({link})", parse_mode="Markdown")

@dp.message_handler(commands=["code"])
async def code(message: types.Message):
    try:
        code = message.text.split()[1]
        set_auth_code(message.from_user.id, code)
        await message.reply("✅ Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
    except Exception:
        await message.reply("⚠️ Ошибка: пришлите код в формате: /code <полученный_код>")

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    try:
        await message.reply("🎙 Обрабатываю голосовое сообщение...")

        file_info = await bot.get_file(message.voice.file_id)
        ogg_file = await bot.download_file(file_info.file_path)
        ogg_data = ogg_file.read()

        text = speech_to_text(ogg_data)
        if not text:
            await message.reply("⚠️ Не удалось распознать речь.")
            return

        await message.reply(f"🧾 Распознано:\n{text}")

        if is_user_authenticated(message.from_user.id):
            save_to_yadisk(message.from_user.id, text)
            await message.reply("💾 Данные сохранены на Яндекс.Диск.")
        else:
            await message.reply("⚠️ Для сохранения данных авторизуйтесь через /login")
    except Exception as e:
        logging.error(f"Ошибка при обработке голоса: {e}")
        await message.reply("⚠️ Ошибка при обработке голосового сообщения.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
