import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Эта строка должна быть в самом начале!

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
    token_path = f'tokens/{user_id}.token'
    if not os.path.exists(token_path):
        print(f'[ERROR] Токен для user_id={user_id} не найден')
        return False

    with open(token_path) as f:
        token = f.read().strip()

    headers = {'Authorization': f'OAuth {token}'}
    params = {
        'path': f'app:/budgetify/{user_id}.txt',
        'overwrite': 'true'
    }
    url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"[ERROR] Ошибка при запросе href: {response.status_code} {response.text}")
        return False

    href = response.json().get('href')
    if not href:
        print(f"[ERROR] В ответе Я.Диска нет href! Ответ: {response.json()}")
        return False

    response2 = requests.put(href, data=text.encode('utf-8'))
    if response2.status_code not in [201, 202]:
        print(f"[ERROR] Ошибка при загрузке файла: {response2.status_code} {response2.text}")
        return False

    return True
