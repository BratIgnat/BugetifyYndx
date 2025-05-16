import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openpyxl import Workbook, load_workbook

from speechkit import recognize_ogg  # наша функция из speechkit.py

# ─────────── Загрузка переменных окружения ───────────

load_dotenv()  # прочитать .env
BOT_TOKEN      = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not YANDEX_API_KEY:
    raise RuntimeError("YANDEX_API_KEY не задан в .env")

# ───────────────── Общие настройки ─────────────────

EXCEL_FILE = "expenses.xlsx"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────── Excel-функции ──────────────────

def init_excel_file():
    """Создает файл Excel с заголовками, если его нет."""
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.append(["Дата", "Сумма", "Категория", "Источник", "Позиции"])
        wb.save(EXCEL_FILE)

def append_to_excel(amount, category, source="Голос", items="-"):
    """Добавляет новую строку в Excel."""
    init_excel_file()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        amount,
        category,
        source,
        items
    ])
    wb.save(EXCEL_FILE)

# ─────────────────── Командные хендлеры ──────────────────

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/add сумма категория"""
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Формат: /add сумма категория")
            return
        amount = float(context.args[0].replace(",", "."))
        category = " ".join(context.args[1:])
        append_to_excel(amount, category, source="Команда")
        await update.message.reply_text(f"✅ Добавлено: {amount} — {category}")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: сумма должна быть числом.")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def edit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/edit_amount новая_сумма — меняет сумму последней записи"""
    try:
        if len(context.args) != 1:
            await update.message.reply_text("Формат: /edit_amount новая_сумма")
            return
        new_amount = float(context.args[0].replace(",", "."))
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        ws.cell(row=ws.max_row, column=2).value = new_amount
        wb.save(EXCEL_FILE)
        await update.message.reply_text(f"✅ Сумма обновлена на {new_amount}")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/edit_category новая_категория — меняет категорию последней записи"""
    try:
        if not context.args:
            await update.message.reply_text("Формат: /edit_category новая_категория")
            return
        new_category = " ".join(context.args)
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        ws.cell(row=ws.max_row, column=3).value = new_category
        wb.save(EXCEL_FILE)
        await update.message.reply_text(f"✅ Категория обновлена на: {new_category}")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ─────────────────── Обработка голосовых ──────────────────

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовое сообщение, распознаёт и добавляет трату."""
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_path = f"voice_{update.message.message_id}.ogg"
        await file.download_to_drive(file_path)

        text = recognize_ogg(file_path)  # распознаём через speechkit.py
        logger.info(f"Распознан текст: {text!r}")

        # Парсим сумму и категорию
        words = text.strip().split()
        amount = None
        category = None
        for i, w in enumerate(words):
            try:
                amount = float(w.replace(",", "."))
                category = " ".join(words[i+1:]) or "Без категории"
                break
            except ValueError:
                continue
        if amount is None:
            raise ValueError("Не удалось найти сумму в распознанном тексте.")

        append_to_excel(amount, category, source="Голос")
        await update.message.reply_text(f"✅ Добавлено: {amount} — {category}")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"❌ Ошибка при обработке голоса: {e}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

# ─────────────────── Запуск бота ──────────────────

def main():
    init_excel_file()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("edit_amount", edit_amount))
    app.add_handler(CommandHandler("edit_category", edit_category))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))

    print("Бот запущен! Ожидаю сообщений...")
    app.run_polling()

if __name__ == "__main__":
    main()
