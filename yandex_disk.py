import os
import requests
import io
import openpyxl
import re
from datetime import datetime

TOKENS_DIR = "tokens"
if not os.path.exists(TOKENS_DIR):
    os.makedirs(TOKENS_DIR)

class ExpenseParseError(Exception):
    """Кастомное исключение для ошибок парсинга и валидации расходов."""
    pass

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
    Корректно разбирает строки типа 'подушка 750 рублей 42 копейки' → (750.42, 'подушка')
    Работает и с '1000 р еда' → (1000.0, 'еда'), и с 'еда 1000 р' → (1000.0, 'еда')
    """
    original_text = text.lower()

    # Для парсинга чисел (с копейками) ищем все числа и валюты
    pattern = r"(\d+[.,]?\d*)\s*(руб(ль|лей|ля|ли|лем|лям|лями)?|р)?(\s*\d{1,2}\s*(коп(ейка|ейки|еек|ейку|ейкой|ейками)?|к)?)?"
    matches = list(re.finditer(pattern, original_text, flags=re.IGNORECASE))
    
    amount = 0.0
    if matches:
        for match in matches:
            if match:
                # Извлекаем рубли и копейки
                rub = match.group(1)
                kop = None
                if match.group(4):
                    # Второе число (копейки)
                    kop_match = re.search(r"\d{1,2}", match.group(4))
                    if kop_match:
                        kop = kop_match.group(0)
                if kop:
                    amount = float(rub) + float(kop)/100
                else:
                    amount = float(rub)
                # Вырезаем эту сумму с валютой из текста
                text_wo_amount = original_text.replace(match.group(0), "")
                category = re.sub(r"\s+", " ", text_wo_amount).strip()
                return amount, category
    # Если не найдено суммы — возвращаем 0 и весь текст как категорию
    return 0.0, original_text.strip()

def save_to_yadisk(user_id, text, message_date=None):
    print(f"[DEBUG] datetime = {datetime}")
    token = get_user_token(user_id)
    if not token:
        raise Exception("User not authenticated")
    file_name = f"{user_id}.xlsx"
    remote_path = f"app:/{file_name}"

    amount, category = parse_expense(text)
    if amount is None or category is None:
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
        # Если старый файл — добавь столбец если нужно (миграция)
        if sheet.max_row == 1 and sheet.max_column == 3:
            sheet.cell(row=1, column=4).value = "Дата и время"
    else:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["#", "Сумма", "Категория", "Дата и время"])

    idx = sheet.max_row
    # timestamp: используем message_date или текущее время сервера
    if message_date:
        dt = datetime.fromtimestamp(message_date)  # message_date из Telegram — это unix timestamp (int)
    else:
        dt = datetime.now()
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    sheet.append([idx, amount, category, dt_str])

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
