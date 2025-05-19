import requests
import uuid
import os
from pydub import AudioSegment
from tempfile import NamedTemporaryFile

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")  # необязательно, если SpeechKit IAM


def speech_to_text(ogg_data):
    """
    Преобразует ogg-файл (байты) в текст с помощью Yandex SpeechKit.
    """
    # Сохраняем ogg временно и конвертируем в wav
    with NamedTemporaryFile(suffix=".ogg", delete=True) as ogg_file:
        ogg_file.write(ogg_data)
        ogg_file.flush()

        audio = AudioSegment.from_ogg(ogg_file.name)

        with NamedTemporaryFile(suffix=".wav", delete=True) as wav_file:
            audio.export(wav_file.name, format="wav")
            wav_file.flush()

            # Читаем содержимое wav-файла
            with open(wav_file.name, "rb") as f:
                audio_bytes = f.read()

    # Формируем запрос к Yandex SpeechKit
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    params = {
        "lang": "ru-RU",
        # "folderId": FOLDER_ID,  # если требуется
    }

    response = requests.post(url, headers=headers, params=params, data=audio_bytes)
    response.raise_for_status()

    result = response.json()
    return result.get("result")
