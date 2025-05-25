"""
Модуль конфигурации приложения ShelterApp
Загружает настройки из cfg.txt и spesies_config.txt
"""
import configparser
import os
from typing import Dict, List, Tuple


class Config:
    """Класс для управления конфигурацией приложения"""
    
    # Константы приложения
    APP_TITLE = "ShelterApp"
    DEFAULT_GEOMETRY = "1000x750"
    DEFAULT_QUARANTINE_DAYS = 10
    
    # Константы UI
    COLUMN_WIDTHS = {
        "ID": 30,
        "Имя": 100,
        "Вид": 150,
        "Дата рождения": 100,
        "Возраст (мес.)": 90,
        "Дата поступления": 100,
        "Клетка": 70,
        "Осталось дней карантина": 150,
        "Med": 20,
        "Adopt": 20,
        "Del": 20
    }
    
    # Маппинг колонок для редактирования
    COLUMN_MAP = {
        "#2": "name",
        "#3": "species",
        "#4": "birth_date",
        "#6": "arrival_date",
        "#7": "cage_number",
        "#8": "quarantine_until",
    }
    
    COLUMN_MAP_ADOPTED = {
        "#1": None,
        "#2": "name",
        "#3": "species",
        "#4": "birth_date",
        "#5": None,
        "#6": "arrival_date",
        "#7": "owner_name",
        "#8": "owner_contact",
        "#9": "adoption_date",
    }
    
    def __init__(self):
        self.species_map: Dict[str, List[str]] = {}
        self.event_result_map: Dict[str, List[Tuple[str, str]]] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Загружает все конфигурационные файлы"""
        self._load_species_config()
        self._load_event_config()
    
    def _load_species_config(self):
        """Загружает конфигурацию видов и пород из spesies_config.txt"""
        if not os.path.exists('spesies_config.txt'):
            return
            
        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.optionxform = str  # сохраняем регистр
        cfg.read('spesies_config.txt', encoding='utf-8')
        
        for section in cfg.sections():
            breeds = [k for k in cfg[section].keys()]
            self.species_map[section] = breeds
    
    def _load_event_config(self):
        """Загружает конфигурацию событий из event_config.txt"""
        if not os.path.exists('event_config.txt'):
            return
            
        current_etype = None
        current_specs = []
        
        with open("event_config.txt", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.split('#', 1)[0].strip()
                
                if not line:
                    continue
                    
                # Обработка новой секции
                if '=' in line:
                    if current_etype is not None:
                        self.event_result_map[current_etype] = current_specs
                    etype, remainder = line.split('=', 1)
                    current_etype = etype.strip()
                    current_specs = []
                    line = remainder.strip()
                    
                # Обработка полей
                if current_etype is not None and ':' in line:
                    fields = [f.strip() for f in line.split(',') if f.strip()]
                    for field in fields:
                        if ':' not in field:
                            continue
                        name, typ = field.split(':', 1)
                        current_specs.append((name.strip(), typ.strip()))
                        
            # Добавить последнюю секцию
            if current_etype is not None:
                self.event_result_map[current_etype] = current_specs
    
    def get_species_list(self) -> List[str]:
        """Возвращает список всех видов"""
        return list(self.species_map.keys())
    
    def get_breeds_for_species(self, species: str) -> List[str]:
        """Возвращает список пород для указанного вида"""
        return self.species_map.get(species, [])
    
    def get_event_types(self) -> List[str]:
        """Возвращает список типов событий"""
        return list(self.event_result_map.keys())
    
    def get_event_fields(self, event_type: str) -> List[Tuple[str, str]]:
        """Возвращает поля для указанного типа события"""
        return self.event_result_map.get(event_type, [])


# Глобальный экземпляр конфигурации
config = Config()
