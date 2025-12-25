import easyocr
import os


class OCRService:
    def __init__(self, tesseract_path: str = None):

        print("⏳ Завантаження моделі EasyOCR... Це може зайняти час при першому запуску.")
        # Ініціалізуємо рідера для української (uk), російської (ru) та англійської (en)
        # gpu=False, якщо запускаєш на слабкому сервері без відеокарти.
        # Якщо є NVIDIA GPU, став gpu=True для швидкості.
        self.reader = easyocr.Reader(['uk', 'ru', 'en'], gpu=False)

    def recognize_text(self, image_paths: list[str]) -> str:
        result_text = ""
        for img_path in image_paths:
            try:
                text_list = self.reader.readtext(img_path, detail=0, paragraph=True)
                full_text = "\n".join(text_list)

                result_text += f"\n--- {os.path.basename(img_path)} ---\n{full_text}\n"
            except Exception as e:
                result_text += f"⚠️ Помилка обробки {os.path.basename(img_path)}: {e}\n"

        return result_text.strip() if result_text.strip() else "❌ Текст не знайдено."