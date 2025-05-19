import requests


def save_to_yandex_disk(filename, content, token):
    """
    Сохраняет текстовый файл в папку "Budgetify" на Яндекс.Диске пользователя через OAuth-токен.
    """
    # 1. Проверим, существует ли папка Budgetify
    folder_url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {token}"}

    requests.put(folder_url, headers=headers, params={"path": "app:/Budgetify"})

    # 2. Получим URL для загрузки файла
    upload_url_resp = requests.get(folder_url + "/upload", headers=headers, params={
        "path": f"app:/Budgetify/{filename}",
        "overwrite": "true"
    })

    if upload_url_resp.status_code != 200:
        print("Ошибка при получении ссылки для загрузки:", upload_url_resp.text)
        return False

    upload_url = upload_url_resp.json().get("href")

    # 3. Загрузим файл
    upload_resp = requests.put(upload_url, data=content.encode("utf-8"))
    if upload_resp.status_code != 201:
        print("Ошибка при загрузке файла:", upload_resp.text)
        return False

    return True
