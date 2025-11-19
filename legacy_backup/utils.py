import uuid
import requests
import openai
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

from os import getenv


scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file('/Users/rikenshah/Desktop/Fun/insta-model/aashvi-model-899f62fffa21.json',
                                              scopes=scope)


def setup_openai():
    openai.organization =  getenv("OPENAI_ORGANIZATION")
    openai.api_key = getenv("OPENAI_API_KEY")


def send_messages(message):
    body = {
        "message_id": str(uuid.uuid4()),
        "text": message,
        "chat_id": "1417419064"
    }

    res = requests.post(f"{getenv('TELEGRAM_WEBHOOK_URL')}/sendMessage",
                        json=body)

    if res.status_code == 200:
        print("Message sent")
    else:
        print("Error sending message", res.status_code, res.json())


def send_images_to_bot(message, images):
    body = {
        "chat_id": "1417419064"
    }
    send_messages(message)
    medias = []
    for img in images:
        medias.append({
            "type": "photo",
            "media": img,

        })
    body["media"] = medias
    print(body)
    res = requests.post(f"{getenv('TELEGRAM_WEBHOOK_URL')}/sendMediaGroup", json=body)
    if res.status_code == 200:
        print(res.json())
        print("images sent")
    else:
        print("Error sending message", res.status_code, res.json())


def get_gspread_client():
    sheet = gspread.authorize(creds).open_by_key(getenv("GSPREED_KEY")).worksheet("v1")
    return sheet


def generate_uuid():
    return str(uuid.uuid4())


