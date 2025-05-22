import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я Budgetify — твой ассистент по учёту расходов.\n\n"
                         "Отправь мне голосовое сообщение с тратой, например:\n"
                         "250 метро\nили\n127 рублей 25 копеек шоколадка.")


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    await message.reply("🎙 Обрабатываю голосовое сообщение...")

    voice = await message.voice.get_file()
    ogg_file = await bot.download_file(voice.file_path)
    ogg_data = ogg_file.read()

    try:
        text = speech_to_text(ogg_data)
        if text:
            await message.reply(f"📝 Распознано:
{text}")
        else:
            await message.reply("😕 Не удалось распознать речь.")
    except Exception as e:
        logging.exception("Ошибка при обработке голоса")
        await message.reply("⚠️ Произошла ошибка при распознавании.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
