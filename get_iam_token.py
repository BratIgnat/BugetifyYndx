import json
import jwt
import time
import requests

# Путь до твоего key.json
with open("key.json", "r") as f:
    service_account = json.load(f)

service_account_id = service_account["service_account_id"]
key_id = service_account["id"]
private_key = service_account["private_key"] if "private_key" in service_account else service_account["key"]["secret"]

now = int(time.time())
payload = {
    "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
    "iss": service_account_id,
    "iat": now,
    "exp": now + 360,
}

encoded_jwt = jwt.encode(payload, private_key, algorithm="PS256", headers={"kid": key_id})

response = requests.post(
    "https://iam.api.cloud.yandex.net/iam/v1/tokens",
    json={"jwt": encoded_jwt}
)

if response.status_code == 200:
    print("✅ IAM Token:")
    print(response.json()["iamToken"])
else:
    print("❌ Ошибка получения IAM токена:")
    print(response.text)
