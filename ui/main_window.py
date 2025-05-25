"""
Главное окно приложения ShelterApp
"""
import tkinter as tk
from tkinter import ttk
from config import config
from ui.shelter_tab import ShelterTab
from ui.medical_tab import MedicalTab
from ui.adopted_tab import AdoptedTab


class ShelterApp:
    """Главное приложение ShelterApp"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_tabs()
        self.setup_bindings()
    
    def setup_window(self):
        """Настройка главного окна"""
        self.root.title(config.APP_TITLE)
        self.root.geometry(config.DEFAULT_GEOMETRY)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Установка иконки
        try:
            img = tk.PhotoImage(file='img/icon.png')
            self.root.iconphoto(True, img)
        except tk.TclError:
            # Если файл иконки не найден, продолжаем без неё
            pass
    
    def create_tabs(self):
        """Создание вкладок"""
        self.notebook = ttk.Notebook(self.root)
        
        # Создаем вкладки и сохраняем ссылки на них
        self.shelter_tab = ShelterTab(self.notebook)
        self.adopted_tab = AdoptedTab(self.notebook)
        self.medical_tab = MedicalTab(self.notebook)
        
        # Устанавливаем ссылку на главное приложение в каждой вкладке
        self.shelter_tab.app = self
        self.adopted_tab.app = self
        self.medical_tab.app = self
        
        # Добавляем вкладки в notebook
        self.notebook.add(self.shelter_tab.frame, text="Приют")
        self.notebook.add(self.adopted_tab.frame, text="Переданы")
        self.notebook.add(self.medical_tab.frame, text="Медицина", 
                         image=self.medical_tab.blank_img, compound='right')
        
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
    
    def setup_bindings(self):
        """Настройка горячих клавиш"""
        self.fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", lambda e: self.toggle_fullscreen() if self.fullscreen else None)
    
    def toggle_fullscreen(self, event=None):
        """Переключение полноэкранного режима"""
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
    
    def refresh_all_tabs(self):
        """Обновляет все вкладки"""
        self.shelter_tab.refresh_list()
        self.adopted_tab.refresh_list()
        self.medical_tab.refresh_list()
    
    def run(self):
        """Запуск приложения"""
        # Инициализация данных
        self.refresh_all_tabs()
        
        # Запуск главного цикла
        self.root.mainloop()
