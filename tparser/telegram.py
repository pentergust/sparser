"""
Телеграмм бот, отправляющий расписание уроков.
Является обёрткой над SceduleParser.

Author: Артём Березин
Modifired: Milinuri Nirvalen
Ver: sp 1.0
"""

from tparser import ScheduleParser

from datetime import datetime

import telebot


# Неекоторые настройки скрипта
API_TOKEN = ""
bot = telebot.TeleBot(API_TOKEN)
days = ["понедельник", "вторник", "среда", "четверг", "пятница", "субботу",
        "расписание на сегодня", "расписание на завтра"]

# Сообщение при старте бота в первый раз
start_text = """
🧾 Здравствуй! Я - бот, который рассылает вам ваше расписание!
❓ Введите /help для запуска бота.
❗ Внимание, бот находится в разработке, некоторые функции ещё не реализованы!
🔎 Предложения по доработке: https://t.me/optemikk"""


# Фукнкции для Телеграмм бота
# ===========================

def return_to_home(mag, sp):
    """Возвращает пользователя в главный экран бота."""
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.add("Продолжить")
    keyboard.add("Выбрать класс")
    keyboard.add(f"Выбран класс: {sp.user['clas_let']}")
    # keyboard.add("Список изменений")
    bot.reply_to(msg, "✅ Главное меню", reply_markup=keyboard)

def change_class(msg, sp):
    """Изменение класса пользователя."""
    
    if msg.text.lower() == "отмена":
        bot.reply_to(msg, "✅ Вы отменили изменение класса!")
    else:
        bot.reply_to(msg, sp.change_class(msg.text.lower()))

    return_to_home(msg, sp)

def send_keyboard(msg):
    """Вывод основной клавиатуры клавиатуры."""
    
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.add("Расписание на завтра")
    keyboard.add("Расписание на сегодня")
    keyboard.add("Понедельник", "Вторник", "Среда")
    keyboard.add("Четверг", "Пятница", "Суббота")
    keyboard.add("Вернуться в меню")
    bot.reply_to(msg, f"🧾 Нажмите на кнопку и получить реасписание!", 
                 reply_markup=keyboard)
        

# Основная часть бота
# ===================

@bot.message_handler(commands=["start"])
def start(msg):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    bot.reply_to(msg, start_text, reply_markup=keyboard)

@bot.message_handler(content_types=["text"])
def handle_text(msg):
    text = msg.text.lower()
    sp = ScheduleParser(str(msg.chat.id))

    if text == "/help":
        return_to_home(msg, sp)
    
    elif text in days:
        if text == "расписание на сегодня":
            today = datetime.today().weekday()
        elif text == "расписание на завтра":
            today = datetime.today().weekday()+1
        else:
            today = days.index(text)

        bot.reply_to(msg, sp.get_lessons(today))
    
    elif text == "выбрать класс":
        keyboard = telebot.types.ReplyKeyboardMarkup(True)
        keyboard.add("Отмена")
        bot.reply_to(msg, "✏ Введите номер и букву Вашего класса.",
                     reply_markup=keyboard)
        bot.register_next_step_handler(msg, change_class)
    
    elif text == "вернуться в меню":
        return_to_home(msg, sp)
    
    elif text == "продолжить":
        send_keyboard(msg)

# Запуск скрипта
# ==============

if __name__ == "__main__":
    print("Start bot")
    bot.polling(none_stop=True, interval=0)
