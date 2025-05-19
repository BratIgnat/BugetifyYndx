import logging
import os
import io
import requests
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InputFile
from dotenv import load_dotenv
from pathlib import Path
from speechkit import speech_to_text
from yandex_disk import save_to_yandex_disk

env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)
print("DEBUG BOT_TOKEN:", os.getenv("BOT_TOKEN"))


# --- Читаем переменные окружения (systemd через EnvironmentFile)
BOT_TOKEN = os.environ['BOT_TOKEN']
YANDEX_API_KEY = os.environ['YANDEX_API_KEY']
YANDEX_CLIENT_ID = os.environ['YANDEX_CLIENT_ID']
YANDEX_CLIENT_SECRET = os.environ['YANDEX_CLIENT_SECRET']

# --- Инициализируем Telegram-бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

user_tokens = {}  # Временное хранилище токенов

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Я Budgetify — твой ассистент по учёту расходов.\n\n"
                         "Отправь мне голосовое сообщение с тратой, например:\n"
                         "250 метро\nили\n127 рублей 25 копеек шоколадка.\n\n"
                         "❗️ Чтобы сохранять расходы в Яндекс.Диск, нужно авторизоваться: /login")

@dp.message_handler(commands=['login'])
async def login_command(message: types.Message):
    oauth_url = generate_oauth_url()
    # Отправим как явную ссылку в HTML-режиме, чтобы Telegram не портил URL
    await message.answer(f"🔑 <b>Для авторизации перейдите по ссылке:</b>\n<a href=\"{oauth_url}\">Авторизоваться через Яндекс</a>", parse_mode="HTML")

# Генерация OAuth URL для пользователя

def generate_oauth_url():
    redirect_uri = 'https://oauth.yandex.ru/verification_code'
    scope = 'cloud_api:disk.app_folder'
    return (f"https://oauth.yandex.ru/authorize?response_type=code"
            f"&client_id={YANDEX_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}")

@dp.message_handler(commands=['code'])
async def code_command(message: types.Message):
    code = message.get_args()
    if not code:
        await message.answer("❗ Пожалуйста, введите код авторизации после команды. Пример: /code 1234567")
        return

    token_data = exchange_code_for_token(code)
    if 'access_token' in token_data:
        user_tokens[message.from_user.id] = token_data['access_token']
        await message.answer("✅ Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
    else:
        await message.answer("❌ Ошибка авторизации. Проверьте код и попробуйте снова.")

# Функция обмена кода на токен

def exchange_code_for_token(code):
    url = "https://oauth.yandex.ru/token"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': YANDEX_CLIENT_ID,
        'client_secret': YANDEX_CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    return response.json()

@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    await message.answer("🔄 Обрабатываю голосовое сообщение...")
    file_info = await bot.get_file(message.voice.file_id)
    file = await bot.download_file(file_info.file_path)
    ogg_data = file.read()

    text = speech_to_text(ogg_data)

    if text:
        await message.answer(f"📝 Распознанный текст: {text}")

        token = user_tokens.get(message.from_user.id)
        if token:
            filename = f"expense_{message.message_id}.txt"
            yandex_response = save_to_yandex_disk(filename, text, token)
            if yandex_response:
                await message.answer("☁️ Данные успешно сохранены в Яндекс.Диск.")
            else:
                await message.answer("⚠️ Не удалось сохранить в Яндекс.Диск.")
        else:
            await message.answer("❗ Сначала необходимо авторизоваться через /login")
    else:
        await message.answer("❌ Не удалось распознать речь. Попробуйте снова.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
