import os
import io
import openpyxl
import requests

def get_user_token(user_id):
    tokens_dir = "tokens"
    token_path = os.path.join(tokens_dir, f"{user_id}.token")
    if not os.path.exists(token_path):
        return None
    with open(token_path, "r") as f:
        return f.read().strip()

def save_expense_to_excel(user_token, user_id, amount, category):
    disk_path = f"app:/budgetify/{user_id}.xlsx"
    headers = {"Authorization": f"OAuth {user_token}"}

    # Скачиваем файл если он есть, иначе создаём новый
    url = f"https://cloud-api.yandex.net/v1/disk/resources/download?path={disk_path}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        download_url = response.json()["href"]
        excel_content = requests.get(download_url).content
        workbook = openpyxl.load_workbook(io.BytesIO(excel_content))
        sheet = workbook.active
    else:
        # Новый Excel
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["#", "Сумма", "Категория"])

    # Следующая строка
    row_num = sheet.max_row
    sheet.append([row_num, f"{amount}", category])

    # Сохраняем в память
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # Получаем upload url
    upload_url = f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={disk_path}&overwrite=true"
    response = requests.get(upload_url, headers=headers)
    upload_href = response.json()["href"]
    r = requests.put(upload_href, data=output.getvalue())
    r.raise_for_status()

    return True
