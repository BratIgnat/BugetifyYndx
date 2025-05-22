# ✅ bot.py — основной файл бота
import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text
from excel_writer import save_expense_to_excel
from yandex_disk import save_to_yandex_disk

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # если нужен

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Логгирование
logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a', 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("👋 Привет! Я Budgetify — ассистент по учёту расходов.\n\nОтправь мне голосовое сообщение с тратой, например:\n\n250 метро\nили\n127 рублей 25 копеек шоколадка.")


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    try:
        await message.reply("🔄 Обрабатываю голосовое сообщение...")

        file_info = await bot.get_file(message.voice.file_id)
        file = await bot.download_file(file_info.file_path)
        ogg_data = file.read()

        text = speech_to_text(ogg_data)
        if not text:
            await message.reply("Не удалось распознать речь. Попробуй ещё раз.")
            return

        await message.reply(f"📝 Распознано:\n{text}")

        save_expense_to_excel(user_id=message.from_user.id, text=text)
        save_to_yandex_disk(user_id=message.from_user.id)

    except Exception as e:
        logger.exception("Ошибка при обработке голоса")
        await message.reply("Произошла ошибка при обработке сообщения. Попробуй позже.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
