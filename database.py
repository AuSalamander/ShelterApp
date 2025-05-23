import sqlite3
import os
import glob
import json

DB_NAME = "test_shelter.db"

def add_event_doc(event_id: int, filename: str):
    """Сохраняет в БД, что к событию прикреплён уже существующий файл filename."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO event_docs(event_id, filename)
        VALUES (?, ?)
    ''', (event_id, filename))
    conn.commit()
    conn.close()

def delete_event_doc(event_id: int, filename: str):
    """Удаляет только ссылку из БД, сам файл на диске остаётся."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM event_docs
          WHERE event_id = ? AND filename = ?
    ''', (event_id, filename))
    conn.commit()
    conn.close()

def get_event_docs(event_id: int):
    """Возвращает список имён файлов, сохранённых в БД для этого события."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT filename
          FROM event_docs
         WHERE event_id = ?
         ORDER BY filename
    ''', (event_id,))
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows

def update_event_field(event_id: int, field: str, value):
    """
    Обновляет одно поле в таблице events.
    field — 'type', 'date_start', 'date_end' или 'conclusion'.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if field not in ('type','date_start','date_end','conclusion','results'):
        conn.close()
        raise ValueError("Недопустимое поле")
    cur.execute(f"UPDATE events SET {field} = ? WHERE id = ?", (value, event_id))
    conn.commit()
    conn.close()

def update_event_results(event_id: int, results_json: str):
    """
    Перезаписывает колонку results для события event_id.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        UPDATE events
           SET results = ?
         WHERE id = ?
    ''', (results_json, event_id))
    conn.commit()
    conn.close()


def add_event(animal_id: int,
              etype: str,
              date_start: str,
              date_end: str = None,
              conclusion: str = None,
              results: str = None):
    """
    Добавляет новое событие для животного.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # results — либо строка JSON, либо None
    r = results if isinstance(results, str) else (json.dumps(results) if results else None)
    cur.execute('''
        INSERT INTO events
            (animal_id, type, date_start, date_end, conclusion, results)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (animal_id, etype, date_start, date_end, conclusion, r))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_animal_events(animal_id: int):
    """
    Возвращает только неудалённые события
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT type, date_start, date_end, conclusion, results, id
        FROM events
        WHERE animal_id = ? 
          AND deleted = 0
        ORDER BY date_start
    ''', (animal_id,))
    rows = cur.fetchall()
    conn.close()

    docs_dir = os.path.join('docs', str(animal_id))
    
    events = []
    for etype, ds, de, concl, results, eid in rows:
        event_docs = get_event_docs(eid)
        # Исправлено: нормализация путей для кроссплатформенности
        event_docs = [os.path.normpath(os.path.join(docs_dir, fn)) for fn in event_docs]
        
        events.append((
            etype,
            ds,
            de,
            concl or "",
            event_docs,
            results or "",
            eid
        ))
    return events


def update_adoption_field(animal_id, field, value):
    """
    Обновляет поле усыновления для животного
    """
    allowed_fields = {
        'adoption_date', 
        'owner_name', 
        'owner_contact',
        "arrival_date",
        "name",
        "species",
        "birth_date",
    }
    
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле для усыновления: {field}")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f'''
        UPDATE animals
        SET {field} = ?
        WHERE id = ? AND adopted = 1
    ''', (value, animal_id))
    conn.commit()
    conn.close()

def init_db():
    """
    Создаёт таблицы с поддержкой мягкого удаления и добавляет колонки
    к существующим таблицам при необходимости.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # --- animals ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT,
            birth_date TEXT,
            age_estimated INTEGER NOT NULL DEFAULT 0,
            arrival_date TEXT,
            cage_number TEXT,
            quarantine_until TEXT,
            deleted INTEGER NOT NULL DEFAULT 0,
            adopted INTEGER NOT NULL DEFAULT 0,          -- Флаг усыновления
            adoption_date TEXT,                          -- Дата усыновления
            owner_name TEXT,                              -- Имя владельца
            owner_contact TEXT                            -- Контакты владельца
        )
    ''')

    # Получаем список всех колонок один раз
    cur.execute("PRAGMA table_info(animals)")
    existing_columns = {row[1] for row in cur.fetchall()}

    # Добавляем все недостающие колонки
    columns_to_add = [
        ('deleted', 'INTEGER NOT NULL DEFAULT 0'),
        ('adopted', 'INTEGER NOT NULL DEFAULT 0'),
        ('adoption_date', 'TEXT'),
        ('owner_name', 'TEXT'),
        ('owner_contact', 'TEXT')
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            cur.execute(f'ALTER TABLE animals ADD COLUMN {col_name} {col_type}')

    # --- events ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id   INTEGER NOT NULL,
            type        TEXT    NOT NULL,
            date_start  TEXT    NOT NULL,
            date_end    TEXT,
            conclusion  TEXT,
            results     TEXT,
            deleted     INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Проверяем существование колонки deleted в events
    cur.execute("PRAGMA table_info(events)")
    columns = [row[1] for row in cur.fetchall()]
    if 'deleted' not in columns:
        cur.execute('ALTER TABLE events ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0')

    # --- medical ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS medical (
            animal_id       INTEGER PRIMARY KEY,
            quarantine_days INTEGER DEFAULT 0,
            notes           TEXT DEFAULT ''
        )
    ''')

    # --- procedures ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS procedures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id    INTEGER,
            type         TEXT,
            scheduled    TEXT,
            completed    INTEGER,
            completed_at TEXT,
            result       TEXT
        )
    ''')

    # --- event_docs ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS event_docs (
            event_id   INTEGER NOT NULL,
            filename   TEXT    NOT NULL,
            PRIMARY KEY(event_id, filename),
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')

    conn.commit()
    conn.close()

def add_adoption(animal_id, owner_name, owner_contact, adoption_date):
    """
    Помечает животное как усыновленное и сохраняет данные владельца
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        UPDATE animals
        SET adopted = 1,
            adoption_date = ?,
            owner_name = ?,
            owner_contact = ?
        WHERE id = ? AND deleted = 0 AND adopted = 0
    ''', (adoption_date, owner_name, owner_contact, animal_id))
    conn.commit()
    conn.close()

