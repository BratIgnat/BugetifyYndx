import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
)
from speechkit import recognize_ogg

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')  # <-- для SpeechKit (НЕ IAM!)
YANDEX_CLIENT_ID = os.getenv('YANDEX_CLIENT_ID')
YANDEX_CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET')

logging.basicConfig(level=logging.INFO)

WAITING_OAUTH_CODE = 1
user_tokens = {}

WELCOME = (
    "👋 Привет! Я Budgetify — твой ассистент по учёту расходов.\n\n"
    "Отправь мне голосовое сообщение с тратой, например:\n"
    "`250 метро`\nили\n`127 рублей 25 копеек шоколадка`.\n\n"
    "❗ Чтобы сохранять расходы в Яндекс.Диск, нужно авторизоваться: /login"
)
HELP = (
    "📝 *Справка по командам:*\n"
    "/start — приветствие\n"
    "/login — подключить Яндекс.Диск\n"
    "/excel — получить ссылку на свою таблицу\n"
    "/last — последние расходы\n"
    "/help — помощь"
)
LOGIN_MSG = (
    "🔑 Для работы с Яндекс.Диском, пожалуйста, авторизуйтесь:\n\n"
    "1. Перейдите по ссылке: {url}\n"
    "2. Скопируйте код авторизации\n"
    "3. Отправьте мне этот код"
)
SUCCESS_LOGIN = "✅ Готово! Я могу сохранять ваши расходы на ваш Яндекс.Диск."
NEED_LOGIN = "⚠️ Для этой операции нужна авторизация через Яндекс. Введите команду /login"
ADDED_ROW = "✅ Записал: *{amount}* — {category}\n📊 Всё хранится на вашем Яндекс.Диске."
EXCEL_LINK_MSG = "🗂 Вот ссылка на вашу таблицу: {link}"

def get_oauth_url():
    return (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&client_id={YANDEX_CLIENT_ID}&"
        f"scope=cloud_api:disk.app_folder"
    )

def exchange_code_for_token(code):
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": YANDEX_CLIENT_ID,
        "client_secret": YANDEX_CLIENT_SECRET,
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        logging.error(f"OAuth error: {e} / {response.text if 'response' in locals() else ''}")
        return None

def get_file_link(user_id, token):
    file_path = f"app:/Budgetify_{user_id}.csv"
    url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path={file_path}"
    headers = {"Authorization": f"OAuth {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()['href']
    return None

def append_row_to_disk(user_id, token, row):
    file_path = f"Budgetify_{user_id}.csv"
    # Скачиваем существующий файл (если есть)
    url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path=app:/{file_path}"
    headers = {"Authorization": f"OAuth {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        download_url = resp.json()['href']
        csv_data = requests.get(download_url).content.decode()
    else:
        # Если файла нет, создаём заголовок
        csv_data = "Дата,Сумма,Категория,Источник\n"
    # Добавляем новую строку
    from datetime import datetime
    csv_data += f"{datetime.now().strftime('%Y-%m-%d %H:%M')},{row[0]},{row[1]},Голос\n"
    # Загружаем обратно
    upload_url_resp = requests.get(
        f"https://cloud-api.yandex.net/v1/disk/resources/upload?path=app:/{file_path}&overwrite=true",
        headers=headers)
    if upload_url_resp.status_code == 200:
        upload_url = upload_url_resp.json()['href']
        requests.put(upload_url, data=csv_data.encode())
        return True
    return False

def parse_text(text):
    import re
    text = text.replace(",", ".")
    regex = r"(\d+)[\s,]*(?:руб[а-я]*)?[\s,]*(?:(\d+)[\s,]*копеек?)?\s*(.*)"
    match = re.match(regex, text, re.I)
    if match:
        rub = float(match.group(1))
        kop = float(match.group(2)) / 100 if match.group(2) else 0
        amount = round(rub + kop, 2)
        category = match.group(3).strip() if match.group(3) else "Без категории"
        return amount, category
    parts = text.split()
    for i, word in enumerate(parts):
        try:
            amount = float(word)
            category = " ".join(parts[i + 1:]) or "Без категории"
            return amount, category
        except:
            continue
    raise ValueError("Не удалось найти сумму!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode="Markdown")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = get_oauth_url()
    await update.message.reply_text(LOGIN_MSG.format(url=url), parse_mode="Markdown")
    return WAITING_OAUTH_CODE

async def oauth_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id
    token = exchange_code_for_token(code)
    if token:
        user_tokens[user_id] = token
        await update.message.reply_text(SUCCESS_LOGIN)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Ошибка авторизации. Попробуйте ещё раз: /login")
        return WAITING_OAUTH_CODE

async def excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = user_tokens.get(user_id)
    if not token:
        await update.message.reply_text(NEED_LOGIN)
        return
    link = get_file_link(user_id, token)
    if link:
        await update.message.reply_text(EXCEL_LINK_MSG.format(link=link))
    else:
        await update.message.reply_text("Не удалось получить ссылку на файл. Попробуйте записать хотя бы одну трату!")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = user_tokens.get(user_id)
    if not token:
        await update.message.reply_text(NEED_LOGIN)
        return

    file = await context.bot.get_file(update.message.voice.file_id)
    file_path = f"voice_{update.message.message_id}.ogg"
    await file.download_to_drive(file_path)

    try:
        text = recognize_ogg(file_path, YANDEX_API_KEY)
        amount, category = parse_text(text)
        row = [amount, category]
        append_row_to_disk(user_id, token, row)
        await update.message.reply_text(ADDED_ROW.format(amount=amount, category=category), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = user_tokens.get(user_id)
    if not token:
        await update.message.reply_text(NEED_LOGIN)
        return
    await update.message.reply_text("⏳ Эта команда в разработке.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("login", login)],
        states={WAITING_OAUTH_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, oauth_code)]},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("excel", excel))
    app.add_handler(CommandHandler("last", last))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
