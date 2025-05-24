# speechkit.py
from dotenv import load_dotenv
import os
import requests

load_dotenv()

YANDEX_API_KEY   = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

def speech_to_text(ogg_data: bytes) -> str | None:
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type":  "audio/ogg; codecs=opus",
    }
    params = {
        "lang":     "ru-RU",
        "folderId": YANDEX_FOLDER_ID,
    }

    resp = requests.post(url, headers=headers, params=params, data=ogg_data)
    print(">> status:", resp.status_code)
    print(">> body:  ", resp.text)
    resp.raise_for_status()
    return resp.json().get("result")
