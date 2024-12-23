import sqlite3
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types

# Telegram API Token
API_TOKEN = 'ВАШ_ТОКЕН_ОТ_BOTFATHER'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Настройка базы данных
conn = sqlite3.connect("bot_users.db")
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    faculty TEXT,
    group_name TEXT
)''')
conn.commit()

# Функция для сохранения данных пользователя
def save_user(user_id, faculty, group_name):
    cursor.execute("REPLACE INTO users (user_id, faculty, group_name) VALUES (?, ?, ?)",
                   (user_id, faculty, group_name))
    conn.commit()

# Функция для получения данных пользователя
def get_user(user_id):
    cursor.execute("SELECT faculty, group_name FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

# Парсинг расписания с сайта
def fetch_schedule(faculty, group_name):
    try:
        # URL сайта
        url = "https://tt.chuvsu.ru/"
        session = requests.Session()

        # Получение страницы и выбор факультета
        response = session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        faculty_option = soup.find("option", text=faculty)
        if not faculty_option:
            return "Факультет не найден. Проверьте ввод."

        faculty_id = faculty_option["value"]
        response = session.post(url, data={"selection": faculty_id})

        # Выбор группы
        soup = BeautifulSoup(response.text, 'html.parser')
        group_option = soup.find("option", text=group_name)
        if not group_option:
            return "Группа не найдена. Проверьте ввод."

        group_id = group_option["value"]
        response = session.post(url, data={"selection": group_id})

        # Получение расписания
        soup = BeautifulSoup(response.text, 'html.parser')
        schedule_table = soup.find("table", class_="schedule")
        if not schedule_table:
            return "Расписание не найдено."

        schedule_text = "\n".join(row.get_text(strip=True) for row in schedule_table.find_all("tr"))
        return schedule_text

    except Exception as e:
        return f"Ошибка при получении расписания: {e}"

# Обработчики сообщений
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)

    if user_data:
        await message.reply("Вы уже зарегистрированы. Напишите 'расписание', чтобы получить данные.")
    else:
        await message.reply("Привет! Введите ваш факультет:")

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user(user_id)

    if not user_data:
        # Если пользователь не зарегистрирован, запрашиваем факультет и группу
        if "faculty" not in message.text:
            save_user(user_id, message.text, None)
            await message.reply(f"Факультет '{message.text}' сохранен. Теперь введите свою группу:")
        else:
            faculty = cursor.execute("SELECT faculty FROM users WHERE user_id = ?", (user_id,)).fetchone()
            save_user(user_id, faculty, message.text)
            await message.reply(f"Группа '{message.text}' сохранена. Напишите 'расписание', чтобы получить данные.")
    else:
        # Если пользователь зарегистрирован, обрабатываем команду 'расписание'
        if message.text.lower() == 'расписание':
            faculty, group_name = user_data
            schedule = fetch_schedule(faculty, group_name)
            await message.reply(schedule)
        else:
            await message.reply("Неизвестная команда. Напишите 'расписание', чтобы получить данные.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
