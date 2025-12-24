import docx2pdf
import img2pdf
import os

class ConverterService:
    @staticmethod
    def docx_to_pdf(input_path: str, output_path: str):
        # Статичний метод, бо йому не треба зберігати стан
        docx2pdf.convert(input_path, output_path)

    @staticmethod
    def images_to_pdf(image_paths: list[str], output_path: str):
        if not image_paths:
            raise ValueError("Список зображень порожній")

        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(image_paths))