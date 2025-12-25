import convertapi
import img2pdf
from config import Config

class ConverterService:
    def __init__(self):
        convertapi.api_credentials = Config.CONVERT_API_SECRET

    def docx_to_pdf(self, input_path: str, output_path: str):
        # Відправляємо файл на сервер ConvertAPI
        result = convertapi.convert('pdf', { 'File': input_path })
        # Зберігаємо результат
        result.file.save(output_path)

    def images_to_pdf(self, image_paths: list[str], output_path: str):
        # Це легка операція, її залишаємо робити локально
        if not image_paths:
            raise ValueError("Список зображень порожній")
        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(image_paths))