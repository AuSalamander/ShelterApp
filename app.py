import tkinter as tk
from tkinter import ttk, messagebox
import database  # файл database.py
from datetime import date, timedelta
import re 

# номер колонки в Treeview → имя поля в БД
COLUMN_MAP = {
    "#2": "name",                # колонка «Имя»
    "#3": "species",             # колонка «Вид»
    "#4": "birth_date",          # колонка «Дата рождения»
    "#6": "arrival_date",        # колонка «Дата поступления»
    "#7": "cage_number",         # колонка «Клетка»
    "#8": "quarantine_until",    # колонка «Осталось дней карантина»
    # столбец "#9" — это «Del», его не редактируем
}
# Инициализация БД
database.init_db()

# Функции действий

def blink_row(item):
    current = list(tree.item(item, 'tags'))
    if 'expired' in current:
        # временно убираем зелёный фон
        new_tags = [t for t in current if t != 'expired']
    else:
        # возвращаем зелёный фон
        new_tags = current + ['expired']
    tree.item(item, tags=new_tags)
    blink_timers[item] = root.after(100, lambda: blink_row(item))

# вернёт дату, отстоящую на `months` месяцев назад от today
def subtract_months(today: date, months: int) -> date:
    total = today.year * 12 + today.month - 1 - months
    year = total // 12
    month = total % 12 + 1
    day = min(today.day, (date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)).day)
    return date(year, month, day)

def on_tree_click(event):
    # только ячейки
    if tree.identify("region", event.x, event.y) != "cell":
        return

    # выясняем, на какую колонку кликнули
    col_id = tree.identify_column(event.x)      # строка вида "#1", "#2", ...
    col_index = int(col_id.replace("#", "")) - 1
    col_name = tree["columns"][col_index]        # имя колонки из columns = (...)

    # если это колонка «Del» — удаляем
    if col_name == "Del":
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        animal_id = tree.item(row_id)["values"][0]
        if messagebox.askyesno("Подтверждение", f"Удалить ID {animal_id}?"):
            database.delete_animal(animal_id)
            refresh_list()


def on_double_click(event):
    # Обрабатываем только клики по ячейкам
    if tree.identify("region", event.x, event.y) != "cell":
        return

    col_id = tree.identify_column(event.x)  # например, "#4"
    # Разрешаем редактировать лишь те колонки, что в COLUMN_MAP
    if col_id not in COLUMN_MAP:
        return

    row_id = tree.identify_row(event.y)
    if not row_id:
        return

    # Получаем имя поля в БД
    field = COLUMN_MAP[col_id]
    # Координаты ячейки
    x, y, width, height = tree.bbox(row_id, col_id)
    old_value = tree.set(row_id, col_id)

    entry = tk.Entry(tree)
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
        animal_id = tree.item(row_id)["values"][0]
        database.update_animal_field(animal_id, field, new_value)
        entry.destroy()
        refresh_list()

    entry.bind("<Return>", save_edit)
    entry.bind("<FocusOut>", save_edit)


def add():
    name = entry_name.get().strip()
    species = entry_species.get().strip()
    bd = entry_birth.get().strip()
    est = entry_est.get().strip()
    arrival = entry_arrival.get().strip() or date.today().isoformat()
    cage = entry_cage.get().strip()
    quarantine_until = entry_quarantine.get().strip()

    if not name:
        messagebox.showwarning("Ошибка", "Имя обязательно")
        return

    # Проверяем, что клетка не занята
    if cage in database.get_all_cage_numbers():
        messagebox.showwarning("Ошибка", f"Клетка {cage} уже занята")
        return

    # Дата рождения / оценка
    if bd:
        try:
            bdate = date.fromisoformat(bd)
            est_flag = 0
        except ValueError:
            messagebox.showwarning("Ошибка", "Неверный формат даты рождения")
            return
    elif est:
        try:
            months = int(est)
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
        qdate = date.fromisoformat(quarantine_until)
    except ValueError:
        messagebox.showwarning("Ошибка", "Неправильный формат даты окончания карантина")
        return

    database.add_animal(
        name,
        species,
        bdate.isoformat(),
        est_flag,
        arrival,
        cage,
        qdate.isoformat()
    )
    messagebox.showinfo("Готово", "Животное добавлено")
    refresh_list()


def refresh_list():
    # Останавливаем все текущие мигания
    for item, timer in list(blink_timers.items()):
        root.after_cancel(timer)
    blink_timers.clear()

    # Очищаем таблицу
    tree.delete(*tree.get_children())

    today = date.today()
    for (id_, name, species, bd, est_flag,
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
            id_, name, species,
            bd_disp, age_disp,
            arr or "",
            cage, days_left, "🗑"
        )
        item = tree.insert('', 'end', values=values, tags=tags)

        # если карантин закончился — запускаем мигание
        if 'expired' in tags:
            blink_row(item)


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

def get_default_quarantine_cage():
    taken = database.get_all_cage_numbers()
    # выбираем только карантинные: начинаются с "К" и 4 hex-цифры
    used = {int(cn[1:], 16) for cn in taken if cn.startswith("К")}
    for i in range(0x10000):
        if i not in used:
            return f"К{i:04X}"
    raise RuntimeError("Нет свободных карантинных клеток")

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

