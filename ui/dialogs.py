"""
Диалоговые окна для ShelterApp
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
import os
from config import config
from models import Animal, AnimalManager
from utils import validate_date_format
import database


class AdoptionDialog:
    """Диалог усыновления животного"""
    
    def __init__(self, parent, animal_id):
        self.parent = parent
        self.animal_id = animal_id
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """Создание диалогового окна"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Передача животного")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Поля ввода
        ttk.Label(self.dialog, text="Имя владельца").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.ent_owner = ttk.Entry(self.dialog, width=30)
        self.ent_owner.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(self.dialog, text="Контакт владельца").grid(row=1, column=0, sticky='w', pady=5, padx=5)
        self.ent_contact = ttk.Entry(self.dialog, width=30)
        self.ent_contact.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(self.dialog, text="Дата передачи (YYYY-MM-DD)").grid(row=2, column=0, sticky='w', pady=5, padx=5)
        self.ent_date = ttk.Entry(self.dialog, width=30)
        self.ent_date.grid(row=2, column=1, pady=5, padx=5)
        self.ent_date.insert(0, date.today().isoformat())
        
        # Кнопки
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Подтвердить", command=self.confirm).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.cancel).pack(side='left', padx=5)
        
        # Фокус на первое поле
        self.ent_owner.focus()
    
    def confirm(self):
        """Подтверждение усыновления"""
        owner = self.ent_owner.get().strip()
        contact = self.ent_contact.get().strip()
        adoption_date = self.ent_date.get().strip()
        
        if not owner or not contact:
            messagebox.showwarning("Ошибка", "Укажите имя и контакт владельца")
            return
        
        if not validate_date_format(adoption_date):
            messagebox.showwarning("Ошибка", "Неверный формат даты")
            return
        
        try:
            database.add_adoption(self.animal_id, owner, contact, adoption_date)
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось оформить усыновление: {str(e)}")
    
    def cancel(self):
        """Отмена"""
        self.result = False
        self.dialog.destroy()


