import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

# ───── Загрузка переменных окружения ─────
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# --- КОСТЫЛЬ: жёстко укажи client_id для OAuth Яндекс.Диска ---
# !! Временно: подставь свой актуальный client_id вместо 'ВАШ_CLIENT_ID'
YANDEX_CLIENT_ID = "644cc9ff80d54de8bea23a6e5b6d13e4"
YANDEX_CLIENT_SECRET = os.getenv('YANDEX_CLIENT_SECRET')

logging.basicConfig(level=logging.INFO)

# ───── Пример команды для теста OAuth ссылки ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth_url = (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&client_id={YANDEX_CLIENT_ID}&scope=cloud_api:disk.app_folder"
    )
    await update.message.reply_text(f"Ссылка для авторизации:\n{auth_url}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    main()
