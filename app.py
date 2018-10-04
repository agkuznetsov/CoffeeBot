from flask import Flask, request, jsonify
import csv
import json
import random
from datetime import datetime
from collections import Counter
from threading import Lock


USERS_PATH = 'CoffeeBot/data/users.csv'
CUPS_PATH = 'CoffeeBot/data/cups.csv'
LOG_PATH = 'CoffeeBot/log/requests.txt'

HELP_MESSAGE = 'Приятного кофепития, {}!'

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

keyboard_main = {
        'parse_mode': 'Markdown',
        'reply_markup':  {'keyboard':[['Выпить кофейку'],['Статистика']]}
    }

ok_messages = [
                'Приятного!',
                'Ок',
                'Done',
                'Хорошо!',
                'Как скажете!',
                '+1'
            ]

wrong_passwd_messages = [
        'Не подходит. Попробуйте ещё!',
        'Ну, нет. Есть идеи?',
        'Давайте попробуем ещё раз'
    ]

def get_registred_users():
    '''
    Read registred users data from csv (all in state registered)
    '''
    users = set()

    with open(USERS_PATH, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 0:
                users.add(row[0])

    return { user:'registered' for user in users }

def get_stats():
    '''
    Output drunk coffee cups per user
    '''

    cups = []

    with open(CUPS_PATH, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 0:
                cups.append(row[0])

    if len(cups) == 0:
        return 'Пока никто не выпил ни одной чашки!'

    user_names = dict()

    with open(USERS_PATH, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1:
                user_names[row[0]] = row[1]

    return '\n'.join(
        ['{} - {}'.format(name, count)
            for name, count in sorted({
                user_names[username]: count
                    for username, count
                        in Counter(cups).items()}.items())]
        )

def check_registraion(user):
    '''
    Check if user already registred
    '''
    return user in users

def check_password(passwd):
    '''
    Password check for registration process
    '''
    return passwd.strip().title() == 'Осень'

def get_random_message(messages):
    '''
    Select random message from list. Useful for same type messages
    '''
    return random.choice(messages)

def write_user(username, name):
    '''
    Store user and registration dates
    '''
    with lock:
        with open(USERS_PATH, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([username, name, datetime.now()])

def write_cup(username):
    '''
    Store cup drunk by user
    '''
    with lock:
        with open(CUPS_PATH, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([username, datetime.now()])

def proccess_message(data):
    '''
    Process telegram messages
    '''

    # Check if message type is text. Could be image etc
    if not 'text' in data['message']:
        return 'OK'

    chat_id = data['message']['chat']['id']

    if 'username' in data['message']['chat']:
        username = data['message']['chat']['username']
    else:
        username = data['message']['chat']['first_name']

    user_text = data['message']['text']

    message_base = {
        'method': 'sendMessage',
        'chat_id': chat_id
    }

    keyboard = {}

    # Check if user already communicated with bot
    if username in users:
        # Authentification by password
        if users[username] == 'asking_for_pass':
            if not check_password(user_text):
                text = get_random_message(wrong_passwd_messages)
            else:
                text = 'Да. Добро пожаловать! Как вас зовут?'
                users[username] = 'asking_for_name'
        # Setting username
        elif users[username] == 'asking_for_name':
                name = user_text
                # Need to write down user data to users.csv
                write_user(username, name)
                text = 'Приятного кофепития, {}!'.format(name)
                users[username] = 'registered'
                keyboard = keyboard_main
        # Select user action
        elif users[username] == 'registered':
                if user_text in ['Выпить кофейку', '/drink']:
                    write_cup(username)
                    text = get_random_message(ok_messages)
                elif user_text in ['Статистика', '/stats']:
                    text = get_stats()
                else:
                    text = 'Может, по кофе?'
                keyboard = keyboard_main
    else:
        text = 'Похоже, мы ещё не знакомы! Знаете кодовое слово?'
        users[username] = 'asking_for_pass'

    return {**message_base, **keyboard, 'text': text }

users = get_registred_users()
app = Flask(__name__)
lock = Lock()


@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    '''
    Webhook for telegram bot. Teleagram use it for passing messages from users
    '''

    data = request.get_json()

    with open(LOG_PATH, 'a') as f:
        json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write('\n')

    message = proccess_message(data)

    with open(LOG_PATH, 'a') as f:
        json.dump(message, f, indent=4, ensure_ascii=False, sort_keys=True)
        f.write('\n')

    return jsonify(message)
