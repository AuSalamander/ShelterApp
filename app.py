import sys
import os

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем и запускаем новое приложение
from main import main

if __name__ == "__main__":
    main()
