import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ContentType
from speechkit import speech_to_text

# === НАСТРОЙКА ЛОГИРОВАНИЯ ===
LOG_PATH = '/home/brotherignat/BugetifyYndx/bot.log'
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,  # Меняй на DEBUG для подробностей
    format='%(asctime)s %(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Логирование необработанных исключений (чтобы ничего не терялось!)
import sys
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

# === БОТ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    logging.info(f"Пользователь {message.from_user.id} начал работу с ботом.")
    await message.reply("Привет! Я Budgetify бот. Пришли голосовое сообщение или чек.")

@dp.message_handler(content_types=ContentType.VOICE)
async def handle_voice(message: types.Message):
    try:
        logging.info(f"Получено голосовое сообщение от {message.from_user.id}")
        voice = message.voice
        ogg_data = await voice.download(destination=bytes)
        # Используй свою функцию speech_to_text из speechkit.py
        text = speech_to_text(ogg_data)
        await message.reply(f"Текст из голосового: {text}")
        logging.info(f"Распознано: {text}")
    except Exception as e:
        logging.error("Ошибка при обработке голосового сообщения", exc_info=True)
        await message.reply("Ошибка при обработке голосового сообщения.")

@dp.message_handler(content_types=ContentType.PHOTO)
async def handle_photo(message: types.Message):
    try:
        logging.info(f"Получено фото от {message.from_user.id}")
        # Можно добавить обработку чеков тут (оставь заглушку или логику по своему сценарию)
        await message.reply("Спасибо, фото получено! (Обработка чеков будет реализована)")
    except Exception as e:
        logging.error("Ошибка при обработке фото", exc_info=True)
        await message.reply("Ошибка при обработке фото.")

if __name__ == "__main__":
    logging.info("Запуск BudgetifyBot!")
    executor.start_polling(dp, skip_updates=True)
