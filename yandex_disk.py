import os
import requests

# ===== Функция проверки и создания папки budgetify =====

def ensure_folder_exists(user_id):
    token_path = f'tokens/{user_id}.token'
    if not os.path.exists(token_path):
        print(f'[ERROR] Токен для user_id={user_id} не найден')
        return False

    with open(token_path) as f:
        token = f.read().strip()
    headers = {'Authorization': f'OAuth {token}'}
    folder_path = 'app:/budgetify'
    url = 'https://cloud-api.yandex.net/v1/disk/resources'
    params = {'path': folder_path}

    # Проверяем, есть ли папка
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 404:
        # Создаём папку, если её нет
        response = requests.put(url, headers=headers, params=params)
        if response.status_code not in [201, 409]:
            print(f'[ERROR] Не удалось создать папку budgetify: {response.status_code} {response.text}')
            return False
    elif response.status_code != 200:
        print(f'[ERROR] Ошибка при проверке папки budgetify: {response.status_code} {response.text}')
        return False
    return True

# ======= Сохранение расходов пользователя =======

def save_to_yadisk(user_id, text):
    if not ensure_folder_exists(user_id):
        print(f'[ERROR] Не удалось создать/проверить папку budgetify')
        return False

    token_path = f'tokens/{user_id}.token'
    if not os.path.exists(token_path):
        print(f'[ERROR] Токен для user_id={user_id} не найден')
        return False

    with open(token_path) as f:
        token = f.read().strip()

    headers = {'Authorization': f'OAuth {token}'}
    file_name = f'{user_id}.txt'
    file_path = f'app:/budgetify/{file_name}'
    upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
    params = {'path': file_path, 'overwrite': 'true'}

    # Получаем ссылку для загрузки
    resp = requests.get(upload_url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f'[ERROR] Ошибка при получении upload url: {resp.status_code} {resp.text}')
        return False
    href = resp.json().get('href')
    if not href:
        print('[ERROR] В ответе нет поля href')
        return False

    # Загружаем файл
    try:
        r = requests.put(href, data=text.encode('utf-8'))
        if r.status_code not in [201, 202]:
            print(f'[ERROR] Ошибка загрузки файла: {r.status_code} {r.text}')
            return False
    except Exception as e:
        print(f'[ERROR] Exception при загрузке файла: {e}')
        return False

    return True

# ======= Проверка авторизации =======
def is_user_authenticated(user_id):
    token_path = f'tokens/{user_id}.token'
    return os.path.exists(token_path)

# ======= Получить ссылку для авторизации =======
def get_auth_link(client_id):
    return (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&client_id={client_id}&scope=cloud_api:disk.app_folder"
    )

# ======= Сохранить токен после получения кода =======
def set_auth_code(user_id, token):
    tokens_dir = 'tokens'
    os.makedirs(tokens_dir, exist_ok=True)
    with open(f'{tokens_dir}/{user_id}.token', 'w') as f:
        f.write(token)
