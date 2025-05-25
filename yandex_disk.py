import os
import io
import re
import requests
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

TOKENS_DIR = "tokens"

def parse_amount_and_category(text):
    """
    Извлекает сумму (float) и категорию (str) из текста:
    "50 тысяч 43 копейки мороженое" -> (50000.43, "мороженое")
    "120 рублей еда" -> (120.00, "еда")
    "200.50 еда" -> (200.50, "еда")
    """
    original = text
    text = text.lower()
    text = text.replace('тысяч ', '000 ')
    text = text.replace('тысяча ', '000 ')
    text = text.replace('тысячи ', '000 ')
    # Если есть "руб", заменить на "рубль"
    text = re.sub(r'руб(лей|ля|ль)?', 'рубль', text)
    # Ищем сначала "число рубль"
    rub_match = re.search(r'(\d+[.,]?\d*)\s*рубль', text)
    rub = float(rub_match.group(1).replace(',', '.')) if rub_match else 0
    # Копейки
    kop_match = re.search(r'(\d+[.,]?\d*)\s*коп(еек|ейки|ей)?', text)
    kop = float(kop_match.group(1).replace(',', '.')) if kop_match else 0
    # Обработка простого формата: число в начале строки
    match_simple = re.match(r'^\s*(\d+[.,]?\d*)\s+(.+)$', text)
    if match_simple and rub == 0:
        rub = float(match_simple.group(1).replace(',', '.'))
        category = match_simple.group(2).strip()
    else:
        # Всё, что не "рубль" и не "копейка" — категория
        category = text
        category = re.sub(r'\d+[.,]?\d*\s*рубль', '', category)
        category = re.sub(r'\d+[.,]?\d*\s*коп(еек|ейки|ей)?', '', category)
        category = re.sub(r'\d+[.,]?\d*\s*', '', category)
        category = category.strip()
    amount = rub + kop/100
    return round(amount, 2), category

def get_token_path(user_id):
    return os.path.join(TOKENS_DIR, f"{user_id}.token")

def is_user_authenticated(user_id):
    return os.path.exists(get_token_path(user_id))

def get_auth_link(client_id):
    return (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&client_id={client_id}&scope=cloud_api:disk.app_folder"
    )

def set_auth_code(user_id, code, client_id, client_secret):
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    r = requests.post(url, data=data)
    if r.status_code == 200:
        with open(get_token_path(user_id), "w") as f:
            f.write(r.json()["access_token"])
        return True
    else:
        return False

def save_to_yadisk(user_id, recognized_text):
    token_path = get_token_path(user_id)
    if not os.path.exists(token_path):
        raise Exception("User not authenticated")
    with open(token_path) as f:
        token = f.read().strip()

    amount, category = parse_amount_and_category(recognized_text)

    # Имя файла на Я.Диске (каждому пользователю свой файл)
    filename = f"{user_id}.xlsx"

    # 1. Попробовать скачать файл с Я.Диска
    headers = {"Authorization": f"OAuth {token}"}
    get_file_url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path=app:{filename}"
    r = requests.get(get_file_url, headers=headers)
    if r.status_code == 200:
        file_url = r.json()["href"]
        file_content = requests.get(file_url).content
        wb = load_workbook(filename=io.BytesIO(file_content))
        ws = wb.active
    else:
        # Если файла нет — создаём новый
        wb = Workbook()
        ws = wb.active
        ws.append(["#", "Сумма", "Категория"])

    # 2. Добавляем новую строку
    next_id = ws.max_row  # С учётом шапки
    ws.append([next_id, amount, category])

    # 3. Сохраняем в байтовый поток
    excel_stream = io.BytesIO()
    wb.save(excel_stream)
    excel_stream.seek(0)

    # 4. Загружаем на Я.Диск (app: — папка приложения)
    upload_url = f"https://cloud-api.yandex.net/v1/disk/resources/upload?path=app:{filename}&overwrite=true"
    r = requests.get(upload_url, headers=headers)
    if r.status_code == 200:
        href = r.json()["href"]
        up = requests.put(href, files={"file": excel_stream})
        return up.status_code == 201 or up.status_code == 202
    else:
        raise Exception("Не удалось получить ссылку для загрузки файла")
