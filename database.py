import sqlite3
import os
import glob

DB_NAME = 'shelter.db'

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
    cur.execute('''
        INSERT INTO events
            (animal_id, type, date_start, date_end, conclusion, results)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (animal_id, etype, date_start, date_end, conclusion, results))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_animal_events(animal_id: int):
    """
    Возвращает список кортежей:
      (type, date_start, date_end_or_None,
       conclusion_or_empty, doc_paths_list, results_or_empty)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT type, date_start, date_end, conclusion, results, id
        FROM events
        WHERE animal_id = ?
        ORDER BY date_start
    ''', (animal_id,))
    rows = cur.fetchall()           # ← вот здесь получаем rows
    conn.close()

    # Папка с документами для этого животного
    docs_dir = os.path.join('docs', str(animal_id))

    events = []
    for etype, ds, de, concl, results, eid in rows:
        # для каждого события только свои файлы
        if os.path.isdir(docs_dir):
            event_docs = [
                p for p in glob.glob(f"{docs_dir}/*")
                if os.path.basename(p).startswith(f"{eid}_")
            ]
        else:
            event_docs = []

        events.append((
            etype,
            ds,
            de,
            concl or "",
            event_docs,
            results or "",
            eid                # <-- добавили сюда
        ))
    return events


def update_adoption_field(adoption_id, field, value):
    """
    Обновляет одно из полей в таблице adoptions:
      owner_name, owner_contact или adoption_date
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Список разрешённых полей
    if field not in ("owner_name", "owner_contact", "adoption_date"):
        conn.close()
        raise ValueError(f"Недопустимое поле для обновления: {field}")

    cur.execute(
        f'UPDATE adoptions SET {field} = ? WHERE id = ?',
        (value, adoption_id)
    )
    conn.commit()
    conn.close()

def init_db():
    """
    Создаёт, если надо, все таблицы: animals, adoptions, medical, procedures.
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
            quarantine_until TEXT
        )
    ''')

    # --- adoptions ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS adoptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            name TEXT,
            species TEXT,
            birth_date TEXT,
            age_estimated INTEGER,
            arrival_date TEXT,
            owner_name TEXT NOT NULL,
            owner_contact TEXT NOT NULL,
            adoption_date TEXT NOT NULL,
            FOREIGN KEY(animal_id) REFERENCES animals(id)
        )
    ''')

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

    # --- events ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id   INTEGER NOT NULL,
            type        TEXT    NOT NULL,
            date_start  TEXT    NOT NULL,
            date_end    TEXT,           -- может быть NULL
            conclusion  TEXT,
            results     TEXT            -- свободный текст/числа в JSON или CSV
            -- внешний ключ на animals не обязателен, но можно добавить:
            -- , FOREIGN KEY(animal_id) REFERENCES animals(id)
        )
    ''')

    conn.commit()
    conn.close()

def add_adoption(animal_id, name, species, birth_date, age_estimated,
                 arrival_date, owner_name, owner_contact, adoption_date):
    """
    Сохраняет snapshot данных животного вместе с информацией о новом владельце.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO adoptions
            (animal_id, name, species, birth_date, age_estimated,
             arrival_date, owner_name, owner_contact, adoption_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (animal_id, name, species, birth_date, age_estimated,
          arrival_date, owner_name, owner_contact, adoption_date))
    conn.commit()
    conn.close()

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
    Возвращает все записи из таблицы adoptions:
      (id, animal_id, name, species, birth_date,
       age_estimated, arrival_date, owner_name,
       owner_contact, adoption_date)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT
            id, animal_id, name, species,
            birth_date, age_estimated, arrival_date,
            owner_name, owner_contact, adoption_date
        FROM adoptions
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

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
    return new_id


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

def get_all_animals_ids():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM animals")
    out = cur.fetchall()
    conn.close()
    return out  # list of (id, name)

def get_medical(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT quarantine_days, notes FROM medical WHERE animal_id=?", (animal_id,))
    row = cur.fetchone()
    conn.close()
    return row or (0, '')

def upsert_medical(animal_id, quarantine_days, notes):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
      INSERT INTO medical(animal_id, quarantine_days, notes)
        VALUES (?, ?, ?)
      ON CONFLICT(animal_id) DO UPDATE
        SET quarantine_days=?, notes=?
    ''', (animal_id, quarantine_days, notes, quarantine_days, notes))
    conn.commit()
    conn.close()

def get_procedures(animal_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
      SELECT id, type, scheduled, completed, completed_at, result
      FROM procedures WHERE animal_id=?
      ORDER BY scheduled
    ''', (animal_id,))
    out = cur.fetchall()
    conn.close()
    return out

def schedule_procedure(animal_id, type_, scheduled_iso):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
      INSERT INTO procedures(animal_id,type,scheduled,completed)
      VALUES (?,?,?,0)
    ''', (animal_id, type_, scheduled_iso))
    conn.commit()
    conn.close()

def complete_procedure(proc_id, completed_at_iso, result_text):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
      UPDATE procedures
      SET completed=1, completed_at=?, result=?
      WHERE id=?
    ''', (completed_at_iso, result_text, proc_id))
    conn.commit()
    conn.close()


