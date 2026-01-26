from datetime import datetime
from google_client import get_google_client

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

client = get_google_client(scopes)
sheet = client.open("ready_on_onboarding").sheet1


def save_lead(data: dict):
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("user_id"),
        data.get("username"),
        data.get("age"),
        data.get("citizenship"),
        data.get("city"),
        data.get("delivery"),
        data.get("day_income"),
        data.get("month_avg"),
        data.get("month_max"),
    ])
