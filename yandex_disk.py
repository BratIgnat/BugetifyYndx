import os
import re
import io
import openpyxl
import requests
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv

load_dotenv()

# Папка с токенами пользователей
TOKENS_DIR = 'tokens'

def parse_amount_and_category(text):
    """
    Парсит сумму (число) и категорию из строки. Например:
    "50 тысяч 43 копейки монитор" -> 50000.43, "монитор"
    """
    text = text.lower().replace(",", ".").strip()
    rub_sum = 0
    kop_sum = 0

    # Находим рубли (возможно "тысяч" или "тыс." или просто число)
    rub_pattern = r"(\d+([.,]?\d+)?)(\s*тысяч[аи]?|\s*тыс\.?)?\s*(руб(лей|ль|ля|\.|)|р|руб\.)?"
    match_rub = re.search(rub_pattern, text)
    if match_rub:
        rub = match_rub.group(1)
        if "тысяч" in match_rub.group(0) or "тыс" in match_rub.group(0):
            rub_sum += float(rub) * 1000
        else:
            rub_sum += float(rub)
        text = text.replace(match_rub.group(0), "", 1)

    # Находим копейки
    kop_pattern = r"(\d+)(\s*коп(еек|ейки|\.|))"
    match_kop = re.search(kop_pattern, text)
    if match_kop:
        kop_sum += int(match_kop.group(1))
        text = text.replace(match_kop.group(0), "", 1)

    # Итоговая сумма
    if rub_sum or kop_sum:
        total = rub_sum + kop_sum / 100
        total = round(total, 2)
    else:
        total = ""

    category = text.strip()
    return total, category

def get_token(user_id):
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.token")
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            return f.read().strip()
    return None

def is_user_authenticated(user_id):
    return os.path.exists(os.path.join(TOKENS_DIR, f"{user_id}.token"))

def get_auth_link(client_id):
    # Возвращает ссылку для авторизации
    return f"https://oauth.yandex.ru/authorize?response_type=code&client_id={client_id}&scope=cloud_api:disk.app_folder"

def set_auth_code(user_id, code, client_id, client_secret):
    # Получает токен пользователя по коду авторизации
    url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if token:
        os.makedirs(TOKENS_DIR, exist_ok=True)
        with open(os.path.join(TOKENS_DIR, f"{user_id}.token"), "w") as f:
            f.write(token)
        return True
    return False

def save_to_yadisk(user_id, text):
    token = get_token(user_id)
    if not token:
        return False, "Пользователь не авторизован."

    # Парсим сумму и категорию
    amount, category = parse_amount_and_category(text)
    if not amount:
        amount = text  # fallback (на случай "просто категория")

    # Название файла (по user_id, либо любой уникальный)
    filename = f"{user_id}.xlsx"

    # Проверяем, существует ли файл на Я.Диске
    headers = {"Authorization": f"OAuth {token}"}
    file_path = f"app:/{filename}"

    # Скачиваем файл, если он есть
    resp = requests.get("https://cloud-api.yandex.net/v1/disk/resources/download", params={"path": file_path}, headers=headers)
    if resp.status_code == 200:
        url = resp.json()["href"]
        file_resp = requests.get(url)
        file_bytes = io.BytesIO(file_resp.content)
        wb = openpyxl.load_workbook(file_bytes)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.append(["#", "Сумма", "Категория"])  # Заголовки

    # Найти следующий номер строки
    next_row = ws.max_row + 1
    ws.append([next_row - 1, amount, category])

    # Сохраняем файл в BytesIO
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    # Загружаем на Я.Диск
    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    params = {
        "path": file_path,
        "overwrite": "true"
    }
    up_resp = requests.get(upload_url, headers=headers, params=params)
    up_url = up_resp.json()["href"]
    resp = requests.put(up_url, files={"file": file_stream})
    resp.raise_for_status()

    return True, "✅ Расход сохранён!"

