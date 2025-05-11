import sqlite3

DB_NAME = 'shelter.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT,
            age INTEGER,
            arrival_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_animal(name, species, age, arrival_date):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO animals (name, species, age, arrival_date)
        VALUES (?, ?, ?, ?)
    ''', (name, species, age, arrival_date))
    conn.commit()
    conn.close()

def get_all_animals():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM animals')
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_animal(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('DELETE FROM animals WHERE id = ?', (animal_id,))
    conn.commit()
    conn.close()
