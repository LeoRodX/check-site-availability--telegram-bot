import telebot
from telebot import types
import requests
import schedule
import time
import json
import smtplib
import threading
from email.mime.text import MIMEText
from datetime import datetime
import subprocess
import platform

# Загрузка конфигурации
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

TOKEN = config['token']
ID_URL = config['id_url']
SITE_URL = config['site_url']
LKK_URL = config['lkk_url']
TRACERT0_URL = config['tracert_Rostelecom'] # Промежуточный адрес
TRACERT1_URL = config['tracert_Beeline'] # Промежутоный адрес
CHECK_INTERVAL = config['check_interval']
EMAIL_FROM = config['email_from']  # Отправитель  EMAIL
EMAIL_PASSWORD = config['email_password']
SMTP_SERVER = config['smtp_server']
SMTP_PORT = config['smtp_port']
EMAIL_TO = config['email_to']  # Получатель
SUPERVISOR_ID = config['supervisor_id']
DUTY_ID = config['duty_id']

CYCLE = 1

# Инициализация бота
bot = telebot.TeleBot(TOKEN)


# Функция для загрузки данных из файла
def load_data():
    try:
        with open('user_data.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


# Функция для сохранения данных в файл
def save_data(data):
    with open('user_data.json', 'w') as file:
        json.dump(data, file, indent=4)


# Файл для хранения результатов проверок
LOG_ID = 'id_checks.log'
LOG_SITE = 'site_checks.log'
LOG_LKK = 'lkk_checks.log'


# Функция для проверки доступности сайта
def check_site_availability(TEST_URL, LOG_FILE):
    try:
        # Проверка операционной системы
        parameter = '-n' if platform.system().lower() == 'windows' else '-c'
        # Выполняем команду ping
        command0 = ['ping', parameter, '1', TRACERT0_URL]
        output0 = subprocess.run(command0, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True)
        command1 = ['ping', parameter, '1', TRACERT1_URL]
        output1 = subprocess.run(command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True)
        # Если код возврата 0, хост доступен
        if output0.returncode == 0 or output1.returncode == 0:
            try:
                response = requests.get(TEST_URL, timeout=10)
                status = "Доступен" if response.status_code == 200 else "Недоступен"
            except requests.RequestException:
                status = "Недоступен"
            # Пишем в журнал, если статус изменился
            try:
                with open(LOG_FILE, 'r') as log:
                    lines = log.readlines()
                    if len(lines) > 0:
                        last_status = lines[-1].split(" ")[3].strip()
                        if last_status != status:
                            # Логирование результата
                            with open(LOG_FILE, 'a') as log:
                                now = datetime.now()
                                date_format = now.strftime("%d/%m/%Y %H:%M:%S")
                                log.write(f"{date_format} {TEST_URL} {status}\n")
                                # Отправка уведомления
                            send_push(TEST_URL, status)
            except FileNotFoundError as error:
                with open(LOG_FILE, 'a') as log:
                    now = datetime.now()
                    date_format = now.strftime("%d/%m/%Y %H:%M:%S")
                    log.write(f"{date_format} {TEST_URL} {status}\n")
        else:
            status = "Пропустить проверку"
    except Exception as e:
        pass
    return status


# Функция для отправки отчёта на почту
# def send_email(subject, body):
#    msg = MIMEText(body)
#    msg['Subject'] = subject
#    msg['From'] = EMAIL_FROM
#    msg['To'] = EMAIL_TO

#    try:
#        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#            server.starttls()
#            server.login(EMAIL_FROM, EMAIL_PASSWORD)
#            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
#    except Exception as e:
#        print(e)


# Функция для проверки изменений и отправки пушей
def send_push(TEST_URL, current_status):
    if current_status == 'Доступен':
        text_notification = (f"✅💨 Сайт {TEST_URL} {current_status}")
        bot.send_message(chat_id=SUPERVISOR_ID, text=text_notification)
        # bot.send_message(chat_id=DUTY_ID, text=notification)
    elif current_status == 'Недоступен':
        text_notification = (f"❌💨 Сайт {TEST_URL} {current_status}")
        bot.send_message(chat_id=SUPERVISOR_ID, text=text_notification)
        # bot.send_message(chat_id=DUTY_ID, text=notification)


def check_cycle():
    global CYCLE
    if CYCLE == 1:
        check_site_availability(ID_URL, LOG_ID)
        CYCLE = 2
    elif CYCLE == 2:
        check_site_availability(SITE_URL, LOG_SITE)
        CYCLE = 3
    else:
        check_site_availability(LKK_URL, LOG_LKK)
        CYCLE = 1


# Планировщик для проверки каждые 10 минут
schedule.every(CHECK_INTERVAL).minutes.do(check_cycle)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем Reply-клавиатуру
    # resize_keyboard=True делает кнопки компактными
    # row_width задает количество кнопок в строке
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    # Создаем кнопки с эмоджи и текстом
    btn1 = types.KeyboardButton("🆔 Проверить \"ID\"")
    btn2 = types.KeyboardButton("📋 Отчёт \"ID\"")
    btn3 = types.KeyboardButton("🌐 Проверить сайт")
    btn4 = types.KeyboardButton("📝 Отчёт САЙТ")
    btn5 = types.KeyboardButton("👛 Проверить ЛКК")
    btn6 = types.KeyboardButton("📑 Отчёт ЛКК")
    # Добавляем кнопки в клавиатуру
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    # Получаем данные польователя
    user_id = message.from_user.id
    username = message.from_user.username
    # Загружаем текущие данные
    user_data = load_data()
    # Проверяем, есть ли пользователь в данных
    if str(user_id) in user_data:
        bot.reply_to(message,
                     f"Ваш User ID: {user_id}, username: {username}. Для получения уведомлений "
                     f"отправьте это сообщение администратору")
    else:
        # Добавляем нового пользователя
        user_data[str(user_id)] = {'username': username}
        # Сохраняем данные в файл
        save_data(user_data)
        # bot.reply_to(message, f"Ваш User ID: {user_id} и username: {username} сохранены!")
    # Отправляем сообщение с клавиатурой
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)


