from datetime import datetime, timedelta
from google_client import get_google_client

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

client = get_google_client(scopes)
sheet = client.open("ready_on_onboarding").sheet1

def save_lead(data: dict):
    # Время с +4 часа
    current_time = datetime.utcnow() + timedelta(hours=4)

    # Приводим все значения к строкам, если данных нет — пустая строка
    row = [
        current_time.strftime("%Y-%m-%d %H:%M:%S"),
        data.get("user_id", ""),
        data.get("username", ""),
        data.get("age", ""),
        data.get("citizenship", ""),
        data.get("city", ""),
        data.get("delivery", ""),
        data.get("day_income", ""),
        data.get("month_avg", ""),
        data.get("month_max", ""),
    ]
    sheet.append_row(row)
