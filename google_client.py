import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

def get_google_client(scopes: list[str]) -> gspread.Client:
    decoded_json = base64.b64decode(
        os.environ["GOOGLE_CRED_JSON_IN_BASE_64"]
    ).decode("utf-8")

    key_dict = json.loads(decoded_json)

    creds = Credentials.from_service_account_info(
        key_dict,
        scopes=scopes
    )

    return gspread.authorize(creds)