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
    Универсальный парсер строки "1000 рублей 41 копейка проезд" → 1000.41, "проезд"
    Работает для любого порядка слов: сумма до/после категории, с/без валюты/копеек.
    """

    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)

    # Шаблоны для суммы в начале или в конце
    # Пример: "1000 рублей 41 копейка такси" или "такси 1000 рублей 41 копейка"
    pattern = r"""
        (?P<cat1>.*?)            # категория (может быть пустой)
        \s*
        (?P<thousands>\d+)\s*тысяч[а-я]*\s* # "2 тысячи" вариант
        (?:(?P<rub>\d+)\s*руб(?:лей|ль)?)? # рубли (опционально)
        (?:\s*(?P<kop>\d{1,2})\s*коп(?:еек|ейки)?)? # копейки (опционально)
        (?P<cat2>.*)              # категория в конце (может быть пустой)
        |                         # Либо просто рубли/копейки без "тысячи"
        (?P<cat3>.*?)             # категория (может быть пустой)
        (?P<rub2>\d+)\s*руб(?:лей|ль)? # "100 рублей"
        (?:\s*(?P<kop2>\d{1,2})\s*коп(?:еек|ейки)?)? # "50 копеек" (опционально)
        (?P<cat4>.*)              # категория (может быть пустой)
        |                         # Или просто число + текст
        (?P<cat5>.*?)             # категория (может быть пустой)
        (?P<num>\d+(?:[.,]\d{1,2})?) # просто число
        (?P<cat6>.*)
    """

    regex = re.compile(pattern, re.VERBOSE)
    match = regex.match(text)

    # 1. Вариант "2 тысячи 100 рублей 41 копейка такси"
    if match and match.group("thousands"):
        rub = int(match.group("thousands")) * 1000
        if match.group("rub"):
            rub += int(match.group("rub"))
        kop = int(match.group("kop") or 0)
        category = f"{match.group('cat1').strip()} {match.group('cat2').strip()}".strip()
        return rub + kop / 100, category

    # 2. Вариант "100 рублей 41 копейка такси" или "такси 100 рублей 41 копейка"
    if match and match.group("rub2"):
        rub = int(match.group("rub2"))
        kop = int(match.group("kop2") or 0)
        category = f"{match.group('cat3').strip()} {match.group('cat4').strip()}".strip()
        return rub + kop / 100, category

    # 3. Вариант "1000 такси" или "такси 1000"
    if match and match.group("num"):
        try:
            rub = float(match.group("num").replace(',', '.'))
        except:
            rub = 0
        category = f"{match.group('cat5').strip()} {match.group('cat6').strip()}".strip()
        return rub, category

    # 4. Если совсем ничего не найдено — попытаться по простому шаблону
    m = re.match(r"(\d+(?:[.,]\d{1,2})?)\s+(.+)", text)
    if m:
        rub = float(m.group(1).replace(',', '.'))
        category = m.group(2).strip()
        return rub, category

    m = re.match(r"(.+?)\s+(\d+(?:[.,]\d{1,2})?)$", text)
    if m:
        category = m.group(1).strip()
        rub = float(m.group(2).replace(',', '.'))
        return rub, category

    # Если только число без категории или не найдено ничего осмысленного
    return None, None

def save_to_yadisk(user_id, text):
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
