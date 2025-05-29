import os
import requests
import io
import openpyxl
import re

TOKENS_DIR = "tokens"
if not os.path.exists(TOKENS_DIR):
    os.makedirs(TOKENS_DIR)

def get_auth_link(user_id):
    client_id = os.getenv("YANDEX_CLIENT_ID")
    return (
        f"https://oauth.yandex.ru/authorize?response_type=code&client_id={client_id}&scope=cloud_api:disk.app_folder"
    )

def set_auth_code(user_id, code):
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

import re

def parse_expense(text):
    """
    Извлекает сумму из текста (удаляет все формы 'руб', 'р', 'коп', 'к'), возвращает (сумма: float, категория: str).
    Примеры:
    - '1000 р такси' -> (1000.0, 'такси')
    - '50 рублей 30 копеек еда' -> (50.3, 'еда')
    - '25000 аренда' -> (25000.0, 'аренда')
    - '99 копеек' -> (0.99, '')
    """

    text = text.lower()
    # Удалить все валютные слова (любыми формами)
    text_clean = re.sub(r"\b(руб(ль|лей|ля|ли|лем|лям|лями)?|р|коп(ейка|ейки|еек|ейку|ейкой|ейками)?|к)\b", "", text)
    text_clean = re.sub(r"\s+", " ", text_clean).strip()
    
    # Сначала ищем пары "число число" (пример: 100 30 -> 100.30)
    matches = re.findall(r"\d+", text_clean)
    amount = 0.0
    if len(matches) >= 2 and int(matches[1]) < 100:
        amount = float(matches[0]) + float(matches[1]) / 100
        # Остальное после второй цифры — категория
        category_start = text_clean.find(matches[1]) + len(matches[1])
        category = text_clean[category_start:].strip()
        return amount, category

    # Если есть только одно число — это сумма
    if len(matches) >= 1:
        amount = float(matches[0])
        category_start = text_clean.find(matches[0]) + len(matches[0])
        category = text_clean[category_start:].strip()
        return amount, category

    # Не найдено ни одного числа
    return 0.0, text_clean

def save_to_yadisk(user_id, text):
    token = get_user_token(user_id)
    if not token:
        raise Exception("User not authenticated")
    file_name = f"{user_id}.xlsx"
    remote_path = f"app:/{file_name}"

    amount, category = parse_expense(text)
    if amount is None or category is None or category == "":
        raise Exception("Некорректный формат расходов. Пожалуйста, попробуйте ещё раз.")

    # 2. Скачиваем существующий excel (если есть)
    headers = {"Authorization": f"OAuth {token}"}
    download_url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    params_download = {"path": remote_path}
    r2 = requests.get(download_url, params=params_download, headers=headers)

    if r2.status_code == 200 and "href" in r2.json():
        download_href = r2.json()["href"]
        file_content = requests.get(download_href).content
        workbook = openpyxl.load_workbook(io.BytesIO(file_content))
        sheet = workbook.active
    else:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["#", "Сумма", "Категория"])

    idx = sheet.max_row
    sheet.append([idx, amount, category])

    # 3. Сохраняем excel-файл в память
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # 4. Получаем upload ссылку
    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    params = {"path": remote_path, "overwrite": "true"}
    r = requests.get(upload_url, params=params, headers=headers)
    href = r.json().get("href")
    if not href:
        raise Exception("Не удалось получить ссылку для загрузки файла на Яндекс.Диск.")

    # 5. Загружаем обновлённый файл
    requests.put(href, data=output.getvalue())