def get_animal_by_id(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            id, name, species, birth_date, 
            age_estimated, arrival_date, 
            cage_number, quarantine_until,
            deleted, adopted, adoption_date,
            owner_name, owner_contact
        FROM animals
        WHERE id = ? AND deleted = 0 AND adopted = 0
    ''', (animal_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_all_adoptions():
    """
    Возвращает всех усыновленных животных
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, species, birth_date, age_estimated,
               arrival_date, adoption_date, owner_name, owner_contact
        FROM animals
        WHERE adopted = 1 AND deleted = 0
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_animals():
    """
    Возвращает только неудалённых животных
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT id, name, species, birth_date, age_estimated,
               arrival_date, cage_number, quarantine_until
        FROM animals
        WHERE deleted = 0 AND adopted = 0
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_cage_numbers():
    """
    Возвращает клетки только неудалённых животных
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT cage_number 
        FROM animals 
        WHERE cage_number IS NOT NULL 
          AND deleted = 0 AND adopted = 0
    ''')
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows

def add_animal(name, species, birth_date, age_estimated,
               arrival_date, cage_number, quarantine_until):
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
    new_id = cur.lastrowid
    conn.close()
    return new_id  # Исправлено: убрано дублирование return


def delete_animal(animal_id):
    """Мягкое удаление животного (устанавливает флаг deleted)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE animals SET deleted = 1 WHERE id = ?', (animal_id,))
    conn.commit()
    conn.close()

def delete_event(event_id: int):
    """Мягкое удаление события (устанавливает флаг deleted)"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE events SET deleted = 1 WHERE id = ?', (event_id,))
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

def get_all_animals_ids():
    """Возвращает ID и имена только неудалённых животных"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM animals WHERE deleted = 0 AND adopted = 0")
    out = cur.fetchall()
    conn.close()
    return out
