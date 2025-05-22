import requests
import os
from pydub import AudioSegment
from tempfile import NamedTemporaryFile

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

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    response = requests.post(
        "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
        headers=headers,
        params={"lang": "ru-RU"},
        data=audio_bytes,
    )
    response.raise_for_status()
    return response.json().get("result")
