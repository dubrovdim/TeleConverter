import telebot
from telebot import types
import os
import docx2pdf
import img2pdf
import uuid
import tempfile
import shutil
import pytesseract
from PIL import Image

# Отримання токена з змінної середовища
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise Exception("Environment variable TELEGRAM_BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN)

# Словник для зберігання даних користувачів (тимчасові файли зображень)
users_data = {}

# Обробник команди /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("docx to pdf")
    btn2 = types.KeyboardButton("img to pdf")
    btn3 = types.KeyboardButton("text from image")
    markup.row(btn1, btn2, btn3)
    bot.send_message(message.chat.id,
                     f"Привіт, {message.from_user.first_name}! Обери вид форматування.",
                     reply_markup=markup)

# Обробка запиту на конвертацію DOCX у PDF
@bot.message_handler(func=lambda msg: msg.text == "docx to pdf")
def message_docx_to_pdf(message):
    bot.send_message(message.chat.id, "Надішли файл з розширенням .docx")
    bot.register_next_step_handler(message, handle_document)

def handle_document(message):
    cmd = message.text.lower().strip() if message.text else ""
    if cmd in ["img to pdf", "docx to pdf"]:
        if cmd == "docx to pdf":
            message_docx_to_pdf(message)
        else:
            message_img_to_pdf(message)
        return
    if message.text and message.text.startswith('/'):
        bot.process_new_messages([message])
        return
    if message.document is None:
        bot.reply_to(message, "Будь ласка, завантажте файл у форматі .docx")
        bot.register_next_step_handler(message, handle_document)
        return

    # Перевірка розширення
    if not message.document.file_name.lower().endswith('.docx'):
        bot.reply_to(message, "Будь ласка, завантажте файл у форматі .docx")
        bot.register_next_step_handler(message, handle_document)
        return

    # Отримання файлу від Telegram
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Генерація унікальних імен для тимчасових файлів
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    input_file_path = os.path.join(temp_dir, unique_id + ".docx")
    output_file_path = os.path.join(temp_dir, unique_id + ".pdf")

    with open(input_file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    try:
        docx2pdf.convert(input_file_path, output_file_path)
    except Exception as e:
        bot.reply_to(message, f"Сталася помилка при конвертації: {e}")
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
        return

    with open(output_file_path, 'rb') as pdf_file:
        bot.send_document(message.chat.id, pdf_file)

    # Очищення тимчасових файлів
    if os.path.exists(input_file_path):
        os.remove(input_file_path)
    if os.path.exists(output_file_path):
        os.remove(output_file_path)

# Обробка запиту на конвертацію зображень у PDF
@bot.message_handler(func=lambda msg: msg.text == "img to pdf")
def message_img_to_pdf(message):
    chat_id = message.chat.id
    # Створюємо унікальну тимчасову директорію для збереження зображень користувача
    user_temp_dir = tempfile.mkdtemp(prefix=f"chat_{chat_id}_")
    users_data[chat_id] = {'images_dir': user_temp_dir, 'images': []}
    bot.send_message(chat_id, "Надішліть одне або кілька зображень (jpg, jpeg, png). Коли завершите — надішліть /done.")
    bot.register_next_step_handler(message, handle_image)

def handle_image(message):
    chat_id = message.chat.id
    # Якщо дані для користувача відсутні, ініціалізуємо їх
    if chat_id not in users_data:
        user_temp_dir = tempfile.mkdtemp(prefix=f"chat_{chat_id}_")
        users_data[chat_id] = {'images_dir': user_temp_dir, 'images': []}

    cmd = message.text.lower().strip() if message.text else ""
    if cmd in ["img to pdf", "docx to pdf"]:
        if cmd == "img to pdf":
            message_img_to_pdf(message)
        else:
            message_docx_to_pdf(message)
        return

    # Якщо отримано команду /done, формуємо PDF
    if message.text and message.text.lower() == "/done":
        images = users_data[chat_id]['images']
        if not images:
            bot.send_message(chat_id, "Ви не надіслали жодного зображення.")
            bot.register_next_step_handler(message, handle_image)
            return

        output_file_path = os.path.join(users_data[chat_id]['images_dir'], "merged.pdf")
        try:
            with open(output_file_path, 'wb') as new_file:
                new_file.write(img2pdf.convert(images))
        except Exception as e:
            bot.send_message(chat_id, f"Сталася помилка при конвертації: {e}")
            return

        with open(output_file_path, 'rb') as pdf_file:
            bot.send_document(chat_id, pdf_file)

        # Видаляємо тимчасову директорію разом із файлами
        shutil.rmtree(users_data[chat_id]['images_dir'], ignore_errors=True)
        del users_data[chat_id]
        return
    if message.text and message.text.startswith('/'):
        bot.process_new_messages([message])
        return

    # Обробка фото, якщо воно надіслане як фото
    if message.photo:
        photo_obj = message.photo[-1]  # Беремо фото з найвищою роздільною здатністю
        file_info = bot.get_file(photo_obj.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        # Генеруємо унікальне ім'я для зображення
        image_filename = uuid.uuid4().hex + ".jpg"
        image_path = os.path.join(users_data[chat_id]['images_dir'], image_filename)
        with open(image_path, 'wb') as f:
            f.write(downloaded_file)
        users_data[chat_id]['images'].append(image_path)
        bot.send_message(chat_id, "Зображення додано. Надсилайте ще або введіть /done.")
        bot.register_next_step_handler(message, handle_image)
    # Обробка зображень, якщо вони надіслані як документ
    elif message.document:
        file_name = message.document.file_name.lower()
        if not (file_name.endswith('.jpg') or file_name.endswith('.jpeg') or file_name.endswith('.png')):
            bot.send_message(chat_id, "Будь ласка, надішліть файл з правильним розширенням (.jpg, .jpeg, .png).")
            bot.register_next_step_handler(message, handle_image)
            return
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        # Генеруємо унікальне ім'я зберігаючи розширення
        ext = os.path.splitext(file_name)[1]
        image_filename = uuid.uuid4().hex + ext
        image_path = os.path.join(users_data[chat_id]['images_dir'], image_filename)
        with open(image_path, 'wb') as f:
            f.write(downloaded_file)
        users_data[chat_id]['images'].append(image_path)
        bot.send_message(chat_id, "Зображення додано. Надсилайте ще або введіть /done.")
        bot.register_next_step_handler(message, handle_image)
    else:
        bot.send_message(chat_id, "Будь ласка, надішліть зображення у форматі .jpg, .jpeg або .png")
        bot.register_next_step_handler(message, handle_image)


@bot.message_handler(func=lambda msg: msg.text == "text from image")
def start_image_text_mode(message):
    chat_id = message.chat.id
    user_temp_dir = tempfile.mkdtemp(prefix=f"chat_{chat_id}_")
    users_data[chat_id] = {'images_dir': user_temp_dir, 'images': []}
    bot.send_message(chat_id, "📸 Надішли одне або кілька фото з текстом. Коли завершиш — напиши /recognize.")
@bot.message_handler(content_types=['photo'])
def save_photo(message):
    chat_id = message.chat.id
    if chat_id not in users_data:
        return bot.reply_to(message, "❗ Спочатку введи команду \"text from image\" (кнопкою або /textfromimage)")
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)
    image_path = os.path.join(users_data[chat_id]['images_dir'], f"{file_id}.jpg")
    with open(image_path, 'wb') as f:
        f.write(downloaded)
    users_data[chat_id]['images'].append(image_path)
    bot.reply_to(message, f"✅ Фото збережено. Усього: {len(users_data[chat_id]['images'])}")
@bot.message_handler(commands=['recognize'])
def recognize_all_images(message):
    chat_id = message.chat.id

    if chat_id not in users_data or not users_data[chat_id]['images']:
        return bot.reply_to(message, "❗ Немає зображень для розпізнавання. Спочатку надішли фото після \"text from image\"")

    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Dmytro\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

    result_text = ""
    for img_path in users_data[chat_id]['images']:
        try:
            image = Image.open(img_path)
            text = pytesseract.image_to_string(image, lang='ukr+rus+eng')
            result_text += f"\n{text.strip()}\n"
        except Exception as e:
            result_text += f"⚠️ Помилка в {img_path}:\n{str(e)}\n"

    bot.send_message(chat_id, result_text if result_text.strip() else "❌ Текст не знайдено.")

    return -1

if __name__ == '__main__':
    bot.polling(none_stop=True)
