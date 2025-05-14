import sqlite3

DB_NAME = 'shelter.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # 1) создаём таблицу, если её совсем нет
    cur.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT
        )
    ''')
    # 2) узнаём, какие колонки есть
    cur.execute("PRAGMA table_info(animals)")
    existing = {row[1] for row in cur.fetchall()}

    # 3) добавляем недостающие столбцы по очереди
    if 'birth_date' not in existing:
        cur.execute("ALTER TABLE animals ADD COLUMN birth_date TEXT")
    if 'age_months' not in existing:
        cur.execute("ALTER TABLE animals ADD COLUMN age_months INTEGER NOT NULL DEFAULT 0")
    if 'age_estimated' not in existing:
        cur.execute("ALTER TABLE animals ADD COLUMN age_estimated INTEGER NOT NULL DEFAULT 0")
    if 'arrival_date' not in existing:
        cur.execute("ALTER TABLE animals ADD COLUMN arrival_date TEXT")

    conn.commit()
    conn.close()

def add_animal(name, species, birth_date, age_months, age_estimated, arrival_date):
    """
    Добавляет животное с учётом даты рождения или оценки возраста.
    birth_date: строка 'YYYY-MM-DD' или None
    age_months: целое число месяцев
    age_estimated: 1 если это оценка, 0 если вычислено из birth_date
    arrival_date: строка 'YYYY-MM-DD'
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO animals
            (name, species, birth_date, age_months, age_estimated, arrival_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, species, birth_date, age_months, age_estimated, arrival_date))
    conn.commit()
    conn.close()

def get_all_animals():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, species, birth_date, age_months, age_estimated, arrival_date
        FROM animals
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

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
