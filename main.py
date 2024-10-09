import telebot
from telebot import types
import psycopg2 as ps
import os
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

winner = ''  # победитель
map_type = ''  # карта
win_rate = ''  # ретинг побед
not_winners = []
maps = ['стандартная', 'зеленая', 'синяя']
bot = telebot.TeleBot(bot_token)

def create_connection():
    connection = None
    try:
        connection = ps.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        print("connection to postgres successful")
    except ps.OperationalError as e:
        print(f"error {e}")

    return connection


def init_db():
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'gamestat'
        );
    """)
    gamestat_exists = cur.fetchone()[0]

    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'playerstat'
        );
    """)
    playerstat_exists = cur.fetchone()[0]

    if not gamestat_exists or not playerstat_exists:
        req1 = '''
        CREATE TABLE IF NOT EXISTS gamestat(
            game_id SERIAL PRIMARY KEY,
            winner VARCHAR(255) NOT NULL,
            map_type VARCHAR(255) NOT NULL,
            winner_rate INT
        );
        '''

        req2 = '''
        CREATE TABLE IF NOT EXISTS playerstat(
            player_name VARCHAR(255) NOT NULL PRIMARY KEY,
            average_winrate REAL,
            number_of_victory INTEGER,
            number_of_games INTEGER
        );
        '''

        cur.execute(req1)
        cur.execute(req2)

    conn.commit()
    cur.close()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    bot.send_message(message.chat.id, "бот настроен и подключен к базе")
    bot.send_message(message.chat.id, "бот ждет картинку с результатом игры", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(content_types=["photo", "document"])
def send_welcome(message):
    bot.send_message(message.chat.id, 'Давайте зарегестрируем новую игру', reply_markup=types.ReplyKeyboardRemove())
    fist_step(message)


@bot.message_handler(commands=['register_game'])
def register_game(message):
    bot.send_message(message.chat.id, 'Давайте зарегестрируем новую игру')
    fist_step(message)


@bot.message_handler(commands=['what_map'])
def what_map(message):
    conn = create_connection()
    cur = conn.cursor()

    req = '''
        SELECT map_type, COUNT(map_type) AS count_value
        FROM (
            SELECT map_type
            FROM gamestat
            ORDER BY game_id DESC
            LIMIT 10
        ) AS last_ten_records
        GROUP BY map_type
        ORDER BY count_value ASC
        LIMIT 1;
    '''

    cur.execute(req)
    unpopular_map = cur.fetchall()
    print(unpopular_map)
    conn.commit()
    cur.close()
    conn.close()

    if unpopular_map:
        map_type = unpopular_map[0][0]
        print(map_type)
        if map_type == 'стандартная':
            message_text = "🏆Выберите стандартную карту в новой игры!"
        elif map_type == 'зеленая':
            message_text = "🌳Зеленая карта — это природа и тактика!"
        elif map_type == 'синяя':
            message_text = "🌊Синяя карта — это море возможностей!"
        else:
            message_text = "Игра завершена на неизвестной карте."

        bot.send_message(message.chat.id, message_text, reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Не удалось определить карту.")


@bot.message_handler(commands=['games_statistics'])
def games_statistics(message):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM gamestat;")
    total_games = cur.fetchone()[0]

    cur.execute("SELECT map_type, COUNT(*) FROM gamestat GROUP BY map_type;")
    map_types = cur.fetchall()

    cur.execute("""
        SELECT map_type, COUNT(*) AS wins 
        FROM gamestat 
        GROUP BY map_type 
        ORDER BY wins DESC 
        LIMIT 3;
    """)
    top_maps = cur.fetchall()

    cur.execute("""
        SELECT winner, COUNT(*) AS wins 
        FROM gamestat 
        GROUP BY winner 
        ORDER BY wins DESC 
        LIMIT 3;
    """)
    top_winners = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    response = f"""
📊 Статистика игр:

Общее количество игр: {total_games}

Количество игр по типам карт:
"""

    for map_type, count in map_types:
        response += f"{map_type}: {count}\n"

    response += "\nТоп-3 победителей:\n"

    for winner, wins in top_winners:
        response += f"{winner}: {wins} побед\n"

    bot.send_message(message.chat.id, response, reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['players_statistics'])
def players_statistics(message):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT player_name, number_of_victory 
        FROM playerstat
        ORDER BY number_of_victory DESC 
        LIMIT 3;
    """)
    top_players = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    response = "🏆 Лидеры по количеству побед:\n\n"

    for player_name, victories in top_players:
        response += f"{player_name}: {victories} побед\n"

    bot.send_message(message.chat.id, response)
#---------------
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT player_name, average_winrate 
        FROM playerstat 
        ORDER BY average_winrate DESC 
        LIMIT 3;
    """)
    top_players_by_winrate = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    response = "📈 Лидеры по среднему победному рейтингу:\n\n"

    for player_name, winrate in top_players_by_winrate:
        response += f"{player_name}: {winrate:.2f}\n"

    bot.send_message(message.chat.id, response)
#------------------
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT player_name, average_winrate, number_of_victory, number_of_games "
                "FROM playerstat;")
    players_stats = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    response = "👤 Статистика игроков:\n\n"

    for player_name, winrate, victories, games in players_stats:
        if games > 0:
            win_percentage = (victories / games) * 100
        else:
            win_percentage = 0

        response += (f"Игрок: {player_name}\n"
                     f"Средний винрейт: {winrate:.2f}\n"
                     f"Количество побед: {victories}\n"
                     f"Количество игр: {games}\n"
                     f"Процент побед: {win_percentage:.2f}%\n\n")

    bot.send_message(message.chat.id, response, reply_markup=types.ReplyKeyboardRemove())

