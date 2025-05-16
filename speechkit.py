# speechkit.py
import os
import requests

API_KEY = os.getenv("YANDEX_API_KEY")
URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"

headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json",
}

def recognize_ogg(file_path: str) -> str:
    # Загружаем аудио в Yandex
    with open(file_path, "rb") as f:
        data = {
            "config": {
                "specification": {
                    "languageCode": "ru-RU",
                    "profanityFilter": False
                }
            },
            "audio": {
                "content": f.read().decode("ISO-8859-1")
            }
        }
        resp = requests.post(URL, headers=headers, json=data)
    resp.raise_for_status()
    result = resp.json()
    # ...далее извлечение текста из result["response"]["chunks"][...]["alternatives"][0]["text"]
    return result_text
