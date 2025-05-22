import os
import requests

def save_to_yadisk(user_token: str, filename: str, csv_data: str):
    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    params = {
        "path": f"app:/budgetify/{filename}",
        "overwrite": "true"
    }
    headers = {"Authorization": f"OAuth {user_token}"}

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    upload_url = resp.json()["href"]

    upload_resp = requests.put(upload_url, files={"file": csv_data})
    upload_resp.raise_for_status()
