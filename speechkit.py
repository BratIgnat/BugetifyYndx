# speechkit.py
import requests
import base64

def recognize_ogg(file_path, iam_token):
    with open(file_path, "rb") as f:
        data = f.read()

    base64_audio = base64.b64encode(data).decode("utf-8")

    body = {
        "config": {
            "specification": {
                "languageCode": "ru-RU"
            }
        },
        "audio": {
            "content": base64_audio
        }
    }

    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
        headers=headers,
        json=body
    )

    if response.status_code == 200:
        return response.json().get("result", "")
    else:
        print("Yandex SpeechKit error:", response.text)
        return None