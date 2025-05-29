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

import re

def parse_expense(text):
    """
    Извлекает сумму из текста, полностью удаляя слова 'рубль', 'руб', 'р', 'копейка', 'коп', 'к' и все их формы/падежи.
    Всегда возвращает float (например: '50 тысяч рублей 43 копейки' -> 50043.0).
    """

    # 1. Привести к нижнему регистру и убрать все валютные слова
    clean_text = text.lower()
    # Список всех возможных форм рубля и копейки (регулярки по границе слова)
    currency_words = [
        r"\bруб(ль|лей|ля|ли|лям|лями|лем|лю|.)?\b",    # любые формы "рубль"
        r"\bр\b",                                       # отдельное "р"
        r"\bкоп(ейка|ейки|еек|ейку|ейкой|ейками|ейки|.)?\b", # любые формы "копейка"
        r"\bк\b",                                       # отдельное "к"
    ]
    for word_pattern in currency_words:
        clean_text = re.sub(word_pattern, " ", clean_text, flags=re.IGNORECASE)
    
    # 2. Убрать лишние пробелы
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # 3. Поиск суммы (ищем числа, в том числе формата 50 тысяч 43)
    # Заменяем слова "тысяч", "тысяча" и пр. на 000
    clean_text = re.sub(r"\b(тысяч[аи]?|тыс)\b", "000", clean_text)
    clean_text = re.sub(r"\b(миллион[а-я]*)\b", "000000", clean_text)
    clean_text = re.sub(r"\b(миллиард[а-я]*)\b", "000000000", clean_text)

    # Извлекаем все числа
    numbers = re.findall(r"\d+", clean_text)
    if not numbers:
        return 0.0  # Если ничего не найдено

    # Склеиваем числа (напр. "50 000 43" -> 50043), либо берем по логике твоего проекта
    # Тут можно настроить свою логику: например, если обычно "43" — это копейки,
    # то можно вернуть float(рубли) + float(копейки)/100
    # Если всё число склеено — возвращаем как есть
    if len(numbers) == 1:
        return float(numbers[0])

    # Классика для русского ввода: "50 43" = 50 руб 43 коп
    if len(numbers) == 2 and int(numbers[1]) < 100:
        return float(numbers[0]) + float(numbers[1]) / 100

    # В противном случае просто объединяем числа (50 000 43 -> 50043)
    return float(''.join(numbers))

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
