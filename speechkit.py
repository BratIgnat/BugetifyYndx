def speech_to_text(ogg_data):
    from pydub import AudioSegment
    from tempfile import NamedTemporaryFile

    IAM_TOKEN = os.getenv("YANDEX_IAM_TOKEN")
    FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

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
    headers = {
        "Authorization": f"Bearer {IAM_TOKEN}",
    }
    params = {
        "lang": "ru-RU",
        "folderId": FOLDER_ID,
    }

    response = requests.post(url, headers=headers, params=params, data=audio_bytes)
    response.raise_for_status()
    result = response.json()
    return result.get("result")
