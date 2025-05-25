import unittest
import sqlite3
import os
import tempfile
from datetime import date
import database as db
import json

class TestShelterDB(unittest.TestCase):
    def setUp(self):
        """Создание временной БД и инициализация таблиц."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        db.DB_NAME = self.db_path
        db.init_db()
        
        # Добавление тестовых данных
        self.animal_id = db.add_animal(
            "TestAnimal", "Dog", "2020-01-01", 2,
            "2022-01-01", "A1", "2022-02-01"
        )
        self.animal_id2 = db.add_animal(
            "TestAnimal2", "Cat", None, 3,
            "2022-02-01", None, None
        )
        # Добавление тестового события
        self.event_id = db.add_event(
            self.animal_id, "vaccination", "2023-01-01",
            date_end="2023-01-02", conclusion="All good",
            results={"status": "completed"}
        )


    def tearDown(self):
        """Удаление временной БД."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_init_db_tables_created(self):
        """Проверка создания таблиц при инициализации БД."""
        conn = sqlite3.connect(db.DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
        
        expected_tables = {
            'animals',
            'events', 'event_docs'
        }
        self.assertTrue(expected_tables.issubset(tables))

    def test_add_and_get_animal(self):
        """Проверка добавления и получения животного."""
        animal = db.get_animal_by_id(self.animal_id)
        self.assertEqual(animal[1], "TestAnimal")
        self.assertEqual(animal[2], "Dog")

    def test_add_event_doc(self):
        """Проверка добавления документа к событию."""
        db.add_event_doc(self.event_id, "test_doc.txt")
        docs = db.get_event_docs(self.event_id)
        self.assertIn("test_doc.txt", docs)
        
        # Проверка отсутствия дубликатов
        db.add_event_doc(self.event_id, "test_doc.txt")
        self.assertEqual(len(docs), 1)

    def test_delete_event_doc(self):
        """Проверка удаления документа из события."""
        db.add_event_doc(self.event_id, "to_delete.txt")
        db.delete_event_doc(self.event_id, "to_delete.txt")
        docs = db.get_event_docs(self.event_id)
        self.assertNotIn("to_delete.txt", docs)

    def test_update_event_field_valid(self):
        """Проверка обновления допустимого поля события."""
        db.update_event_field(self.event_id, "type", "checkup")
        conn = sqlite3.connect(db.DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT type FROM events WHERE id=?", (self.event_id,))
        self.assertEqual(cur.fetchone()[0], "checkup")
        conn.close()

    def test_update_event_field_invalid(self):
        """Проверка исключения при недопустимом поле."""
        with self.assertRaises(ValueError):
            db.update_event_field(self.event_id, "invalid_field", "value")

    def test_add_event_with_results(self):
        """Проверка добавления события с JSON-результатами."""
        event_id = db.add_event(
            self.animal_id, "test", "2023-01-01",
            results={"key": "value"}
        )
        conn = sqlite3.connect(db.DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT results FROM events WHERE id=?", (event_id,))
        result = cur.fetchone()[0]
        self.assertEqual(json.loads(result), {"key": "value"})
        conn.close()

    def test_get_animal_events(self):
        """Проверка получения событий животного с путями документов."""
        db.add_event_doc(self.event_id, "doc1.txt")
        events = db.get_animal_events(self.animal_id)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event[0], "vaccination")
        expected_path = os.path.normpath(f"docs/{self.animal_id}/doc1.txt")
        self.assertEqual(event[4], [expected_path])

    def test_update_adoption_field(self):
        """Проверка обновления поля усыновления."""
        # Создаем животное
        animal_id = db.add_animal(
            "TestAdoptAnimal", "Cat", None, 3,
            "2023-01-01", None, None
        )
        
        # Добавляем запись об усыновлении
        db.add_adoption(animal_id, "Test Owner", "test_contact", "2023-01-01")
        
        # Обновляем поле
        db.update_adoption_field(animal_id, "owner_name", "New Owner")
        
        # Проверяем обновление
        conn = sqlite3.connect(db.DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "SELECT owner_name FROM animals WHERE id = ?",
            (animal_id,)
        )
        result = cur.fetchone()[0]
        conn.close()
        self.assertEqual(result, "New Owner")

    def test_add_and_get_adoption(self):
        """Проверка добавления и получения усыновления."""
        animal_id = db.add_animal(
            "TestAdoptAnimal2", "Dog", "2020-01-01", 2,
            "2022-01-01", "A2", None
        )
        
        # Добавляем усыновление
        db.add_adoption(animal_id, "Owner", "contact", "2023-01-01")
        
        # Получаем все усыновления
        adoptions = db.get_all_adoptions()
        
        # Проверяем наличие добавленной записи
        self.assertTrue(any(
            a[0] == animal_id and a[7] == "Owner" 
            for a in adoptions
        ))

    def test_adoption_lifecycle(self):
        """Полный цикл: добавление, обновление, удаление."""
        animal_id = db.add_animal(
            "TestLifecycle", "Rabbit", None, 1,
            "2023-01-01", "B3", None
        )
        
        # Добавляем усыновление
        db.add_adoption(animal_id, "Lifecycle Owner", "contact", "2023-01-01")
        
        # Обновляем дату
        db.update_adoption_field(animal_id, "adoption_date", "2023-01-02")
        
        # Удаляем животное (мягкое удаление)
        db.delete_animal(animal_id)
        
        # Проверяем, что усыновление больше не показывается
        adoptions = db.get_all_adoptions()
        self.assertNotIn(animal_id, [a[0] for a in adoptions])

    def test_init_db_columns(self):
        """Проверка создания всех таблиц с правильными колонками."""
        conn = sqlite3.connect(db.DB_NAME)
        cur = conn.cursor()
        
        # Проверка структуры таблицы animals
        cur.execute("PRAGMA table_info(animals)")
        columns = {row[1] for row in cur.fetchall()}
        expected = {'id', 'name', 'species', 'birth_date', 'age_estimated',
                   'arrival_date', 'cage_number', 'quarantine_until'}
        self.assertTrue(expected.issubset(columns))
        
        conn.close()

    def test_get_animal_by_id_exists(self):
        """Проверка получения существующего животного."""
        animal = db.get_animal_by_id(self.animal_id)
        self.assertEqual(animal[1], "TestAnimal")
        self.assertEqual(animal[2], "Dog")
        self.assertEqual(animal[6], "A1")  # cage_number

    def test_get_animal_by_id_not_exists(self):
        """Проверка получения несуществующего животного."""
        animal = db.get_animal_by_id(9999)
        self.assertIsNone(animal)

    def test_get_all_cage_numbers(self):
        """Проверка получения занятых номеров клеток."""
        cages = db.get_all_cage_numbers()
        self.assertIn("A1", cages)
        self.assertNotIn(None, cages)
        
        # Добавляем еще одно животное с клеткой
        db.add_animal("New", "Dog", None, 1, "2023-01-01", "B2", None)
        cages = db.get_all_cage_numbers()
        self.assertIn("B2", cages)

    def test_get_all_animals_ids(self):
        """Проверка получения списка ID и имен животных."""
        ids = db.get_all_animals_ids()
        expected = {(self.animal_id, "TestAnimal"), 
                   (self.animal_id2, "TestAnimal2")}
        self.assertTrue(expected.issubset(set(ids)))

    def test_get_all_animals_ids_empty(self):
        """Проверка пустого списка при отсутствии животных."""
        # Удаляем всех животных
        db.delete_animal(self.animal_id)
        db.delete_animal(self.animal_id2)
        ids = db.get_all_animals_ids()
        self.assertEqual(ids, [])

if __name__ == '__main__':
    unittest.main()