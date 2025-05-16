import os
import requests
import logging

# Подхватываем API-ключ из .env
from dotenv import load_dotenv
load_dotenv()
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

if not YANDEX_API_KEY:
    raise RuntimeError("YANDEX_API_KEY не задан в переменных окружения")

# Конфигурируем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL для синхронного распознавания
STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

def recognize_ogg(file_path: str) -> str:
    """
    Распознаёт русский текст из ogg-файла через Yandex SpeechKit.
    Возвращает результат распознавания (строку).
    """
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    params = {
        "lang": "ru-RU",
        "profanityFilter": False,
        "folderId": os.getenv("YANDEX_FOLDER_ID", ""),  # если у вас указан Folder ID
    }

    logger.info(f"Отправка запроса в SpeechKit: {file_path}")
    with open(file_path, "rb") as audio_file:
        resp = requests.post(
            STT_URL,
            headers=headers,
            params=params,
            data=audio_file
        )

    # Проверка статуса
    if resp.status_code != 200:
        logger.error(f"Yandex SpeechKit HTTP {resp.status_code}: {resp.text}")
        resp.raise_for_status()

    result = resp.json()
    if result.get("error_code", 0) != 0:
        msg = result.get("error_message", "Unknown error")
        logger.error(f"Yandex SpeechKit error: {result!r}")
        raise RuntimeError(f"SpeechKit: {msg}")

    text = result.get("result", "")
    logger.info(f"Распознано: {text!r}")
    return text
