"""
Главный файл приложения ShelterApp
Точка входа в приложение после рефакторинга
"""
import database
from ui.main_window import ShelterApp


def main():
    """Главная функция приложения"""
    # Инициализация базы данных
    database.init_db()
    
    # Создание и запуск приложения
    app = ShelterApp()
    app.run()


if __name__ == "__main__":
    main()
