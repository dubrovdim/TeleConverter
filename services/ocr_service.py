import requests
from config import Config


class OCRService:
    def __init__(self):
        self.api_key = Config.OCR_API_KEY
        
    def recognize_text(self, image_paths: list[str]) -> str:
        result_text = ""
        url = "https://api.ocr.space/parse/image"

        for img_path in image_paths:
            try:
                with open(img_path, 'rb') as f:
                    payload = {
                        'apikey': self.api_key,
                        'language': 'eng',
                        'isOverlayRequired': False
                    }
                    files = {'file': f}
                    response = requests.post(url, files=files, data=payload)

                    data = response.json()

                    if data.get('IsErroredOnProcessing'):
                        result_text += f"⚠️ Помилка API: {data.get('ErrorMessage')}\n"
                        continue

                    parsed_results = data.get('ParsedResults')
                    if parsed_results:
                        text = parsed_results[0].get('ParsedText')
                        result_text += f"{text}\n\n"
            except Exception as e:
                result_text += f"⚠️ Помилка з'єднання: {e}\n"

        return result_text.strip() if result_text.strip() else "❌ Текст не знайдено."
