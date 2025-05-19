import sqlite3

DB_NAME = 'shelter.db'

def get_animal_by_id(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, species, birth_date, age_estimated,
               arrival_date, cage_number, quarantine_until
        FROM animals
        WHERE id = ?
    ''', (animal_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_all_adoptions():
    """
    Возвращает список всех записей из таблицы adoptions:
    (id, animal_id, owner_name, owner_contact, adoption_date)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, animal_id, owner_name, owner_contact, adoption_date
        FROM adoptions
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def init_db():
    """
    Создаёт (при необходимости) таблицы animals и adoptions
    """
    # 1) открываем соединение и курсор
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 2) создаём таблицу animals
    cur.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT,
            birth_date TEXT,
            age_estimated INTEGER NOT NULL DEFAULT 0,
            arrival_date TEXT,
            cage_number TEXT,
            quarantine_until TEXT
        )
    ''')

    # 3) создаём таблицу adoptions
    cur.execute('''
        CREATE TABLE IF NOT EXISTS adoptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            owner_name TEXT NOT NULL,
            owner_contact TEXT NOT NULL,
            adoption_date TEXT NOT NULL,
            FOREIGN KEY(animal_id) REFERENCES animals(id)
        )
    ''')

    # 4) фиксируем и закрываем
    conn.commit()
    conn.close()

def get_all_animals():
    """
    Возвращает кортежи:
    (id, name, species, birth_date, age_estimated, arrival_date, cage_number, quarantine_until)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, species, birth_date, age_estimated,
               arrival_date, cage_number, quarantine_until
        FROM animals
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_cage_numbers():
    """
    Возвращает список всех занятых cage_number (строки) из БД.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT cage_number FROM animals WHERE cage_number IS NOT NULL')
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows

def add_animal(name, species, birth_date, age_estimated,
               arrival_date, cage_number, quarantine_until):
    """
    Добавляет животное с указанием клетки и срока карантина.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO animals
            (name, species, birth_date, age_estimated,
             arrival_date, cage_number, quarantine_until)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, species, birth_date, age_estimated,
          arrival_date, cage_number, quarantine_until))
    conn.commit()
    conn.close()


def delete_animal(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM animals WHERE id = ?', (animal_id,))
    conn.commit()
    conn.close()

def update_animal_field(animal_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # осторожно: field берётся из доверенной мапы, не из пользовательского ввода
    query = f'UPDATE animals SET {field} = ? WHERE id = ?'
    cur.execute(query, (value, animal_id))
    conn.commit()
    conn.close()

def add_adoption(animal_id, owner_name, owner_contact, adoption_date):
    """
    Сохраняет информацию о передаче животного (adoption).
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO adoptions
            (animal_id, owner_name, owner_contact, adoption_date)
        VALUES (?, ?, ?, ?)
    ''', (animal_id, owner_name, owner_contact, adoption_date))
    conn.commit()
    conn.close()

