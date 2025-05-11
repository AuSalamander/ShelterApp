import tkinter as tk
from tkinter import ttk, messagebox
import database  # файл database.py
from datetime import date

# Инициализация БД
database.init_db()

# Функции действий

def on_tree_click(event):
    # определяем, куда кликнули
    region = tree.identify("region", event.x, event.y)
    col = tree.identify_column(event.x)
    row = tree.identify_row(event.y)
    # проверяем, что это ячейка столбца Del (это шестой столбец: "#6")
    if region == "cell" and col == "#6" and row:
        animal_id = tree.item(row)['values'][0]
        if messagebox.askyesno("Подтверждение", f"Удалить запись ID {animal_id}?"):
            database.delete_animal(animal_id)
            refresh_list()

def add():
    name = entry_name.get().strip()
    species = entry_species.get().strip()
    age_text = entry_age.get().strip()
    arrival = entry_arrival.get().strip() or date.today().isoformat()
    try:
        age = int(age_text) if age_text else 0
    except ValueError:
        messagebox.showwarning("Ошибка", "Возраст должен быть числом")
        return
    if not name:
        messagebox.showwarning("Ошибка", "Имя обязательно")
        return
    database.add_animal(name, species, age, arrival)
    messagebox.showinfo("Готово", "Животное добавлено")
    refresh_list()


def refresh_list():
    for row in tree.get_children():
        tree.delete(row)
    for animal in database.get_all_animals():
        tree.insert('', 'end', values=(
            animal[0],  # ID
            animal[1],  # имя
            animal[2],  # вид
            animal[3],  # возраст
            animal[4],  # дата
            "🗑"         # иконка удаления
        ))


def toggle_fullscreen(event=None):
    global fullscreen
    fullscreen = not fullscreen
    root.attributes("-fullscreen", fullscreen)


def end_fullscreen(event=None):
    global fullscreen
    fullscreen = False
    root.attributes("-fullscreen", False)

def delete():
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Ошибка", "Сначала выберите запись для удаления")
        return
    animal_id = tree.item(sel[0])['values'][0]
    if messagebox.askyesno("Подтверждение", f"Удалить животное с ID {animal_id}?"):
        database.delete_animal(animal_id)
        refresh_list()


# Главное окно
root = tk.Tk()
root.title("Приют: учёт животных")
root.columnconfigure(2, weight=1)
fullscreen = False

# Разрешаем изменение размеров и конфигурируем веса сетки
root.rowconfigure(5, weight=1)
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)

# Поля ввода
frm_inputs = ttk.Frame(root, padding=(10, 10))
frm_inputs.grid(row=0, column=0, columnspan=2, sticky="ew")

for i in range(4):
    frm_inputs.columnconfigure(i, weight=1)

ttk.Label(frm_inputs, text="Имя").grid(row=0, column=0, sticky="w")
entry_name = ttk.Entry(frm_inputs)
entry_name.grid(row=0, column=1, sticky="ew", padx=5)

ttk.Label(frm_inputs, text="Вид").grid(row=1, column=0, sticky="w")
entry_species = ttk.Entry(frm_inputs)
entry_species.grid(row=1, column=1, sticky="ew", padx=5)

ttk.Label(frm_inputs, text="Возраст").grid(row=2, column=0, sticky="w")
entry_age = ttk.Entry(frm_inputs)
entry_age.grid(row=2, column=1, sticky="ew", padx=5)

ttk.Label(frm_inputs, text="Дата (YYYY-MM-DD)").grid(row=3, column=0, sticky="w")
entry_arrival = ttk.Entry(frm_inputs)
entry_arrival.grid(row=3, column=1, sticky="ew", padx=5)

# Кнопки
frm_buttons = ttk.Frame(root, padding=(10, 5))
frm_buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
frm_buttons.columnconfigure(0, weight=1)
frm_buttons.columnconfigure(1, weight=1)

btn_add = ttk.Button(frm_buttons, text="Добавить", command=add)
btn_add.grid(row=0, column=0, sticky="ew", padx=5)
btn_refresh = ttk.Button(frm_buttons, text="Обновить список", command=refresh_list)
btn_refresh.grid(row=0, column=1, sticky="ew", padx=5)


# Таблица
columns = ("ID", "Имя", "Вид", "Возраст", "Дата", "Del")
tree = ttk.Treeview(root, columns=columns, show='headings')
for idx, col in enumerate(columns):
    tree.heading(col, text=col)
    tree.column(col, anchor="center")
tree.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
for col in columns:
    heading = "" if col == "Del" else col
    tree.heading(col, text=heading)
# столбец с иконкой удаления
tree.column("Del", width=30, anchor="center")

# Поддержка прокрутки
scroll = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscroll=scroll.set)
scroll.grid(row=5, column=2, sticky="ns")

# Привязка клавиш для полноэкранного режима
root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', end_fullscreen)
tree.bind("<Button-1>", on_tree_click)

# Запуск
refresh_list()
root.mainloop()

