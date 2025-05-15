# bot.py
import os
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from speechkit import recognize_ogg
from excel_writer import write_to_excel




BOT_TOKEN = "7621914998:AAFgJ2oQWs5BnX3PdCyqYDQUz4wVmq46Cqs"
YANDEX_IAM_TOKEN = "y0__xCwze6jBRjB3RMg87n1kRMCcNMWjN7PrhtHmWk7yguUOJTdJg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь голосовое с суммой и категорией. Например: '500 продукты'")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        file_path = tmp.name
    await file.download_to_drive(file_path)

    text = recognize_ogg(file_path, YANDEX_IAM_TOKEN)
    os.remove(file_path)

    if not text:
        await update.message.reply_text("Не удалось распознать голосовое сообщение 😢")
        return

    await update.message.reply_text(f"Распознанный текст: {text}")

    try:
        amount, *category_words = text.strip().split()
        amount = int(amount)
        category = " ".join(category_words)
        write_to_excel(amount, category)
        await update.message.reply_text(f"Записано в таблицу: {amount} руб — {category}")
    except Exception as e:
        print("Ошибка при обработке:", e)
        await update.message.reply_text("Не удалось обработать сообщение. Скажи: '500 категория'")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("Бот запущен!")
    app.run_polling()