# === ФРЕЙМ ДЛЯ ОСНОВНОЙ ИНФОРМАЦИИ ===


frm_inputs = ttk.LabelFrame(root, text="Основная информация")
frm_inputs.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
# Делаем так, чтобы второй столбец (ввод) растягивался,
# а первый (метки) — нет
frm_inputs.columnconfigure(0, weight=0)
frm_inputs.columnconfigure(1, weight=1)

ttk.Label(frm_inputs, text="Имя").grid(row=0, column=0, sticky="w", pady=2)
entry_name = ttk.Entry(frm_inputs)
entry_name.grid(row=0, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Вид").grid(row=1, column=0, sticky="w", pady=2)
entry_species = ttk.Entry(frm_inputs)
entry_species.grid(row=1, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Дата рождения\n(YYYY-MM-DD)").grid(row=2, column=0, sticky="w", pady=2)
entry_birth = ttk.Entry(frm_inputs)
entry_birth.grid(row=2, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="ИЛИ оценка возраста\n(месяцы)").grid(row=3, column=0, sticky="w", pady=2)
entry_est = ttk.Entry(frm_inputs)
entry_est.grid(row=3, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Дата поступления\n(YYYY-MM-DD)").grid(row=4, column=0, sticky="w", pady=2)
entry_arrival = ttk.Entry(frm_inputs)
entry_arrival.grid(row=4, column=1, sticky="ew", pady=2)


# === ФРЕЙМ ДЛЯ КЛЕТКИ И КАРАНТИНА ===
frm_quarantine = ttk.LabelFrame(root, text="Клетка / Карантин")
frm_quarantine.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
frm_quarantine.columnconfigure(0, weight=0)
frm_quarantine.columnconfigure(1, weight=1)

ttk.Label(frm_quarantine, text="Клетка").grid(row=0, column=0, sticky="w", pady=2)
entry_cage = ttk.Entry(frm_quarantine)
entry_cage.grid(row=0, column=1, sticky="ew", pady=2)
entry_cage.insert(0, get_default_quarantine_cage())

ttk.Label(frm_quarantine, text="Окончание\nкарантина").grid(row=1, column=0, sticky="w", pady=2)
entry_quarantine = ttk.Entry(frm_quarantine)
entry_quarantine.grid(row=1, column=1, sticky="ew", pady=2)
entry_quarantine.insert(0, (date.today() + timedelta(days=10)).isoformat())


# Убедитесь, что у root тоже настроены веса,
# чтобы оба фрейма растягивались поровну:
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)


# Кнопки
frm_buttons = ttk.Frame(root, padding=(10, 5))
frm_buttons.grid(row=4, column=0, columnspan=2, sticky="ew")
frm_buttons.columnconfigure(0, weight=1)
frm_buttons.columnconfigure(1, weight=1)

btn_add = ttk.Button(frm_buttons, text="Добавить", command=add)
btn_add.grid(row=0, column=0, sticky="ew", padx=5)
btn_refresh = ttk.Button(frm_buttons, text="Обновить список", command=refresh_list)
btn_refresh.grid(row=0, column=1, sticky="ew", padx=5)


# ======= ПЕРЕОПРЕДЕЛЕНИЕ COLUMNS =======
columns = (
    "ID", "Имя", "Вид",
    "Дата рождения", "Возраст (мес.)",
    "Дата прибытия",
    "Клетка", "Осталось дней карантина", "Del"
)

# ======= FRAME ДЛЯ ТАБЛИЦЫ И СКРОЛЛБАРА =======
table_frame = ttk.Frame(root)
table_frame.grid(row=5, column=0, columnspan=3, sticky='nsew')
table_frame.rowconfigure(0, weight=1)
table_frame.columnconfigure(0, weight=1)



# ======= СОЗДАЁМ Treeview =======



tree = ttk.Treeview(
    table_frame,
    columns=columns,
    show='headings'
)
# Заголовки и базовые ширины
for col in columns:
    tree.heading(col, text= col)
# Настройка отдельных колонок
tree.column("ID", width=20, anchor='center')
tree.column("Имя",width=100, anchor='center')
tree.column("Вид",width=100, anchor='center')
tree.column("Дата рождения", width=100, anchor='center')
tree.column("Возраст (мес.)", width=90, anchor='center')
tree.column("Дата прибытия", width=100, anchor='center')
tree.column("Клетка", width=70, anchor='center')
tree.column("Осталось дней карантина", width=150, anchor='center')
tree.column("Del", width=30, anchor='center')

# ======= СКРОЛЛБАР =======
vsb = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=vsb.set)

# ======= РАЗМЕЩЕНИЕ =======
tree.grid(row=0, column=0, sticky='nsew')
vsb.grid(row=0, column=1, sticky='ns')

# ======= БИНДИНГИ =======
tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# — теги для раскраски строк
tree.tag_configure('quarantine', background='#FFF59D')
tree.tag_configure('expired', background='#C8E6C9')

# Привязка клавиш
root.bind('<F11>', toggle_fullscreen)
root.bind('<Escape>', end_fullscreen)
tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# словарь для хранения ID таймеров мигания
blink_timers = {}

# Запуск
refresh_list()
root.mainloop()