def fist_step(message):
    global not_winners
    not_winners = []
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    conn = create_connection()
    cur = conn.cursor()
    select_req = '''
            SELECT player_name FROM playerstat;
        '''
    cur.execute(select_req)
    names = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()

    for i in range(0, len(names), 2):
        row_buttons = []
        row_buttons.append(types.KeyboardButton(names[i][0]))
        if i + 1 < len(names):
            row_buttons.append(types.KeyboardButton(names[i + 1][0]))
        markup.row(*row_buttons)

    bot.send_message(message.chat.id, 'Кто победил?', reply_markup=markup)
    bot.register_next_step_handler(message, reg_winner)


def reg_winner(message):
    global winner
    winner = message.text.lower()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Стандартная карта')
    markup.add(item1)
    item2 = types.KeyboardButton('Синяя карта')
    markup.add(item2)
    item3 = types.KeyboardButton('Зеленая карта')
    markup.add(item3)
    bot.send_message(message.from_user.id, "Какая карта?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_map)


def reg_map(message):
    global map_type

    if message.text == 'Стандартная карта':
        map_type = 'стандартная'
    elif message.text == 'Синяя карта':
        map_type = 'синяя'
    elif message.text == 'Зеленая карта':
        map_type = 'зеленая'

    bot.send_message(message.from_user.id, "Количество очков победителя", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_win_rate)


def reg_win_rate(message):
    global win_rate
    win_rate = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    key1 = types.KeyboardButton('Да')
    key2 = types.KeyboardButton('Нет')
    markup.add(key1, key2)
    bot.send_message(message.from_user.id, f'победил {winner} с рейтингом {win_rate} на {map_type} картa')
    bot.send_message(message.chat.id, 'Все верно?', reply_markup=markup)
    bot.register_next_step_handler(message, reg_game)


def reg_game(message):
    if message.text.lower() == 'да':
        reg_game_to_db(message)
    elif message.text.lower() == 'нет':
        bot.send_message(message.chat.id, 'Давайте начнем регистрацию заново')
        fist_step(message)
    else:
        bot.send_message(message.chat.id, 'Необходимо ответить Да или Нет')
        bot.register_next_step_handler(message, reg_game)


def reg_game_to_db(message):
    conn = create_connection()
    cur = conn.cursor()
    req = '''
        INSERT INTO gamestat (winner, map_type, winner_rate)
        VALUES(%s, %s, %s);
    '''
    records_to_insert = (winner, map_type, win_rate)
    cur.execute(req, records_to_insert)
    conn.commit()
    cur.close()
    conn.close()

    bot.send_message(message.chat.id, 'Игра добавлена', reply_markup=types.ReplyKeyboardRemove())

    # Создание разметки с кнопками
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    conn = create_connection()
    cur = conn.cursor()
    select_req = f'''
        SELECT player_name 
        FROM playerstat
        WHERE player_name != '{winner}';
    '''
    cur.execute(select_req)
    names = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()

    # Добавление кнопок по 2 в ряд
    for i in range(0, len(names), 2):
        row_buttons = []
        # Добавляем до двух кнопок в строку
        row_buttons.append(types.KeyboardButton(names[i][0]))  # Первая кнопка
        if i + 1 < len(names):  # Проверяем, есть ли вторая кнопка
            row_buttons.append(types.KeyboardButton(names[i + 1][0]))  # Вторая кнопка
        markup.row(*row_buttons)  # Добавляем строку с кнопками

    item_not = types.KeyboardButton('Больше никто')
    markup.add(item_not)  # Добавляем кнопку "Больше никто"

    bot.send_message(message.chat.id, 'Кто участвовал в игре?', reply_markup=markup)
    bot.register_next_step_handler(message, ask_other_players)


def ask_other_players(message):
    global not_winners
    if message.text.lower() != 'больше никто':
        if message.text not in not_winners:
            not_winners.append(message.text.lower())
        else:
            bot.send_message(message.chat.id, 'Этот игрок уже участвует в этой игре')
            return show_player_selection(message)

        # Проверка на максимальное количество игроков
        if len(not_winners) >= 4:
            bot.send_message(message.chat.id, "Вы уже выбрали 4 игрока. Больше нельзя добавлять.")
            print(not_winners)
            reg_player_to_db(message)
            return

    else:
        bot.send_message(message.chat.id, "Хорошо, тогда добавляю", reply_markup=types.ReplyKeyboardRemove())
        print(not_winners)
        reg_player_to_db(message)
        return

    # Показать оставшихся игроков
    show_player_selection(message)


def show_player_selection(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    conn = create_connection()
    cur = conn.cursor()
    select_req = f'''
        SELECT player_name 
        FROM playerstat
        WHERE player_name != '{winner}';
    '''
    cur.execute(select_req)
    names = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()

    # Список для временного хранения кнопок
    row_buttons = []

    # Добавление кнопок по 2 в ряд, исключая уже выбранных игроков
    for name in names:
        player_name = name[0].lower()  # Приводим к нижнему регистру для сравнения
        if player_name not in not_winners:  # Проверяем, был ли игрок уже выбран
            row_buttons.append(types.KeyboardButton(name[0]))
            # Если в строке уже 2 кнопки, добавляем их в разметку и очищаем список
            if len(row_buttons) == 2:
                markup.add(*row_buttons)
                row_buttons.clear()

    # Если осталась одна кнопка, добавляем её
    if row_buttons:
        markup.add(*row_buttons)

    item_not = types.KeyboardButton('Больше никто')
    markup.add(item_not)

    bot.send_message(message.chat.id, 'Кто ещё?', reply_markup=markup)
    bot.register_next_step_handler(message, ask_other_players)

def reg_player_to_db(message):
    global win_rate
    conn = create_connection()
    cur = conn.cursor()
    get_winner_stat = f'''
        SELECT average_winrate, number_of_victory, number_of_games
        FROM playerstat
        WHERE player_name = '{winner}';
    '''
    insert_winner = '''
        INSERT INTO playerstat(player_name, average_winrate, number_of_victory, number_of_games)
        VALUES(%s, %s, %s, %s)
    '''
    update_winner = '''
        UPDATE playerstat 
        SET 
        average_winrate = %s,
        number_of_victory = %s,
        number_of_games = %s
        WHERE player_name = %s;
    '''
    get_player_stat = '''
        SELECT number_of_games
        FROM playerstat
        WHERE player_name = %s;
    '''
    insert_player_stat = '''
        INSERT INTO playerstat (player_name, average_winrate, number_of_victory, number_of_games) 
        VALUES (%s, %s, %s, %s)
    '''
    update_player_stat = '''
        UPDATE playerstat SET
        number_of_games = %s
        WHERE player_name = %s;
    '''
    cur.execute(get_winner_stat)
    stat = cur.fetchall()
    if not stat:
        data = (winner, win_rate, 1, 1)
        cur.execute(insert_winner, data)
    else:
        current_average_winrate = float(stat[0][0])
        current_number_of_victories = int(stat[0][1])
        current_number_of_games = int(stat[0][2])
        win_rate = float(win_rate)
        if current_average_winrate == 0:
            new_average_winrate = win_rate
        else:
            new_average_winrate = (current_average_winrate + win_rate) / 2
        data = (new_average_winrate, current_number_of_victories + 1, current_number_of_games + 1, winner)
        cur.execute(update_winner, data)

    for rec in not_winners:
        cur.execute(get_player_stat, (rec,))
        stat = cur.fetchone()

        if stat:
            current_games = stat[0] + 1
            dat = (current_games, rec)
            cur.execute(update_player_stat, dat)
        else:
            dat = (rec, 0, 0, 1)
            cur.execute(insert_player_stat, dat)

    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Игра добавлена в базу и статичтики обновлены",
                     reply_markup=types.ReplyKeyboardRemove())


# bot.polling(none_stop=True, timeout=123)
bot.infinity_polling()
