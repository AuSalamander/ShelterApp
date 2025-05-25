"""
Модели данных для приложения ShelterApp
"""
from datetime import date
from typing import Optional, Dict, Any
import database
from utils import validate_cage_number, validate_date_format, calculate_age_in_months


class Animal:
    """Модель животного"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.name = data.get('name', '')
        self.species = data.get('species', '')
        self.birth_date = data.get('birth_date', '')
        self.age_estimated = data.get('age_estimated', 0)
        self.arrival_date = data.get('arrival_date', '')
        self.cage_number = data.get('cage_number', '')
        self.quarantine_until = data.get('quarantine_until', '')
        self.deleted = data.get('deleted', 0)
        self.adopted = data.get('adopted', 0)
        self.adoption_date = data.get('adoption_date')
        self.owner_name = data.get('owner_name')
        self.owner_contact = data.get('owner_contact')
    
    @classmethod
    def from_db_row(cls, row):
        """Создает объект Animal из строки БД"""
        if not row:
            return None
        
        return cls({
            'id': row[0],
            'name': row[1],
            'species': row[2],
            'birth_date': row[3],
            'age_estimated': row[4],
            'arrival_date': row[5],
            'cage_number': row[6],
            'quarantine_until': row[7],
            'deleted': row[8] if len(row) > 8 else 0,
            'adopted': row[9] if len(row) > 9 else 0,
            'adoption_date': row[10] if len(row) > 10 else None,
            'owner_name': row[11] if len(row) > 11 else None,
            'owner_contact': row[12] if len(row) > 12 else None,
        })
    
    def validate(self) -> tuple[bool, str]:
        """Валидирует данные животного"""
        if not self.name.strip():
            return False, "Имя обязательно"
        
        if self.cage_number and not validate_cage_number(self.cage_number):
            return False, "Номер клетки должен быть вида 'К0000' или 'О0000'"
        
        if self.birth_date and not validate_date_format(self.birth_date):
            return False, "Неверный формат даты рождения"
        
        if self.arrival_date and not validate_date_format(self.arrival_date):
            return False, "Неверный формат даты поступления"
        
        if self.quarantine_until and not validate_date_format(self.quarantine_until):
            return False, "Неверный формат даты окончания карантина"
        
        return True, ""
    
    def save(self) -> int:
        """Сохраняет животное в БД"""
        is_valid, error_msg = self.validate()
        if not is_valid:
            raise ValueError(error_msg)
        
        if self.id:
            # Обновление существующего
            for field in ['name', 'species', 'birth_date', 'arrival_date', 
                         'cage_number', 'quarantine_until']:
                database.update_animal_field(self.id, field, getattr(self, field))
            return self.id
        else:
            # Создание нового
            new_id = database.add_animal(
                self.name, self.species, self.birth_date, self.age_estimated,
                self.arrival_date, self.cage_number, self.quarantine_until
            )
            self.id = new_id
            return new_id
    
    def delete(self):
        """Мягкое удаление животного"""
        if self.id:
            database.delete_animal(self.id)
            self.deleted = 1
    
    def adopt(self, owner_name: str, owner_contact: str, adoption_date: str):
        """Помечает животное как усыновленное"""
        if not validate_date_format(adoption_date):
            raise ValueError("Неверный формат даты усыновления")
        
        database.add_adoption(self.id, owner_name, owner_contact, adoption_date)
        self.adopted = 1
        self.adoption_date = adoption_date
        self.owner_name = owner_name
        self.owner_contact = owner_contact
    
    def get_age_display(self) -> str:
        """Возвращает отображение возраста"""
        if not self.birth_date:
            return ""
        
        try:
            birth_date_obj = date.fromisoformat(self.birth_date)
            months = calculate_age_in_months(birth_date_obj)
            return f"~{months}" if self.age_estimated else str(months)
        except ValueError:
            return ""
    
    def get_birth_date_display(self) -> str:
        """Возвращает отображение даты рождения"""
        if not self.birth_date:
            return ""
        return f"~{self.birth_date}" if self.age_estimated else self.birth_date
    
    def is_in_quarantine(self) -> bool:
        """Проверяет, находится ли животное в карантине"""
        return (self.cage_number and self.cage_number.startswith("К") and 
                self.quarantine_until and not self.adopted and not self.deleted)


class Event:
    """Модель события"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.animal_id = data.get('animal_id')
        self.type = data.get('type', '')
        self.date_start = data.get('date_start', '')
        self.date_end = data.get('date_end')
        self.conclusion = data.get('conclusion')
        self.results = data.get('results')
        self.deleted = data.get('deleted', 0)
    
    @classmethod
    def from_db_row(cls, row):
        """Создает объект Event из строки БД"""
        if not row:
            return None
        
        return cls({
            'id': row[0] if len(row) > 0 else None,
            'animal_id': row[1] if len(row) > 1 else None,
            'type': row[2] if len(row) > 2 else '',
            'date_start': row[3] if len(row) > 3 else '',
            'date_end': row[4] if len(row) > 4 else None,
            'conclusion': row[5] if len(row) > 5 else None,
            'results': row[6] if len(row) > 6 else None,
            'deleted': row[7] if len(row) > 7 else 0,
        })
    
    def validate(self) -> tuple[bool, str]:
        """Валидирует данные события"""
        if not self.type.strip():
            return False, "Тип события обязателен"
        
        if not self.date_start.strip():
            return False, "Дата начала обязательна"
        
        if not validate_date_format(self.date_start):
            return False, "Неверный формат даты начала"
        
        if self.date_end and not validate_date_format(self.date_end):
            return False, "Неверный формат даты окончания"
        
        return True, ""
    
    def save(self) -> int:
        """Сохраняет событие в БД"""
        is_valid, error_msg = self.validate()
        if not is_valid:
            raise ValueError(error_msg)
        
        if self.id:
            # Обновление существующего
            for field in ['type', 'date_start', 'date_end', 'conclusion', 'results']:
                database.update_event_field(self.id, field, getattr(self, field))
            return self.id
        else:
            # Создание нового
            new_id = database.add_event(
                self.animal_id, self.type, self.date_start, 
                self.date_end, self.conclusion, self.results
            )
            self.id = new_id
            return new_id
    
    def delete(self):
        """Мягкое удаление события"""
        if self.id:
            database.delete_event(self.id)
            self.deleted = 1
    
    def get_date_display(self) -> str:
        """Возвращает отображение дат события"""
        if not self.date_end or self.date_start == self.date_end:
            return self.date_start
        return f"{self.date_start} — {self.date_end}"


