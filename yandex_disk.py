import os
import requests

APP_ID = os.getenv("YANDEX_CLIENT_ID")
APP_SECRET = os.getenv("YANDEX_CLIENT_SECRET")
TOKENS_DIR = "tokens"

def get_auth_link(user_id):
    return (
        f"https://oauth.yandex.ru/authorize?response_type=code"
        f"&client_id={APP_ID}&scope=cloud_api:disk.app_folder"
    )

def set_auth_code(user_id, code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
    }
    resp = requests.post("https://oauth.yandex.ru/token", data=data)
    resp.raise_for_status()

    os.makedirs(TOKENS_DIR, exist_ok=True)
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.token")
    with open(token_path, "w") as f:
        f.write(resp.json()["access_token"])

def is_user_authenticated(user_id):
    return os.path.exists(os.path.join(TOKENS_DIR, f"{user_id}.token"))

def save_to_yadisk(user_id, text):
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.token")
    with open(token_path, "r") as f:
        token = f.read().strip()

    headers = {"Authorization": f"OAuth {token}"}
    upload_link = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/upload",
        headers=headers,
        params={"path": "budgetify_data.txt", "overwrite": "true"},
    ).json()["href"]

    requests.put(upload_link, headers=headers, data=text.encode("utf-8"))
