import time

import mysql as mysql
import telebot
import mysql.connector

from telebot import types
from datetime import datetime

from mysql.connector import connect, Error
from threading import Thread

import genshinstats as gs

token = '53043877:AAE3kWe_OnJUWQG4at_-2i0'
bot = telebot.TeleBot(token)

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="user_info_genshin",
)

cursor = mydb.cursor()
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn1 = types.KeyboardButton("/set_cookie")
btn2 = types.KeyboardButton("/смола")
btn3 = types.KeyboardButton("/help")
btn4 = types.KeyboardButton("/abyss")
markup.add(btn1, btn4, btn3, btn2)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет', reply_markup=markup)

@bot.message_handler(commands=['set_cookie'])
def get_ltuid(message):
    bot.send_message(message.chat.id, 'Введи ltuid. Для отмены введите /cancel')
    info_list = ({})
    info_list.update({'id': str(message.from_user.id)})
    bot.register_next_step_handler(message, get_ltoken, info_list)

def get_ltoken(message, info_list):
    if (message.text == "/cancel"):
        return
    bot.send_message(message.chat.id, 'Введи ltoken. Для отмены введите /cancel')
    info_list.update({'ltuid': str(message.text)})
    bot.register_next_step_handler(message, get_uid, info_list)

def get_uid(message, info_list):
    if (message.text == "/cancel"):
        return
    bot.send_message(message.chat.id, 'Введи uid. Для отмены введите /cancel')
    info_list.update({'ltoken': str(message.text)})
    bot.register_next_step_handler(message, set_uid, info_list)

def set_uid(message, info_list):
    info_list.update({'uid': str(message.text)})
    if (message.text == "/cancel"):
        return
    sql_commit(info_list, message)
    bot.send_message(message.chat.id, 'Теперь вы можете узнать количесвто смолы')

def sql_commit(info_list, message):
    sql = "SELECT * FROM users WHERE (id = '" + str(info_list["id"]) + "')"
    cursor.execute(sql)
    result = cursor.fetchall()

    if (len(result) != 0):
        bot.send_message(info_list["id"],
                         "Информация о ваших cookie файлах уже есть, вы уверены что хотите перезаписать ее? да/нет")
        bot.register_next_step_handler(message, rewrite, info_list)
        return
    add_info(info_list)

def add_info(info_list):
    sql = "INSERT INTO users (id, ltoken, ltuid, uid) VALUES (%s, %s, %s, %s)"
    val = (str(info_list.get("id")), str(info_list.get("ltoken")), str(info_list.get("ltuid")), str(info_list.get("uid")))
    cursor.execute(sql, val)
    mydb.commit()

def rewrite(message, info_list):
    if(message.text.lower() == "нет"):
        info_list.update({"isTrue": '0'})
    elif(message.text.lower() == "да"):
        sql = "DELETE FROM users WHERE (id = " + str(info_list["id"]) + ")"
        cursor.execute(sql)
        mydb.commit()
        add_info(info_list)
    else:
        bot.send_message(message.from_user.id, "Введите да или нет")
        bot.register_next_step_handler(message, rewrite, info_list)

@bot.message_handler(commands=['смола'])
def get_smola_msg(message):
    get_smola(message.from_user.id)

def get_smola(id):
    user_info = get_user_data(id)
    gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
    info = gs.get_notes(str(user_info.get("uid")))

    time = int(info["until_resin_limit"])
    minutes = 0
    hours = 0
    while time >= 60:
        time -= 60
        minutes += 1
        if minutes >= 60:
            minutes -= 60
            hours += 1
    final = '<b>' + str(info["resin"]) + "/160</b>\n" + "Полное восстановление через: " + str(hours) + ' ч. ' + str(minutes) + ' мин.'
    bot.send_message(id, final, reply_markup=markup, parse_mode='HTML')

def get_user_data(id):
    get_cursor = mydb.cursor()
    user_info = ({})
    sql = "SELECT ltoken, ltuid, uid, isAlerted FROM users WHERE (id = " + str(id) + ")"
    get_cursor.execute(sql)
    try:
        list = get_cursor.fetchall()
        list = str(list).split('(')
        list = str(list[1]).split(')')
        list = str(list[0]).split(',')
        ltoken = list[0].split("'")
        ltuid = list[1].split("'")
        uid = list[2]
        user_info.update({'ltoken': ltoken[1]})
        user_info.update({'ltuid': ltuid[1]})
        user_info.update({'uid': int(uid)})
        user_info.update({'isAlerted': str(list[3])})
        mydb.commit()
        return user_info
    except:
        return "error"

def claim_reward(id):
    print('here')
    user_info = get_user_data(id)
    try:
        gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
        reward = gs.claim_daily_reward()
        if reward is not None:
            text = f"Награда за ежедневную отметку - {reward['cnt']}x {reward['name']} \n"
            photo = str(reward['icon'])
            bot.send_photo(id, photo)
            bot.send_message(id, text)
    except:
        return

