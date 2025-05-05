import tkinter as tk
from tkinter import ttk, messagebox
import database  # наш файл database.py
from datetime import date

def add():
    name = entry_name.get()
    species = entry_species.get()
    age = entry_age.get()
    arrival = entry_arrival.get() or date.today().isoformat()
    if not name:
        messagebox.showwarning("Ошибка", "Имя обязательно")
        return
    database.add_animal(name, species, int(age or 0), arrival)
    messagebox.showinfo("Готово", "Животное добавлено")
    refresh_list()

def refresh_list():
    for row in tree.get_children():
        tree.delete(row)
    for animal in database.get_all_animals():
        tree.insert('', 'end', values=animal)

# — главный код окна —
database.init_db()

root = tk.Tk()
root.title("Приют: учёт животных")

# Поля ввода
tk.Label(root, text="Имя").grid(row=0, column=0)
entry_name = tk.Entry(root); entry_name.grid(row=0, column=1)
tk.Label(root, text="Вид").grid(row=1, column=0)
entry_species = tk.Entry(root); entry_species.grid(row=1, column=1)
tk.Label(root, text="Возраст").grid(row=2, column=0)
entry_age = tk.Entry(root); entry_age.grid(row=2, column=1)
tk.Label(root, text="Дата (YYYY-MM-DD)").grid(row=3, column=0)
entry_arrival = tk.Entry(root); entry_arrival.grid(row=3, column=1)

# Кнопки
tk.Button(root, text="Добавить", command=add).grid(row=4, column=0, pady=5)
tk.Button(root, text="Обновить список", command=refresh_list).grid(row=4, column=1)

# Таблица для вывода
columns = ("ID", "Имя", "Вид", "Возраст", "Дата")
tree = ttk.Treeview(root, columns=columns, show='headings')
for col in columns:
    tree.heading(col, text=col)
tree.grid(row=5, column=0, columnspan=2)

refresh_list()
root.mainloop()