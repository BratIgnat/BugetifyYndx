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

def parse_expense(text):
    """
    Парсит строку типа '200 р 53 к кукуруза', 'подушка 750 р 42 к', '350 к вода', 'молоко 28 рублей' и др.
    Возвращает (float сумма, категория) или (None, None)
    """

    # Унификация: заменить длинные слова, убрать двойные пробелы и привести к нижнему регистру
    text = text.lower()
    text = text.replace("рублей", "р").replace("рубль", "р").replace("руб", "р")
    text = text.replace("копеек", "к").replace("копейки", "к").replace("копейка", "к").replace("коп", "к")
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text).strip()

    # Вариант 1: сумма в начале ("200 р 53 к кукуруза")
    match = re.match(r"(?P<rub>\d+)\s*р?\s*(?P<kop>\d{1,2})?\s*к?\s*(?P<cat>.+)", text)
    if match:
        rub = int(match.group("rub"))
        kop = int(match.group("kop") or 0)
        amount = rub + kop / 100
        category = match.group("cat").strip()
        return amount, category

    # Вариант 2: категория в начале ("подушка 750 р 42 к", "молоко 28 р", "молоко 28")
    match = re.match(r"(?P<cat>.+?)\s+(?P<rub>\d+)\s*р?\s*(?P<kop>\d{1,2})?\s*к?$", text)
    if match:
        rub = int(match.group("rub"))
        kop = int(match.group("kop") or 0)
        amount = rub + kop / 100
        category = match.group("cat").strip()
        return amount, category

    # Вариант 3: только копейки ("50 к мороженое")
    match = re.match(r"(?P<kop>\d{1,2})\s*к\s*(?P<cat>.+)", text)
    if match:
        kop = int(match.group("kop"))
        amount = kop / 100
        category = match.group("cat").strip()
        return amount, category

    # Вариант 4: просто число и категория ("301 мороженое" или "мороженое 301")
    match = re.match(r"(\d+(?:[.,]\d{1,2})?)\s+(.+)", text)
    if match:
        try:
            amount = float(match.group(1).replace(',', '.'))
        except Exception:
            amount = None
        category = match.group(2).strip()
        if amount is not None:
            return amount, category

    match = re.match(r"(.+?)\s+(\d+(?:[.,]\d{1,2})?)$", text)
    if match:
        category = match.group(1).strip()
        try:
            amount = float(match.group(2).replace(',', '.'))
        except Exception:
            amount = None
        if amount is not None:
            return amount, category

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