def get_nickname(id):
    cursor = mydb.cursor()
    user_info = get_user_data(id)
    try:
        gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
        nick = gs.get_game_accounts()
        nick = str(nick).split("'nickname':")
        nick = str(nick[1]).split("'")
        nick = nick[1]
        sql = 'UPDATE users SET nickname = %s WHERE (id = %s)'
        val = (str(nick), str(id))
        cursor.execute(sql, val)
        mydb.commit()
    except:
        pass

def remind():
    remind_cursor = mydb.cursor()
    print("Updated: " + str(datetime.now()))
    sql = "SELECT id FROM users"
    remind_cursor.execute(sql)
    IDs = remind_cursor.fetchall()
    for id in IDs:
        id = str(id).split('(')
        id = str(id[1]).split(',')
        id = id[0]
        user_info = get_user_data(id)
        try:
            gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
            info = gs.get_notes(str(user_info.get("uid")))
            smola = info['resin']
            sql = "UPDATE users SET smola = %s WHERE (id = %s)"
            val = (str(smola), str(id))
            remind_cursor.execute(sql, val)
            get_nickname(id)
            damage(id)
            timeT = str(datetime.now()).split(" ")
            timeT = timeT[1].split(":")
            if (timeT[0] == "19"):
                claim_reward(id)
            if (smola >= 150):
                if(int(user_info.get('isAlerted')) == 0):
                    get_smola(id)
                    sql = "UPDATE users SET isAlerted = %s WHERE (id = %s)"
                    val = ('1', str(id))
                    remind_cursor.execute(sql, val)
            else:
                sql = "UPDATE users SET isAlerted = %s WHERE (id = %s)"
                val = ('0', str(id))
                remind_cursor.execute(sql, val)
        except:
            continue
    mydb.commit()
    time.sleep(1800)
    remind()

@bot.message_handler(commands=['abyss'])
def strike(message):
    user_info = get_user_data(message.from_user.id)
    if (user_info == "error"):
        bot.send_message(message.from_user.id, "Ошибка. Вы уверены что вы ввели ваши данные?")
        return
    try:
        gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
        check = gs.get_spiral_abyss(str(user_info.get("uid")))
        strike = check.get('character_ranks').get('strongest_strike')
        strike = str(strike).split("'value':")
        strike = strike[1].split(',')
        floor = str(check).split("'max_floor': ")
        floor = floor[1].split("'")
        if (str(floor[1]) == '0-0'):
            bot.send_message(message.from_user.id, 'Данные о бездне пока не доступны', reply_markup=markup)
        else:
            final = 'Самый сильный удар в текущей бездне:' + strike[0] + '\nМаксимальный этаж: ' + floor[1]
            bot.send_message(message.from_user.id, final, reply_markup=markup)
    except:
        try:
            gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
            check = gs.get_spiral_abyss(str(user_info.get("uid")))
            floor = str(check).split("'max_floor': ")
            floor = floor[1].split("'")
            if(str(floor[1]) == '0-0'):
                bot.send_message(message.from_user.id, 'Данные о бездне пока не доступны', reply_markup=markup)
            else:
                final = 'Самый сильный удар в текущей бездне: 0' + '\nМаксимальный этаж: ' + floor[1]
                bot.send_message(message.from_user.id, final, reply_markup=markup)
        except:
            bot.send_message(message.from_user.id, 'Произошла ошибка. Нет сведений о нынешней бездне.', reply_markup=markup)


def damage(id):
    cursor1 = mydb.cursor()
    try:
        user_info = get_user_data(id)
        gs.set_cookie(ltuid=str(user_info.get("ltuid")), ltoken=str(user_info.get("ltoken")))
        check = gs.get_spiral_abyss(str(user_info.get("uid")))
        strike = check.get('character_ranks').get('strongest_strike')
        strike = str(strike).split("'value':")
        strike = strike[1].split(',')
        sql = "UPDATE users SET strike = %s WHERE (id = %s)"
        val = (str(strike[0]), str(id))
        cursor1.execute(sql, val)
        floor = str(check).split("'max_floor': ")
        floor = floor[1].split("'")
        sql = "UPDATE users SET floor = %s WHERE (id = %s)"
        val = (str(floor[1]), str(id))
        cursor1.execute(sql, val)
        mydb.commit()
    except:
        pass

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.from_user.id,
                      "Для получения ltoken и ltuid перейдите на свою личную страницу в HoYoLab и там нажмите F12.\nПосле этого перейдите во вкладку 'console' и введите там 'document.cookie' после нажмите на enter.")
    bot.send_message(message.from_user.id,
                     "В результате ищите ltuid и ltoken. Также потребуется ваш UID который находится в правом нижнем углу в игре.")
    bot.send_message(message.from_user.id,
                     "После введения данных появится возможность узнать сколько у вас смолы командой /смола. Также ежедневно автоматически будет собираться награда за ежедневную отметку на сайте miHoYo. А также командой /abyss узнать самый сильный удар в текущей бездне.")

th = Thread(target=remind, args=())
th.start()

while True:
    try:
        bot.polling(none_stop=True, interval=0)
    except:
        time.sleep(5)