class EventDialog:
    """Диалог создания события"""
    
    def __init__(self, parent, animal_id):
        self.parent = parent
        self.animal_id = animal_id
        self.result = None
        self.extra_fields = {}  # Дополнительные поля для именных событий
        self.create_dialog()
    
    def create_dialog(self):
        """Создание диалогового окна"""
        # Получаем данные животного
        animal_data = database.get_animal_by_id(self.animal_id)
        if not animal_data:
            messagebox.showerror("Ошибка", "Животное не найдено")
            return
        
        name = animal_data[1]
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Новое событие для #{self.animal_id} ({name})")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Создаем скроллируемую область
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.create_form()
    
    def create_form(self):
        """Создание формы события"""
        self.scrollable_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Тип события
        ttk.Label(self.scrollable_frame, text="Тип события:").grid(
            row=row, column=0, sticky='w', padx=5, pady=5
        )
        
        event_types = config.get_event_types() + ["Другое"]
        self.cmb_type = ttk.Combobox(
            self.scrollable_frame, 
            values=event_types, 
            state="readonly", 
            width=40
        )
        self.cmb_type.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        if event_types:
            self.cmb_type.set(event_types[0])
        
        row += 1
        
        # Поле для ввода пользовательского типа
        self.lbl_other = ttk.Label(self.scrollable_frame, text="Укажите тип:")
        self.ent_other = ttk.Entry(self.scrollable_frame, width=40)
        
        row += 1
        
        # Даты
        ttk.Label(self.scrollable_frame, text="Дата начала (YYYY-MM-DD):").grid(
            row=row, column=0, sticky='w', padx=5, pady=5
        )
        self.ent_date_start = ttk.Entry(self.scrollable_frame, width=40)
        self.ent_date_start.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.ent_date_start.insert(0, date.today().isoformat())
        
        row += 1
        
        ttk.Label(self.scrollable_frame, text="Дата окончания:").grid(
            row=row, column=0, sticky='w', padx=5, pady=5
        )
        self.ent_date_end = ttk.Entry(self.scrollable_frame, width=40)
        self.ent_date_end.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        
        row += 1
        
        # Заключение
        ttk.Label(self.scrollable_frame, text="Заключение:").grid(
            row=row, column=0, sticky='nw', padx=5, pady=5
        )
        self.txt_conclusion = tk.Text(self.scrollable_frame, height=4, width=40)
        self.txt_conclusion.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        
        row += 1
        
        # Документы
        docs_frame = ttk.LabelFrame(self.scrollable_frame, text="Документы")
        docs_frame.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        docs_frame.columnconfigure(0, weight=1)
        
        self.doc_paths = []
        self.lb_docs = tk.Listbox(docs_frame, height=3)
        sb_docs = ttk.Scrollbar(docs_frame, orient='vertical', command=self.lb_docs.yview)
        self.lb_docs.configure(yscrollcommand=sb_docs.set)
        
        self.lb_docs.grid(row=0, column=0, sticky='nsew', pady=2)
        sb_docs.grid(row=0, column=1, sticky='ns', pady=2)
        
        btn_frame = ttk.Frame(docs_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(btn_frame, text="Добавить файлы", command=self.add_documents).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Удалить выбранное", command=self.remove_document).pack(side='left', padx=5)
        
        row += 1

        # Фрейм для дополнительных полей именных событий
        self.extra_fields_frame = ttk.LabelFrame(self.scrollable_frame, text="Дополнительные поля")
        self.extra_fields_frame.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        self.extra_fields_frame.columnconfigure(1, weight=1)

        row += 1
        
        # Кнопки
        btn_frame = ttk.Frame(self.scrollable_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Создать", command=self.create_event).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.cancel).pack(side='left', padx=5)
        
        # Настройка обработчиков
        self.cmb_type.bind("<<ComboboxSelected>>", self.on_type_change)
        self.on_type_change()  # Инициализация
    
    def on_type_change(self, event=None):
        """Обработчик изменения типа события"""
        selected_type = self.cmb_type.get()
        
        # Показываем/скрываем поле "Другое"
        if selected_type == "Другое":
            self.lbl_other.grid(row=1, column=0, sticky='w', padx=5, pady=5)
            self.ent_other.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        else:
            self.lbl_other.grid_forget()
            self.ent_other.grid_forget()
        
        # Очищаем дополнительные поля
        for widget in self.extra_fields_frame.winfo_children():
            widget.destroy()
        self.extra_fields.clear()
        
        # Добавляем дополнительные поля для именных событий
        if selected_type != "Другое" and selected_type in config.get_event_types():
            fields = config.get_event_fields(selected_type)
            
            if fields:
                for idx, (field_name, field_type) in enumerate(fields):
                    ttk.Label(self.extra_fields_frame, text=f"{field_name}:").grid(
                        row=idx, column=0, sticky='w', padx=5, pady=2
                    )
                    
                    if field_type.lower() in ['text', 'string', 'str']:
                        widget = ttk.Entry(self.extra_fields_frame, width=40)
                    elif field_type.lower() in ['textarea', 'multiline']:
                        widget = tk.Text(self.extra_fields_frame, height=3, width=40)
                    elif field_type.lower() in ['number', 'int', 'float']:
                        widget = ttk.Entry(self.extra_fields_frame, width=40)
                    elif field_type.lower() in ['date']:
                        widget = ttk.Entry(self.extra_fields_frame, width=40)
                        widget.insert(0, date.today().isoformat())
                    elif field_type.lower() in ['bool', 'boolean', 'checkbox']:
                        widget = ttk.Checkbutton(self.extra_fields_frame)
                    else:
                        widget = ttk.Entry(self.extra_fields_frame, width=40)
                    
                    widget.grid(row=idx, column=1, sticky='w', padx=5, pady=2)
                    self.extra_fields[field_name] = (widget, field_type)
            else:
                # Скрываем фрейм если нет дополнительных полей
                self.extra_fields_frame.grid_forget()
        else:
            # Скрываем фрейм для "Другое" или неизвестных типов
            self.extra_fields_frame.grid_forget()
    
    def add_documents(self):
        """Добавление документов"""
        folder = os.path.abspath(f"docs/{self.animal_id}")
        os.makedirs(folder, exist_ok=True)
        
        files = filedialog.askopenfilenames(
            title="Выберите файлы",
            initialdir=folder
        )
        
        for file_path in files:
            filename = os.path.basename(file_path)
            if filename not in self.doc_paths:
                self.doc_paths.append(filename)
                self.lb_docs.insert('end', filename)
    
    def remove_document(self):
        """Удаление выбранного документа"""
        selection = self.lb_docs.curselection()
        for idx in reversed(selection):
            filename = self.lb_docs.get(idx)
            self.doc_paths.remove(filename)
            self.lb_docs.delete(idx)
    
    def create_event(self):
        """Создание события"""
        event_type = self.cmb_type.get()
        if event_type == "Другое":
            event_type = self.ent_other.get().strip()
        
        date_start = self.ent_date_start.get().strip()
        date_end = self.ent_date_end.get().strip() or None
        conclusion = self.txt_conclusion.get("1.0", "end").strip() or None
        
        if not event_type or not date_start:
            messagebox.showwarning("Ошибка", "Тип и дата начала обязательны")
            return
        
        if not validate_date_format(date_start):
            messagebox.showwarning("Ошибка", "Неверный формат даты начала")
            return
        
        if date_end and not validate_date_format(date_end):
            messagebox.showwarning("Ошибка", "Неверный формат даты окончания")
            return
        
        # Собираем дополнительные поля
        results_data = {}
        for field_name, (widget, field_type) in self.extra_fields.items():
            try:
                if isinstance(widget, tk.Text):
                    value = widget.get("1.0", "end").strip()
                elif isinstance(widget, ttk.Checkbutton):
                    value = widget.instate(['selected'])
                else:
                    value = widget.get().strip()
                
                if value:  # Сохраняем только непустые значения
                    results_data[field_name] = value
            except Exception:
                pass  # Игнорируем ошибки получения значений
        
        # Преобразуем дополнительные поля в JSON строку
        results_json = None
        if results_data:
            import json
            try:
                results_json = json.dumps(results_data, ensure_ascii=False)
            except Exception:
                pass  # Если не удалось сериализовать, сохраняем без дополнительных полей
        
        try:
            # Создаем событие
            event_id = database.add_event(
                self.animal_id, event_type, date_start, date_end, conclusion, results_json
            )
            
            # Добавляем документы
            for filename in self.doc_paths:
                database.add_event_doc(event_id, filename)
            
            self.result = True
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать событие: {str(e)}")
    
    def cancel(self):
        """Отмена"""
        self.result = False
        self.dialog.destroy()