# Обработчик кнопок
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    # Кнопки ID
    if message.text == '🆔 Проверить \"ID\"':
        status = check_site_availability(ID_URL, LOG_ID)
        # Добавление эмоджи
        if status == 'Доступен':
            bot.send_message(message.chat.id, f"✅ Сайт {ID_URL} сейчас {status}.")
        elif status == 'Недоступен':
            bot.send_message(message.chat.id, f"❌ Сайт {ID_URL} сейчас {status}.")
    elif message.text == '📋 Отчёт \"ID\"':
        with open(LOG_ID, 'r') as log:
            lines = log.readlines()[
                    -7 * 24 * 6:]  # Последние 7 дней (10 минут * 6 раз в час * 24 часа * 7 дней)
            report = "".join(lines)
            bot.send_message(message.chat.id, f"Отчёт за последние 7 дней:\n{report}")
    # Кнопки сайта
    elif message.text == '🌐 Проверить сайт':
        status = check_site_availability(SITE_URL, LOG_SITE)
        # Добавление эмоджи
        if status == 'Доступен':
            bot.send_message(message.chat.id, f"✅ Сайт {SITE_URL} сейчас {status}.")
        elif status == 'Недоступен':
            bot.send_message(message.chat.id, f"❌ Сайт {SITE_URL} сейчас {status}.")
    elif message.text == '📝 Отчёт САЙТ':
        with open(LOG_SITE, 'r') as log:
            lines = log.readlines()[
                    -7 * 24 * 6:]  # Последние 7 дней (10 минут * 6 раз в час * 24 часа * 7 дней)
            report = "".join(lines)
            bot.send_message(message.chat.id, f"Отчёт за последние 7 дней:\n{report}")
    # Кнопки ЛКК
    elif message.text == '👛 Проверить ЛКК':
        status = check_site_availability(LKK_URL, LOG_LKK)
        if status == 'Доступен':
            bot.send_message(message.chat.id, f"✅ Сайт {LKK_URL} сейчас {status}.")
        elif status == 'Недоступен':
            bot.send_message(message.chat.id, f"❌ Сайт {LKK_URL} сейчас {status}.")
    elif message.text == '📑 Отчёт ЛКК':
        with open(LOG_LKK, 'r') as log:
            lines = log.readlines()[-7 * 24 * 6:]
            report = "".join(lines)
            # # send_email(f"Отчёт по сайту {SITE_URL}", report)
            # # bot.send_message(message.chat.id, "Отчёт отправлен на почту.")
            bot.send_message(message.chat.id, f"Отчёт за последние 7 дней:\n{report}")
    # Отправка сообщения всем чатланам. сообщение должно начинаться с текста "Внимание!"
    elif message.text.startswith('Внимание!'):
        text_information = message.text[9:]
        users = load_data()
        for user_id in users:
            try:
                bot.send_message(user_id, f"ℹ️️{text_information}")
            except Exception as e:
                pass


# Запуск планировщика в отдельном потоке
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()

# Запуск бота
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        time.sleep(2)




