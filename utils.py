"""
Утилиты для приложения ShelterApp
"""
import re
import os
import sys
from datetime import date, timedelta
from tkinter import font
from typing import Optional


def validate_cage_number(cage_number: str) -> bool:
    """Проверяет корректность номера клетки"""
    return bool(re.fullmatch(r'^[КО][0-9A-Fa-f]{4}$', cage_number))


def validate_date_format(date_str: str) -> bool:
    """Проверяет корректность формата даты YYYY-MM-DD"""
    try:
        date.fromisoformat(date_str)
        return True
    except ValueError:
        return False


def calculate_age_in_months(birth_date: date, reference_date: Optional[date] = None) -> int:
    """Вычисляет возраст в месяцах"""
    if reference_date is None:
        reference_date = date.today()
    
    return (reference_date.year * 12 + reference_date.month) - \
           (birth_date.year * 12 + birth_date.month)


def subtract_months(from_date: date, months: int) -> date:
    """Возвращает дату, отстоящую на указанное количество месяцев назад"""
    total = from_date.year * 12 + from_date.month - 1 - months
    year = total // 12
    month = total % 12 + 1
    day = min(from_date.day, (date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)).day)
    return date(year, month, day)


def get_default_quarantine_cage(taken_cages: list) -> str:
    """Генерирует номер свободной карантинной клетки"""
    # Таблица замены кириллических букв на латинские
    CYRILLIC_TO_LATIN = str.maketrans({
        'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E',
        'а': 'a', 'в': 'b', 'с': 'c', 'е': 'e',
    })
    
    used = set()
    for cn in taken_cages:
        if cn.startswith("К"):
            hex_part = cn[1:].translate(CYRILLIC_TO_LATIN)
            try:
                num = int(hex_part, 16)
                used.add(num)
            except ValueError:
                print(f"⚠ Некорректный номер клетки: {cn}")
    
    # Ищем первый свободный номер
    for i in range(0x10000):
        if i not in used:
            return f"К{i:04X}"
    
    raise RuntimeError("Нет свободных карантинных клеток")


def autofit_treeview_columns(tree, columns: list, padding: int = 10):
    """Автоматически подгоняет ширину колонок Treeview под содержимое"""
    tv_font = font.nametofont("TkDefaultFont")

    for col in columns:
        # Измеряем ширину заголовка
        max_width = tv_font.measure(col)
        # Измеряем каждую ячейку в этой колонке
        for item in tree.get_children():
            cell_text = str(tree.set(item, col))
            w = tv_font.measure(cell_text)
            if w > max_width:
                max_width = w
        # Устанавливаем ширину + padding
        tree.column(col, width=max_width + padding)


def open_folder_in_explorer(folder_path: str):
    """Открывает папку в проводнике операционной системы"""
    folder_path = os.path.abspath(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    
    if os.name == 'nt':  # Windows
        os.startfile(folder_path)
    elif sys.platform == 'darwin':  # macOS
        os.system(f'open "{folder_path}"')
    else:  # Linux
        os.system(f'xdg-open "{folder_path}"')


def truncate_text_for_width(text: str, font_obj, max_width: int) -> str:
    """Обрезает текст до указанной ширины с добавлением '...'"""
    if font_obj.measure(text) <= max_width:
        return text
    
    # Бинарный поиск максимальной длины
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        if font_obj.measure(text[:mid] + '...') <= max_width:
            lo = mid + 1
        else:
            hi = mid
    
    return text[:lo-1] + '...' if lo > 0 else '...'


def format_species_display(species: str, breed: str) -> str:
    """Форматирует отображение вида и породы"""
    return f"{species} / {breed}" if breed else species


def calculate_quarantine_days_left(quarantine_until: str, reference_date: Optional[date] = None) -> int:
    """Вычисляет количество дней до окончания карантина"""
    if not quarantine_until:
        return 0
    
    if reference_date is None:
        reference_date = date.today()
    
    try:
        qdate = date.fromisoformat(quarantine_until)
        return max((qdate - reference_date).days, 0)
    except ValueError:
        return 0