class AnimalManager:
    """Менеджер для работы с животными"""
    
    @staticmethod
    def get_all_active() -> list[Animal]:
        """Возвращает всех активных (не удаленных и не усыновленных) животных"""
        rows = database.get_all_animals()
        return [Animal.from_db_row(row) for row in rows]
    
    @staticmethod
    def get_all_adopted() -> list[Animal]:
        """Возвращает всех усыновленных животных"""
        rows = database.get_all_adoptions()
        animals = []
        for row in rows:
            # Формат из get_all_adoptions: (id, name, species, birth_date, age_estimated,
            #                               arrival_date, adoption_date, owner_name, owner_contact)
            animal_data = {
                'id': row[0],
                'name': row[1],
                'species': row[2],
                'birth_date': row[3],
                'age_estimated': row[4],
                'arrival_date': row[5],
                'adoption_date': row[6],
                'owner_name': row[7],
                'owner_contact': row[8],
                'adopted': 1
            }
            animals.append(Animal(animal_data))
        return animals
    
    @staticmethod
    def get_by_id(animal_id: int) -> Optional[Animal]:
        """Возвращает животное по ID"""
        row = database.get_animal_by_id(animal_id)
        return Animal.from_db_row(row)
    
    @staticmethod
    def get_all_cage_numbers() -> list[str]:
        """Возвращает список всех занятых номеров клеток"""
        return database.get_all_cage_numbers()
    
    @staticmethod
    def get_animals_for_medical() -> list[tuple[int, str]]:
        """Возвращает список (ID, имя) для медицинского раздела"""
        return database.get_all_animals_ids()


class EventManager:
    """Менеджер для работы с событиями"""
    
    @staticmethod
    def get_animal_events(animal_id: int) -> list:
        """Возвращает события животного"""
        return database.get_animal_events(animal_id)
    
    @staticmethod
    def add_event_document(event_id: int, filename: str):
        """Добавляет документ к событию"""
        database.add_event_doc(event_id, filename)
    
    @staticmethod
    def remove_event_document(event_id: int, filename: str):
        """Удаляет документ из события"""
        database.delete_event_doc(event_id, filename)
    
    @staticmethod
    def get_event_documents(event_id: int) -> list[str]:
        """Возвращает список документов события"""
        return database.get_event_docs(event_id)
