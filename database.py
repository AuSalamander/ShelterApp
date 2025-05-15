import sqlite3

DB_NAME = 'shelter.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Создаём таблицу, если её нет
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
