import tkinter as tk
from tkinter import ttk, messagebox
import database  # файл database.py
from datetime import date

# номер колонки в Treeview → имя поля в БД
COLUMN_MAP = {
    "#2": "name",
    "#3": "species",
    "#4": "birth_date",
    "#5": "age_months",   
    "#6": "arrival_date",
    "#7": "Del",
}
# Инициализация БД
database.init_db()

# Функции действий

def on_tree_click(event):
    # определяем, куда кликнули
    region = tree.identify("region", event.x, event.y)
    col = tree.identify_column(event.x)
    row = tree.identify_row(event.y)
    # проверяем, что это ячейка столбца Del (это шестой столбец: "#6")
    if region == "cell" and col == "#7" and row:
        animal_id = tree.item(row)['values'][0]
        if messagebox.askyesno("Подтверждение", f"Удалить запись ID {animal_id}?"):
            database.delete_animal(animal_id)
            refresh_list()

def on_double_click(event):
    # работаем только с ячейками
    if tree.identify("region", event.x, event.y) != "cell":
        return
    col = tree.identify_column(event.x)
    # редактируем только колонки, что есть в мапе
    if col not in COLUMN_MAP:
        return
    row = tree.identify_row(event.y)
    if not row:
        return

    # координаты ячейки
    x, y, width, height = tree.bbox(row, col)
    old_value = tree.set(row, col)

    # создаём Entry прямо над ячейкой
    entry = tk.Entry(tree)
    entry.place(x=x, y=y, width=width, height=height)
    entry.insert(0, old_value)
    entry.focus()

    def save_edit(e):
        new_value = entry.get()
        animal_id = tree.item(row)['values'][0]
        field = COLUMN_MAP[col]
        database.update_animal_field(animal_id, field, new_value)
        entry.destroy()
        refresh_list()

    # сохраняем на уходе фокуса и на Enter
    entry.bind("<FocusOut>", save_edit)
    entry.bind("<Return>", save_edit)

def add():
    name = entry_name.get().strip()
    species = entry_species.get().strip()
    bd = entry_birth.get().strip()
    est = entry_est.get().strip()
    arrival = entry_arrival.get().strip() or date.today().isoformat()
    if not name:
        messagebox.showwarning("Ошибка", "Имя обязательно"); return
    # проверяем ввод
    if bd:
        # если указали дату рождения — вычисляем месяцы
        try:
            y, m, d = map(int, bd.split('-'))
            bdate = date(y, m, d)
            delta = date.today().year*12 + date.today().month - (y*12 + m)
            age_m = delta
            est_flag = 0
        except:
            messagebox.showwarning("Ошибка", "Неверный формат даты рождения"); return
    elif est:
        try:
            age_m = int(est)
            est_flag = 1
            bdate = None
        except:
            messagebox.showwarning("Ошибка", "Оценка должна быть числом"); return
    else:
        messagebox.showwarning("Ошибка", "Укажите дату рождения или оценку возраста"); return
    database.add_animal(name, species, bdate.isoformat() if bdate else None, age_m, est_flag, arrival)
    messagebox.showinfo("Готово", "Животное добавлено")
    refresh_list()


def refresh_list():
    tree.delete(*tree.get_children())
    for id_, name, species, bd, months, est_flag, arr in database.get_all_animals():
        bd_disp = bd or ""
        age_disp = f"~{months}" if est_flag else str(months)
        arr_disp = arr or ""
        tree.insert('', 'end', values=(id_, name, species, bd_disp, age_disp, arr_disp, "🗑"))


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
root.columnconfigure(2, weight=0)  # третья колонка с кнопкой

# строка 5 (где будет таблица) тоже растягивается
root.rowconfigure(5, weight=1)

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

ttk.Label(frm_inputs, text="Дата рождения (YYYY-MM-DD)").grid(row=2, column=0, sticky="w")
entry_birth = ttk.Entry(frm_inputs)
entry_birth.grid(row=2, column=1, sticky="ew", padx=5)

ttk.Label(frm_inputs, text="ИЛИ оценка возраста (месяцы)").grid(row=3, column=0, sticky="w")
entry_est = ttk.Entry(frm_inputs)
entry_est.grid(row=3, column=1, sticky="ew", padx=5)

ttk.Label(frm_inputs, text="Дата поступления (YYYY-MM-DD)").grid(row=4, column=0, sticky="w")
entry_arrival = ttk.Entry(frm_inputs)
entry_arrival.grid(row=4, column=1, sticky="ew", padx=5)

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
columns = ("ID", "Имя", "Вид", "Дата рождения (YYYY-MM-DD)", "Возраст (мес.)", "Дата поступления (YYYY-MM-DD)", "Del")
tree = ttk.Treeview(root, columns=columns, show='headings')
for idx, col in enumerate(columns):
    tree.heading(col, text=col)
    tree.column(col, anchor="center")
tree.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
for col in columns:
    heading = col
    tree.heading(col, text=heading)

# по умолчанию все колонки растягиваем, но Del остаётся узкой
tree.column("Дата поступления (YYYY-MM-DD)", anchor="center")
tree.column("Del", width=30, anchor="center")

# Поддержка прокрутки
scroll = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
tree.configure(yscroll=scroll.set)
scroll.grid(row=5, column=2, sticky="ns")

# Привязка клавиш для полноэкранного режима
root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', end_fullscreen)
tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# Запуск
refresh_list()
root.mainloop()

