import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CONVERT_API_SECRET = os.getenv('CONVERT_API_SECRET')  # Твій ключ від ConvertAPI
    OCR_API_KEY = os.getenv('OCR_API_KEY')  # Твій ключ від OCR.space

    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не встановлено!")