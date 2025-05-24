import os
import pandas as pd
from yadisk import YaDisk  # или ваш метод авторизации и загрузки файлов

def save_to_yadisk(user_id, amount, category):
    """
    Сохраняет данные пользователя в Excel-файл (XLSX) и заливает на Яндекс.Диск.
    """
    filename = f"{user_id}.xlsx"
    local_path = filename
    remote_path = f"app:/budgetify/{filename}"

    # Проверяем, есть ли уже такой файл
    if os.path.exists(local_path):
        df = pd.read_excel(local_path)
    else:
        df = pd.DataFrame(columns=["#", "Сумма", "Категория"])

    # Индекс новой записи
    idx = len(df) + 1
    df.loc[len(df)] = [idx, amount, category]

    # Сохраняем локально
    df.to_excel(local_path, index=False)

    # Загружаем на Яндекс.Диск через ваш API/SDK
    # Авторизация должна быть реализована через ваш токен
    # y = YaDisk(token=...) # Подключение и авторизация, используйте ваш код
    # y.upload(local_path, remote_path, overwrite=True)
    # ----------------------
    # Вместо YaDisk — вставьте ваш рабочий метод загрузки файла на диск пользователя!

def is_user_authenticated(user_id):
    # ваша логика проверки токена
    pass

def get_auth_link(user_id):
    # ваша логика генерации ссылки для авторизации
    pass

def set_auth_code(user_id, code):
    # ваша логика обмена code на токен и сохранения его для пользователя
    pass
