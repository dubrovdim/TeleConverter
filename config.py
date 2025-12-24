import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    # Шлях до Tesseract. Якщо не задано в .env, беремо дефолтний
    TESSERACT_PATH = os.getenv('TESSERACT_PATH', r'C:\Users\Dmytro\AppData\Local\Programs\Tesseract-OCR\tesseract.exe')

    if not TOKEN:
        raise ValueError("Змінна середовища TELEGRAM_BOT_TOKEN не встановлена!")