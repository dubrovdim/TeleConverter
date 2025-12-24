import telebot
from telebot import types
import os
import uuid
import tempfile
import shutil
from config import Config
from services.ocr_service import OCRService
from services.converter_service import ConverterService


class TeleConverterBot:
    def __init__(self):
        # Ініціалізація бота
        self.bot = telebot.TeleBot(Config.TOKEN)

        # Ініціалізація сервісів
        self.ocr_service = OCRService(Config.TESSERACT_PATH)
        self.converter_service = ConverterService()

        # Зберігання стану користувачів
        self.user_states = {}

        # Реєстрація обробників
        self.register_handlers()

    def register_handlers(self):
        self.bot.message_handler(commands=['start'])(self.handle_start)
        self.bot.message_handler(commands=['done', 'recognize'])(self.handle_finish_commands)
        self.bot.message_handler(content_types=['document'])(self.handle_document)
        self.bot.message_handler(content_types=['photo'])(self.handle_photo)
        self.bot.message_handler(func=lambda msg: True)(self.handle_text_menu)

    def run(self):
        print("🤖 Бот запущено і готовий до роботи...")
        try:
            self.bot.polling(none_stop=True)
        except Exception as e:
            print(f"Критична помилка: {e}")

    # --- Handlers ---

    def handle_start(self, message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("docx to pdf")
        btn2 = types.KeyboardButton("img to pdf")
        btn3 = types.KeyboardButton("text from image")
        markup.row(btn1, btn2, btn3)
        self.bot.send_message(message.chat.id,
                              f"Привіт, {message.from_user.first_name}! Обери режим роботи:",
                              reply_markup=markup)

    def handle_text_menu(self, message):
        chat_id = message.chat.id
        text = message.text.lower().strip()

        if text == "docx to pdf":
            self._set_user_mode(chat_id, "docx_to_pdf")
            self.bot.send_message(chat_id, "📄 Надішли файл .docx")

        elif text == "img to pdf":
            self._set_user_mode(chat_id, "img_to_pdf")
            self.bot.send_message(chat_id, "🖼️ Надішли зображення (як фото або файл). Коли закінчиш - напиши /done")

        elif text == "text from image":
            self._set_user_mode(chat_id, "ocr")
            self.bot.send_message(chat_id, "📸 Надішли фото з текстом. Коли закінчиш - напиши /recognize")

        else:
            self.bot.send_message(chat_id, "Будь ласка, обери команду з меню.")

    def handle_document(self, message):
        chat_id = message.chat.id
        state = self.user_states.get(chat_id)

        if not state:
            return self.bot.reply_to(message, "⚠️ Спочатку оберіть режим у меню.")

        file_name = message.document.file_name.lower()

        # Режим DOCX
        if state['mode'] == 'docx_to_pdf':
            if not file_name.endswith('.docx'):
                return self.bot.reply_to(message, "❗ Будь ласка, завантажте файл саме у форматі .docx")
            self._process_docx(message, state['temp_dir'])

        # Режим Images -> PDF (якщо кидають файлом, а не стиснутим фото)
        elif state['mode'] == 'img_to_pdf':
            if file_name.endswith(('.jpg', '.jpeg', '.png')):
                file_info = self.bot.get_file(message.document.file_id)
                downloaded = self.bot.download_file(file_info.file_path)

                ext = os.path.splitext(file_name)[1]
                filename = f"{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(state['temp_dir'], filename)

                with open(save_path, 'wb') as f:
                    f.write(downloaded)

                state['files'].append(save_path)
                self.bot.reply_to(message, f"✅ Файл додано як зображення (всього {len(state['files'])}).")
            else:
                self.bot.reply_to(message, "❗ Цей формат файлу не підтримується для конвертації в PDF.")

    def handle_photo(self, message):
        chat_id = message.chat.id
        state = self.user_states.get(chat_id)

        if not state or state['mode'] not in ['img_to_pdf', 'ocr']:
            return self.bot.reply_to(message, "Спочатку оберіть режим (img to pdf або text from image).")

        file_info = self.bot.get_file(message.photo[-1].file_id)
        downloaded = self.bot.download_file(file_info.file_path)

        filename = f"{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(state['temp_dir'], filename)

        with open(save_path, 'wb') as f:
            f.write(downloaded)

        state['files'].append(save_path)
        self.bot.reply_to(message, f"✅ Фото додано (всього {len(state['files'])}).")

    def handle_finish_commands(self, message):
        chat_id = message.chat.id
        state = self.user_states.get(chat_id)
        if not state: return

        if message.text == '/done' and state['mode'] == 'img_to_pdf':
            self._finish_img_to_pdf(chat_id, state)
        elif message.text == '/recognize' and state['mode'] == 'ocr':
            self._finish_ocr(chat_id, state)

    # --- Internal Logic ---

    def _set_user_mode(self, chat_id, mode):
        # Якщо був старий стан - чистимо
        if chat_id in self.user_states:
            shutil.rmtree(self.user_states[chat_id]['temp_dir'], ignore_errors=True)

        # Створюємо нову тимчасову папку
        temp_dir = tempfile.mkdtemp(prefix=f"bot_{chat_id}_")
        self.user_states[chat_id] = {
            'mode': mode,
            'temp_dir': temp_dir,
            'files': []
        }

    def _process_docx(self, message, temp_dir):
        unique_id = uuid.uuid4().hex
        input_path = os.path.join(temp_dir, f"{unique_id}.docx")
        output_path = os.path.join(temp_dir, f"{unique_id}.pdf")

        try:
            file_info = self.bot.get_file(message.document.file_id)
            downloaded_file = self.bot.download_file(file_info.file_path)

            with open(input_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            self.bot.send_message(message.chat.id, "⏳ Починаю конвертацію...")

            # Виклик сервісу
            self.converter_service.docx_to_pdf(input_path, output_path)

            with open(output_path, 'rb') as pdf_file:
                self.bot.send_document(message.chat.id, pdf_file)

        except Exception as e:
            self.bot.reply_to(message, f"❌ Помилка: {e}")

        finally:
            if os.path.exists(input_path): os.remove(input_path)
            if os.path.exists(output_path): os.remove(output_path)

    def _finish_img_to_pdf(self, chat_id, state):
        if not state['files']:
            return self.bot.send_message(chat_id, "⚠️ Ви не додали жодного зображення.")

        output = os.path.join(state['temp_dir'], "result.pdf")
        try:
            self.converter_service.images_to_pdf(state['files'], output)
            with open(output, 'rb') as f:
                self.bot.send_document(chat_id, f)
        except Exception as e:
            self.bot.send_message(chat_id, f"Помилка: {e}")
        finally:
            self._cleanup(chat_id)

    def _finish_ocr(self, chat_id, state):
        if not state['files']:
            return self.bot.send_message(chat_id, "⚠️ Немає зображень для розпізнавання.")

        self.bot.send_message(chat_id, "⏳ Розпізнаю текст (це може зайняти час)...")
        text = self.ocr_service.recognize_text(state['files'])

        # Якщо текст дуже довгий, Telegram може не прийняти одне повідомлення
        if len(text) > 4000:
            for x in range(0, len(text), 4000):
                self.bot.send_message(chat_id, text[x:x + 4000])
        else:
            self.bot.send_message(chat_id, text)

        self._cleanup(chat_id)

    def _cleanup(self, chat_id):
        if chat_id in self.user_states:
            shutil.rmtree(self.user_states[chat_id]['temp_dir'], ignore_errors=True)
            del self.user_states[chat_id]


if __name__ == "__main__":
    bot_app = TeleConverterBot()
    bot_app.run()