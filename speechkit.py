import os
import requests
from tempfile import NamedTemporaryFile
from pydub import AudioSegment

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

def speech_to_text(ogg_data):
    with NamedTemporaryFile(suffix=".ogg", delete=True) as ogg_file:
        ogg_file.write(ogg_data)
        ogg_file.flush()

        audio = AudioSegment.from_ogg(ogg_file.name)

        with NamedTemporaryFile(suffix=".wav", delete=True) as wav_file:
            audio.export(wav_file.name, format="wav")
            wav_file.flush()

            with open(wav_file.name, "rb") as f:
                audio_bytes = f.read()

    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    params = {"lang": "ru-RU"}

    response = requests.post(url, headers=headers, params=params, data=audio_bytes)
    response.raise_for_status()
    return response.json().get("result")
