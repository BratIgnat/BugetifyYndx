# ✅ yandex_disk.py — загрузка Excel-файла пользователя на Яндекс.Диск
import os
import requests
from dotenv import load_dotenv

load_dotenv()
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")


def save_to_yandex_disk(user_id):
    filename = f"data/{user_id}.xlsx"
    if not os.path.exists(filename):
        return

    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    disk_path = f"app/{user_id}.xlsx"
    params = {"path": disk_path, "overwrite": "true"}

    r = requests.get(upload_url, headers=headers, params=params)
    r.raise_for_status()
    upload_href = r.json().get("href")

    with open(filename, "rb") as f:
        upload = requests.put(upload_href, files={"file": f})
        upload.raise_for_status()
