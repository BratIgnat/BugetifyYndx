import os
import pandas as pd

def save_to_yadisk(user_id, amount, category):
    """
    Сохраняет данные пользователя в Excel-файл (XLSX) и заливает на Яндекс.Диск.
    """
    filename = f"{user_id}.xlsx"
    local_path = filename
    remote_path = f"app:/budgetify/{filename}"

    if os.path.exists(local_path):
        df = pd.read_excel(local_path)
    else:
        df = pd.DataFrame(columns=["#", "Сумма", "Категория"])

    idx = len(df) + 1
    df.loc[len(df)] = [idx, amount, category]
    df.to_excel(local_path, index=False)

    # Загружаем на Яндекс.Диск через ваш API (используй свой готовый код!)
    # --- Твой рабочий способ загрузки файла сюда! ---

def is_user_authenticated(user_id):
    # твоя проверка токена
    pass

def get_auth_link(user_id):
    # твоя генерация ссылки
    pass

def set_auth_code(user_id, code):
    # твоя обработка кода
    pass
