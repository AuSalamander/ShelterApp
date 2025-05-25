"""
Вкладка "Переданы" - таблица усыновленных животных
"""
import database
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from config import config
from models import AnimalManager
from utils import autofit_treeview_columns

class AdoptedTab:
    """Вкладка переданных животных"""
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.setup_bindings()
    
    def setup_ui(self):
        """Создание интерфейса"""
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        
        # Заголовок
        ttk.Label(self.frame, text="Переданные животные", font=("", 14)).grid(
            row=0, column=0, pady=5
        )
        
        # Фрейм для таблицы
        frm_adopt = ttk.Frame(self.frame)
        frm_adopt.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        frm_adopt.rowconfigure(0, weight=1)
        frm_adopt.columnconfigure(0, weight=1)
        
        # Колонки таблицы
        self.columns = (
            "ID животного", "Имя", "Вид", "Дата рождения", 
            "Возраст (мес.)", "Дата поступления",
            "Имя владельца", "Контакт", "Дата передачи"
        )
        
        # Создание таблицы
        self.tree = ttk.Treeview(frm_adopt, columns=self.columns, show='headings')
        
        # Настройка заголовков
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center')
        
        # Скроллбары
        vsb = ttk.Scrollbar(frm_adopt, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        hsb = ttk.Scrollbar(frm_adopt, orient='horizontal', command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)
        
        # Размещение
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, columnspan=2, sticky='ew')
    
    def setup_bindings(self):
        """Настройка обработчиков событий"""
        self.tree.bind("<Double-1>", self.on_double_click)
    
    def refresh_list(self):
        """Обновление списка усыновленных животных"""
        self.tree.delete(*self.tree.get_children())
        
        animals = AnimalManager.get_all_adopted()
        today = date.today()
        
        for animal in animals:
            # Вычисляем возраст
            age_display = animal.get_age_display()
            birth_display = animal.get_birth_date_display()
            
            values = (
                animal.id, animal.name, animal.species,
                birth_display, age_display, animal.arrival_date or "",
                animal.owner_name or "", animal.owner_contact or "",
                animal.adoption_date or ""
            )
            
            self.tree.insert('', 'end', iid=str(animal.id), values=values)
        
        # Автоподгонка ширины колонок
        autofit_treeview_columns(self.tree, self.columns)
    
    def on_double_click(self, event):
        """Обработчик двойного клика для редактирования"""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        
        col_id = self.tree.identify_column(event.x)
        field = config.COLUMN_MAP_ADOPTED.get(col_id)
        
        if not field:
            return  # Эту колонку не редактируем
        
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        # Координаты ячейки
        x, y, width, height = self.tree.bbox(row_id, col_id)
        old_value = self.tree.set(row_id, col_id)

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, old_value)
        entry.focus()

        def save_edit(e):
            new_value = entry.get().strip()
            animal_id = self.tree.item(row_id)["values"][0]
            database.update_adoption_field(animal_id, field, new_value)
            entry.destroy()
            self.refresh_list()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        pass
