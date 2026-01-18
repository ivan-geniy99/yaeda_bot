import json
import gspread
from google.oauth2.service_account import Credentials
import threading
import time
import base64
import os

# === 1. Забираем base64 из переменной окружения ===
b64_key = os.environ["GOOGLE_CRED_JSON_IN_BASE_64"]

# === 2. Декодируем base64 → JSON строка ===
json_key = base64.b64decode(b64_key).decode("utf-8")

# === 3. Парсим JSON ===
key_dict = json.loads(json_key)

# ✅ Добавляем нужные права
scopes = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Авторизация
creds = Credentials.from_service_account_info(key_dict, scopes=scopes) 
client = gspread.authorize(creds)

# === 6. КЭШ ===
average_income_ya_eda = []

# Функция обновления данных
def update_income():
    global average_income_ya_eda
    try:
        sheet = client.open("average_income_ya_eda").sheet1
        average_income_ya_eda = sheet.get_all_records()
        print(f"[INFO] Income cache updated: {len(average_income_ya_eda)} records")
    except Exception as e:
        print(f"[ERROR] Failed to update income: {e}")

# Первоначальный запрос при старте
update_income()

# Фоновый поток для обновления каждые 5 минут
def start_auto_update(interval_sec=300):
    def loop():
        while True:
            update_income()
            time.sleep(interval_sec)
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

# Запускаем автообновление при импорте
start_auto_update()
