import os
import requests
import json

TOKENS_DIR = "tokens"
if not os.path.exists(TOKENS_DIR):
    os.makedirs(TOKENS_DIR)

def get_auth_link(user_id):
    client_id = os.getenv("YANDEX_CLIENT_ID")
    return (
        f"https://oauth.yandex.ru/authorize?response_type=code&client_id={client_id}&scope=cloud_api:disk.app_folder"
    )

def set_auth_code(user_id, code):
    # Получаем токен пользователя через API Яндекса
    client_id = os.getenv("YANDEX_CLIENT_ID")
    client_secret = os.getenv("YANDEX_CLIENT_SECRET")
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    r = requests.post(url, data=data)
    if r.status_code == 200:
        token = r.json().get("access_token")
        with open(f"{TOKENS_DIR}/{user_id}.token", "w") as f:
            f.write(token)
        return True
    return False

def is_user_authenticated(user_id):
    return os.path.exists(f"{TOKENS_DIR}/{user_id}.token")

def get_user_token(user_id):
    try:
        with open(f"{TOKENS_DIR}/{user_id}.token", "r") as f:
            return f.read().strip()
    except Exception:
        return None

def save_to_yadisk(user_id, text):
    token = get_user_token(user_id)
    if not token:
        raise Exception("User not authenticated")
    file_name = f"{user_id}.txt"
    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    params = {"path": f"app:/{file_name}", "overwrite": "true"}
    headers = {"Authorization": f"OAuth {token}"}
    # Get upload link
    r = requests.get(url, params=params, headers=headers)
    href = r.json().get("href")
    if not href:
        raise Exception("Не удалось получить ссылку для загрузки файла на Яндекс.Диск.")
    # Read old content if exists, append new line
    old_data = ""
    download_url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    params_download = {"path": f"app:/{file_name}"}
    r2 = requests.get(download_url, params=params_download, headers=headers)
    if r2.status_code == 200 and "href" in r2.json():
        download_href = r2.json()["href"]
        resp = requests.get(download_href)
        old_data = resp.text
    # Append
    new_data = (old_data + "\n" + text).strip()
    requests.put(href, data=new_data.encode("utf-8"))
