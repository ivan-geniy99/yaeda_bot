import json
import gspread
from google.oauth2.service_account import Credentials
import threading
import time
import base64
import os
import logging
from google_client import get_google_client
logger = logging.getLogger(__name__)


# === 6. КЭШ ===
average_income_ya_eda = []
_init_started = False
_init_lock = threading.Lock()
_data_lock = threading.Lock()

def init_income_service():
    global _init_started
    # 🔒 защита от повторного запуска
    with _init_lock:
        if _init_started:
            return
        _init_started = True

        #b64_key = os.environ.get("GOOGLE_CRED_JSON_IN_BASE_64")
        #decoded_json = base64.b64decode(b64_key).decode("utf-8")
        #key_dict = json.loads(decoded_json)
        # ⬇️ дальше БЕЗ lock
        decoded_json = base64.b64decode(
            os.environ["GOOGLE_CRED_JSON_IN_BASE_64"]
        ).decode("utf-8")
        key_dict = json.loads(decoded_json)

        # ✅ Добавляем нужные права
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]

        # Авторизация
        client = get_google_client(scopes)

        # Функция обновления данных
        def update_income():
            nonlocal client
            try:
                sheet = client.open("average_income_ya_eda").sheet1
                records = sheet.get_all_records()
                
                with _data_lock:
                    average_income_ya_eda.clear()
                    average_income_ya_eda.extend(records)

                logger.info(
                "Income cache updated: %d records",
                len(records)
                )
            except Exception:
                logger.exception("Failed to update income cache")
                
        # Первоначальный запрос при старте
        update_income()

        def loop():
            while True:
                time.sleep(900)
                update_income()

        threading.Thread(target=loop, daemon=True, name="income-cache-updater").start()

def get_average_income():
    if not _init_started:
        init_income_service()  # 🔒 безопасно, т.к. есть lock
    # 🔒 возвращаем копию
    with _data_lock:
        return list(average_income_ya_eda)


