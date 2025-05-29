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
    Парсит строку с суммой и категорией. Удаляет все валюты ('руб', 'р', 'коп', 'к').
    Возвращает (float, категория) либо (None, None).
    """
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)

    # 1. Найти сумму с копейками: 1000 рублей 41 копейка проезд / 350 48 к вода
    money_pattern = (
        r'(?P<amount>\d+[.,]?\d*)'                       # сумма (целое/дробное)
        r'(?:\s*(?:руб(?:ль|лей|ля)?|р)\b)?'             # слово "рубль" (необязательно)
        r'(?:\s*(?P<kop>\d{1,2})\s*(?:коп(?:ейка|еек|ейки)?|к)\b)?' # "копейки" (опц)
        r'(?:\s+)?(?P<category>.+)?'                     # категория (всё остальное)
    )

    # 2. Попробовать "Категория СУММА КОПЕЙКИ"
    match = re.match(r'^(.+?)\s+(\d+[.,]?\d*)(?:\s*(?:руб(?:ль|лей|ля)?|р))?(?:\s*(\d{1,2})\s*(?:коп(?:ейка|еек|ейки)?|к))?$', text)
    if match:
        category = match.group(1).strip()
        rub = match.group(2).replace(',', '.')
        kop = match.group(3) or '0'
        try:
            amount = float(rub) + float(kop)/100
        except Exception:
            return None, None
        if not category or category in ['рубль', 'рублей', 'р', 'копейка', 'копеек', 'к']:
            return None, None
        return amount, category

    # 3. Попробовать "СУММА КОПЕЙКИ Категория"
    match = re.match(money_pattern, text)
    if match:
        rub = match.group('amount').replace(',', '.')
        kop = match.group('kop') or '0'
        category = (match.group('category') or '').strip()
        try:
            amount = float(rub) + float(kop)/100
        except Exception:
            return None, None
        # Если нет категории — ошибка
        if not category or category in ['рубль', 'рублей', 'р', 'копейка', 'копеек', 'к']:
            return None, None
        return amount, category

    # 4. Попробовать просто "СУММА Категория"
    match = re.match(r'^(\d+[.,]?\d*)\s+(.+)$', text)
    if match:
        rub = match.group(1).replace(',', '.')
        category = match.group(2).strip()
        try:
            amount = float(rub)
        except Exception:
            return None, None
        if not category or category in ['рубль', 'рублей', 'р', 'копейка', 'копеек', 'к']:
            return None, None
        return amount, category

    # 5. Попробовать "Категория СУММА"
    match = re.match(r'^(.+?)\s+(\d+[.,]?\d*)$', text)
    if match:
        category = match.group(1).strip()
        rub = match.group(2).replace(',', '.')
        try:
            amount = float(rub)
        except Exception:
            return None, None
        if not category or category in ['рубль', 'рублей', 'р', 'копейка', 'копеек', 'к']:
            return None, None
        return amount, category

    # 6. Ничего не распознано или сумма/категория некорректна
    return None, None

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
