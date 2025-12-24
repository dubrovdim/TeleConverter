import pytesseract
from PIL import Image
import os


class OCRService:
    def __init__(self, tesseract_path: str):
        # Налаштовуємо шлях при створенні екземпляра класу
        self.tesseract_cmd = tesseract_path
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def recognize_text(self, image_paths: list[str], lang='ukr+rus+eng') -> str:
        result_text = ""
        for img_path in image_paths:
            try:
                with Image.open(img_path) as image:
                    text = pytesseract.image_to_string(image, lang=lang)
                    result_text += f"\n--- {os.path.basename(img_path)} ---\n{text.strip()}\n"
            except Exception as e:
                result_text += f"⚠️ Помилка обробки {os.path.basename(img_path)}: {e}\n"

        return result_text.strip() if result_text.strip() else "❌ Текст не знайдено."