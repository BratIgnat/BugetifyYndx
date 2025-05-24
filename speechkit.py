# speechkit.py
from dotenv import load_dotenv
import os
import requests
from pydub import AudioSegment
from tempfile import NamedTemporaryFile

# 1) Подгружаем .env
load_dotenv()

YANDEX_API_KEY    = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID  = os.getenv("YANDEX_FOLDER_ID")      # из .env: YANDEX_FOLDER_ID=blgfvfqalleijjl280ov
assert YANDEX_API_KEY,   "YANDEX_API_KEY не задан!"
assert YANDEX_FOLDER_ID, "YANDEX_FOLDER_ID не задан!"

def speech_to_text(ogg_data: bytes) -> str | None:
    # 2) конвертация OGG→WAV
    with NamedTemporaryFile(suffix=".ogg") as ogg, NamedTemporaryFile(suffix=".wav") as wav:
        ogg.write(ogg_data); ogg.flush()
        audio = AudioSegment.from_ogg(ogg.name)
        audio.export(wav.name, format="wav")
        wav.flush()
        audio_bytes = wav.read() if False else open(wav.name, "rb").read()

    # 3) проверим, что bytes не пустые
    if not audio_bytes:
        raise RuntimeError("SpeechKit: audio_bytes пустой!")

    # 4) готовим запрос
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/octet-stream",   # обязательно!
    }
    params = {
        "lang":     "ru-RU",
        "folderId": YANDEX_FOLDER_ID,
    }

    # 5) отправляем и сразу распечатываем тело ответа (для дебага)
    resp = requests.post(url, headers=headers, params=params, data=audio_bytes)
    print(">> SpeechKit response status:", resp.status_code)
    print(">> SpeechKit response body:", resp.text)

    # 6) поднимаем ошибку, если не 200
    resp.raise_for_status()

    # 7) возвращаем результат
    return resp.json().get("result")
