# bot.py
import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from dotenv import load_dotenv
from speechkit import speech_to_text
from yandex_disk import save_to_yadisk, is_user_authenticated, get_auth_link, set_auth_code

load_dotenv()
logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("\U0001F44B Привет! Я Budgetify — твой ассистент по учёту расходов.\n\n"
                        "Отправь мне голосовое сообщение с тратой, например:\n"
                        "250 метро\nили\n127 рублей 25 копеек шоколадка.\n\n"
                        "❗ Чтобы сохранять расходы в Яндекс.Диск, нужно авторизоваться: /login")

@dp.message_handler(commands=['login'])
async def cmd_login(message: types.Message):
    auth_link = get_auth_link()
    await message.reply(f"🔑 *Для авторизации перейдите по ссылке:*\n[Авторизоваться через Яндекс]({auth_link})",
                          parse_mode="Markdown")

@dp.message_handler(commands=['code'])
async def cmd_code(message: types.Message):
    code = message.get_args()
    user_id = message.from_user.id
    if set_auth_code(user_id, code):
        await message.reply("\u2705 Авторизация прошла успешно! Теперь можете отправлять голосовые сообщения с тратами.")
    else:
        await message.reply("\u274c Ошибка авторизации. Попробуйте снова или проверьте код.")

@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id

    if not is_user_authenticated(user_id):
        await message.reply("\u2757 Сначала авторизуйтесь через /login, чтобы я мог сохранять ваши траты на Яндекс.Диск.")
        return

    await message.reply("\ud83d\udcc5 Обрабатываю голосовое сообщение...")
    try:
        voice = await message.voice.get_file()
        ogg_data = await bot.download_file(voice.file_path)
        ogg_bytes = ogg_data.read()
        text = speech_to_text(ogg_bytes)

        if not text:
            raise ValueError("Пустой результат распознавания")

        await save_to_yadisk(user_id, text)
        await message.reply(f"\ud83d\udcc4 Распознано: {text}\n\n✅ Сохранено в Яндекс.Диск!")

    except Exception as e:
        logging.exception("Ошибка при обработке голоса")
        await message.reply("\u274c Не удалось обработать голосовое сообщение. Попробуйте ещё раз.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
