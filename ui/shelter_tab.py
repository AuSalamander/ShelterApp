"""
Вкладка "Приют" - основная таблица животных
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import re
from config import config
from models import AnimalManager, Animal
from utils import (
    get_default_quarantine_cage, 
    format_species_display, 
    calculate_quarantine_days_left,
    autofit_treeview_columns
)
from ui.dialogs import AdoptionDialog
import database


class ShelterTab:
    """Вкладка приюта с таблицей животных"""
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.blink_timers = {}
        self.setup_ui()
        self.setup_bindings()
    
    def setup_ui(self):
        """Создание интерфейса вкладки"""
        # Настройка сетки
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)
        
        self.create_input_forms()
        self.create_buttons()
        self.create_animal_table()
    
    def create_input_forms(self):
        """Создание форм ввода"""
        # Фрейм основной информации
        self.frm_inputs = ttk.LabelFrame(self.frame, text="Основная информация")
        self.frm_inputs.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.frm_inputs.columnconfigure(0, weight=0)
        self.frm_inputs.columnconfigure(1, weight=1)
        
        # Поля ввода
        ttk.Label(self.frm_inputs, text="Имя").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_name = ttk.Entry(self.frm_inputs)
        self.entry_name.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_inputs, text="Вид").grid(row=1, column=0, sticky="w", pady=2)
        self.combobox_species = ttk.Combobox(
            self.frm_inputs,
            values=config.get_species_list(),
            state="readonly"
        )
        self.combobox_species.grid(row=1, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_inputs, text="Порода").grid(row=2, column=0, sticky="w", pady=2)
        self.combobox_breed = ttk.Combobox(self.frm_inputs, values=[], state="readonly")
        self.combobox_breed.grid(row=2, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_inputs, text="Дата рождения\n(YYYY-MM-DD)").grid(row=3, column=0, sticky="w", pady=2)
        self.entry_birth = ttk.Entry(self.frm_inputs)
        self.entry_birth.grid(row=3, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_inputs, text="ИЛИ оценка возраста\n(месяцы)").grid(row=4, column=0, sticky="w", pady=2)
        self.entry_est = ttk.Entry(self.frm_inputs)
        self.entry_est.grid(row=4, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_inputs, text="Дата поступления\n(YYYY-MM-DD)").grid(row=5, column=0, sticky="w", pady=2)
        self.entry_arrival = ttk.Entry(self.frm_inputs)
        self.entry_arrival.grid(row=5, column=1, sticky="ew", pady=2)
        
        # Фрейм карантина
        self.frm_quarantine = ttk.LabelFrame(self.frame, text="Карантин")
        self.frm_quarantine.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.frm_quarantine.columnconfigure(0, weight=0)
        self.frm_quarantine.columnconfigure(1, weight=1)
        
        ttk.Label(self.frm_quarantine, text="Клетка").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_cage = ttk.Entry(self.frm_quarantine)
        self.entry_cage.grid(row=0, column=1, sticky="ew", pady=2)
        
        ttk.Label(self.frm_quarantine, text="Окончание\nкарантина").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_quarantine = ttk.Entry(self.frm_quarantine)
        self.entry_quarantine.grid(row=1, column=1, sticky="ew", pady=2)
        
        # Устанавливаем значения по умолчанию
        self.set_default_values()
    
    def create_buttons(self):
        """Создание кнопок"""
        frm_buttons = ttk.Frame(self.frame)
        frm_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        frm_buttons.columnconfigure(0, weight=1)
        frm_buttons.columnconfigure(1, weight=1)
        
        btn_add = ttk.Button(frm_buttons, text="Добавить", command=self.add_animal)
        btn_add.grid(row=0, column=0, sticky="ew", padx=5)
        
        btn_refresh = ttk.Button(frm_buttons, text="Обновить список", command=self.refresh_all_tabs)
        btn_refresh.grid(row=0, column=1, sticky="ew", padx=5)
    
    def create_animal_table(self):
        """Создание таблицы животных"""
        self.columns = (
            "ID", "Имя", "Вид", "Дата рождения", "Возраст (мес.)",
            "Дата поступления", "Клетка", "Осталось дней карантина",
            "Med", "Adopt", "Del"
        )
        
        table_frame = ttk.Frame(self.frame)
        table_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show='headings')
        
        # Настройка заголовков и ширин
        for col in self.columns:
            self.tree.heading(col, text=col if col not in ("Med", "Adopt", "Del") else "")
            if col in config.COLUMN_WIDTHS:
                self.tree.column(col, width=config.COLUMN_WIDTHS[col], anchor='center')
        
        # Скроллбар
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        
        # Настройка тегов для раскраски
        self.tree.tag_configure('quarantine', background='#FFF59D')
        self.tree.tag_configure('expired', background='#C8E6C9')
    
    def setup_bindings(self):
        """Настройка обработчиков событий"""
        self.combobox_species.bind("<<ComboboxSelected>>", self.on_species_selected)
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-1>", self.on_double_click)
    
    def set_default_values(self):
        """Установка значений по умолчанию"""
        try:
            cage_numbers = database.get_all_cage_numbers()
            default_cage = get_default_quarantine_cage(cage_numbers)
            self.entry_cage.insert(0, default_cage)
        except RuntimeError:
            pass  # Если нет свободных клеток
        
        default_quarantine = (date.today() + timedelta(days=config.DEFAULT_QUARANTINE_DAYS)).isoformat()
        self.entry_quarantine.insert(0, default_quarantine)
    
    def on_species_selected(self, event):
        """Обработчик выбора вида"""
        species = self.combobox_species.get()
        breeds = config.get_breeds_for_species(species)
        self.combobox_breed['values'] = breeds
        self.combobox_breed.set('')
    
    def add_animal(self):
        """Добавление нового животного"""
        try:
            # Получение данных из формы
            name = self.entry_name.get().strip()
            species = self.combobox_species.get().strip()
            breed = self.combobox_breed.get().strip()
            birth_date = self.entry_birth.get().strip()
            age_est = self.entry_est.get().strip()
            arrival_date = self.entry_arrival.get().strip() or date.today().isoformat()
            cage = self.entry_cage.get().strip()
            quarantine_until = self.entry_quarantine.get().strip()
            
            # Валидация
            if not name:
                messagebox.showwarning("Ошибка", "Имя обязательно")
                return
            
            if not species:
                messagebox.showwarning("Ошибка", "Выберите вид")
                return
            
            # Проверяем, что клетка не занята
            if cage in database.get_all_cage_numbers():
                messagebox.showwarning("Ошибка", f"Клетка {cage} уже занята")
                return
            
            # Формирование полного названия вида
            full_species = format_species_display(species, breed)
            
            # Обработка даты рождения/возраста
            if birth_date:
                try:
                    bdate = date.fromisoformat(birth_date)
                    est_flag = 0
                except ValueError:
                    messagebox.showwarning("Ошибка", "Неверный формат даты рождения")
                    return
            elif age_est:
                try:
                    months = int(age_est)
                    today = date.today()
                    year = today.year - (months // 12)
                    month = today.month - (months % 12)
                    if month <= 0:
                        year -= 1
                        month += 12
                    bdate = date(year, month, today.day)
                    est_flag = 1
                except ValueError:
                    messagebox.showwarning("Ошибка", "Оценка должна быть числом")
                    return
            else:
                messagebox.showwarning("Ошибка", "Укажите дату рождения или оценку возраста")
                return
            
            # Проверяем формат quarantine_until
            try:
                date.fromisoformat(quarantine_until)
            except ValueError:
                messagebox.showwarning("Ошибка", "Неправильный формат даты окончания карантина")
                return
            
            # Сохраняем в базу и получаем новый ID
            new_id = database.add_animal(
                name, full_species, bdate.isoformat(), est_flag,
                arrival_date, cage, quarantine_until
            )
            
            # Создание папки для документов
            import os
            os.makedirs(f"docs/{new_id}", exist_ok=True)
            
            messagebox.showinfo("Готово", f"Животное добавлено с ID {new_id}")
            
            # Очистка формы и обновление всех списков
            self.clear_form()
            self.refresh_all_tabs()
            
            # Уведомление медицинской вкладки о новом животном
            app = self.get_app()
            if app:
                app.medical_tab.notify_new_animal(new_id)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось добавить животное: {str(e)}")
    
    def clear_form(self):
        """Очистка формы"""
        self.entry_name.delete(0, 'end')
        self.combobox_species.set('')
        self.combobox_breed.set('')
        self.entry_birth.delete(0, 'end')
        self.entry_est.delete(0, 'end')
        self.entry_arrival.delete(0, 'end')
        self.entry_cage.delete(0, 'end')
        self.entry_quarantine.delete(0, 'end')
        self.set_default_values()
    
    def get_app(self):
        """Получает ссылку на главное приложение"""
        return getattr(self, 'app', None)
    
    def refresh_all_tabs(self):
        """Обновляет все вкладки"""
        app = self.get_app()
        if app:
            app.refresh_all_tabs()
    
    def refresh_list(self):
        """Обновление списка животных"""
        # Останавливаем все мигания
        for item, timer in list(self.blink_timers.items()):
            self.frame.after_cancel(timer)
        self.blink_timers.clear()
        
        # Очищаем таблицу
        self.tree.delete(*self.tree.get_children())
        
        # Загружаем животных
        today = date.today()
        for (id_, name, full_species, bd, est_flag,
             arr, cage, quarantine_until) in database.get_all_animals():

            # возраст
            bdate = date.fromisoformat(bd)
            months = (today.year * 12 + today.month) - (bdate.year * 12 + bdate.month)
            age_disp = f"~{months}" if est_flag else str(months)
            bd_disp = f"~{bd}" if est_flag else bd

            # вычисляем дни до конца карантина и выбираем теги
            days_left = ""
            tags = ()
            if cage.startswith("К") and quarantine_until:
                try:
                    qdate = date.fromisoformat(quarantine_until)
                    days_left = max((qdate - today).days, 0)
                except:
                    days_left = ""
                if days_left > 0:
                    tags = ('quarantine',)
                else:
                    tags = ('expired',)
            
            values = (
                id_, name, full_species,
                bd_disp, age_disp,
                arr or "",
                cage, days_left,"📋", "🤝", "🗑"
            )
            item = self.tree.insert('', 'end', values=values, tags=tags)

            # если карантин закончился — запускаем мигание
            if 'expired' in tags:
                self.blink_row(item)
    
    def blink_row(self, item):
        """Мигание строки"""
        current = list(self.tree.item(item, 'tags'))
        if 'expired' in current:
            new_tags = [t for t in current if t != 'expired']
        else:
            new_tags = current + ['expired']
        
        self.tree.item(item, tags=new_tags)
        self.blink_timers[item] = self.frame.after(500, lambda: self.blink_row(item))
    
    def on_tree_click(self, event):
        """Обработчик кликов по таблице"""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        
        col_id = self.tree.identify_column(event.x)
        col_index = int(col_id.replace("#", "")) - 1
        col_name = self.columns[col_index]
        row_id = self.tree.identify_row(event.y)
        
        if not row_id:
            return
        
        animal_id = int(self.tree.item(row_id)["values"][0])
        
        if col_name == "Med":
            # Открыть медицинскую карточку
            app = self.get_app()
            if app:
                app.medical_tab.open_medical_card(animal_id)
        elif col_name == "Adopt":
            # Открыть диалог усыновления
            self.open_adoption_dialog(animal_id)
        elif col_name == "Del":
            # Удалить животное
            if messagebox.askyesno("Подтверждение", f"Удалить животное с ID {animal_id}?"):
                database.delete_animal(animal_id)
                self.refresh_all_tabs()
    
    def on_double_click(self, event):
        """Обработчик двойного клика для редактирования"""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return

        col_id = self.tree.identify_column(event.x)  # например, "#4"
        # Разрешаем редактировать лишь те колонки, что в COLUMN_MAP
        if col_id not in config.COLUMN_MAP:
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        # Получаем имя поля в БД
        field = config.COLUMN_MAP[col_id]
        # Координаты ячейки
        x, y, width, height = self.tree.bbox(row_id, col_id)
        old_value = self.tree.set(row_id, col_id)

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, old_value)
        entry.focus()

        def save_edit(e):
            new_value = entry.get().strip()

            # Специальная валидация для клетки
            if field == "cage_number":
                if not re.fullmatch(r'^[КО][0-9A-Fa-f]{4}$', new_value):
                    messagebox.showwarning("Ошибка", "Номер клетки должен быть вида 'К0000' или 'О0000'")
                    entry.focus()
                    return
                occupied = database.get_all_cage_numbers()
                if new_value in occupied and new_value != old_value:
                    messagebox.showwarning("Ошибка", f"Клетка {new_value} уже занята")
                    entry.focus()
                    return

            # Валидация даты окончания карантина
            if field == "quarantine_until":
                try:
                    date.fromisoformat(new_value)
                except ValueError:
                    messagebox.showwarning("Ошибка", "Дата окончания карантина должна быть YYYY-MM-DD")
                    entry.focus()
                    return

            # Общий случай — правка любого другого поля
            animal_id = self.tree.item(row_id)["values"][0]
            database.update_animal_field(animal_id, field, new_value)
            entry.destroy()
            self.refresh_all_tabs()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
    
    def open_adoption_dialog(self, animal_id):
        """Открытие диалога усыновления"""
        dialog = AdoptionDialog(self.frame, animal_id)
        if dialog.result:
            self.refresh_all_tabs()
