import configparser
import tkinter as tk
from tkinter import ttk, messagebox, font
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
}
# Инициализация БД
import database
database.init_db()

# Переменные
blink_timers = {}
fullscreen = False
species_map = {}
cfg = configparser.ConfigParser(allow_no_value=True)
cfg.optionxform = str  # чтобы имена сохранили регистр
cfg.read('spesies_config.txt', encoding='utf-8')
for section in cfg.sections():
    # у нас в секции нет ключ=значение, а просто строки
    breeds = [k for k in cfg[section].keys()]
    species_map[section] = breeds

# Функции действий

def autofit_columns(tree, columns, padding=10):
    """
    Для каждой колонки считает максимальную ширину текста (заголовка + всех ячеек)
    и выставляет её с небольшим отступом padding.
    """
    # Используем дефолтный шрифт приложения
    tv_font = font.nametofont("TkDefaultFont")

    for col in columns:
        # измерим ширину заголовка
        max_width = tv_font.measure(col)
        # измерим каждую ячейку в этой колонке
        for item in tree.get_children():
            cell_text = str(tree.set(item, col))
            w = tv_font.measure(cell_text)
            if w > max_width:
                max_width = w
        # выставляем ширину + padding
        tree.column(col, width=max_width + padding)

def open_adopt_dialog(animal_id):
    dlg = tk.Toplevel(root)
    dlg.title("Передача животного")
    ttk.Label(dlg, text="Имя владельца").grid(row=0, column=0, sticky='w', pady=2)
    ent_owner = ttk.Entry(dlg); ent_owner.grid(row=0, column=1, pady=2)
    ttk.Label(dlg, text="Контакт владельца").grid(row=1, column=0, sticky='w', pady=2)
    ent_contact = ttk.Entry(dlg); ent_contact.grid(row=1, column=1, pady=2)
    ttk.Label(dlg, text="Дата передачи (YYYY-MM-DD)").grid(row=2, column=0, sticky='w', pady=2)
    ent_date = ttk.Entry(dlg); ent_date.grid(row=2, column=1, pady=2)
    ent_date.insert(0, date.today().isoformat())

    def confirm():
        owner = ent_owner.get().strip()
        contact = ent_contact.get().strip()
        ad_date = ent_date.get().strip()
        if not owner or not contact:
            messagebox.showwarning("Ошибка", "Укажите имя и контакт владельца")
            return
        try:
            date.fromisoformat(ad_date)
        except ValueError:
            messagebox.showwarning("Ошибка", "Неверный формат даты")
            return
        # Сохраняем в adoptions и удаляем из animals
            # Сначала получаем snapshot данных животного
        row = database.get_animal_by_id(animal_id)
        # row = (id, name, species, birth_date, age_estimated, arrival_date, cage, quarantine)
        _, name, species, bd, est_flag, arr, _, _ = row

        # Сохраняем в adoptions вместе с данными животного
        database.add_adoption(
            animal_id,
            name, species, bd, est_flag, arr,
            owner, contact, ad_date
        )
        # Только потом удаляем из основной таблицы
        database.delete_animal(animal_id)

        dlg.destroy()
        refresh_list()
        refresh_adopted_list()

    ttk.Button(dlg, text="Подтвердить", command=confirm).grid(row=3, column=0, pady=5)
    ttk.Button(dlg, text="Отмена",    command=dlg.destroy).grid(row=3, column=1, pady=5)

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
        re

    # Приём животного
    if col_name == "Adopt":
        row_id = tree.identify_row(event.y)
    if not row_id:
        return
    animal_id = tree.item(row_id)["values"][0]
    open_adopt_dialog(animal_id)
    return



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
    selected_species = combobox_species.get().strip()
    breed   = combobox_breed.get().strip()
    bd = entry_birth.get().strip()
    est = entry_est.get().strip()
    arrival = entry_arrival.get().strip() or date.today().isoformat()
    cage = entry_cage.get().strip()
    quarantine_until = entry_quarantine.get().strip()
    if not selected_species:
        messagebox.showwarning("Ошибка", "Выберите вид"); return
    # Собираем «вид / порода»
    species = f"{selected_species} / {breed}" if breed else species

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
            cage, days_left, "🤝", "🗑"
        )
        item = tree.insert(
            '',
            'end',
            values=(
                id_, name, full_species,
                bd_disp, age_disp,
                arr,
                cage, days_left,
                "🤝",   # иконка для приёма
                "🗑"
            ),
            tags=tags
        )

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

# === Главное окно ===
root = tk.Tk()
root.title("Приют: учёт животных")
root.geometry("900x600")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# === Верх: Notebook с двумя вкладками ===
notebook = ttk.Notebook(root)
tab_shelter = ttk.Frame(notebook)
tab_adopted = ttk.Frame(notebook)
notebook.add(tab_shelter, text="Приют")
notebook.add(tab_adopted, text="Переданы")
notebook.grid(row=0, column=0, sticky="nsew")
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)

# === Tab “Приют” ===
# 1) Настройка сетки
tab_shelter.columnconfigure(0, weight=1)
tab_shelter.columnconfigure(1, weight=1)
tab_shelter.rowconfigure(2, weight=1)

# 2) Фрейм “Основная информация”
frm_inputs = ttk.LabelFrame(tab_shelter, text="Основная информация")
frm_inputs.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
frm_inputs.columnconfigure(0, weight=0)
frm_inputs.columnconfigure(1, weight=1)

ttk.Label(frm_inputs, text="Имя").grid(row=0, column=0, sticky="w", pady=2)
entry_name = ttk.Entry(frm_inputs); entry_name.grid(row=0, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Вид").grid(row=1, column=0, sticky="w", pady=2)
combobox_species = ttk.Combobox(
    frm_inputs,
    values=list(species_map.keys()),
    state="readonly"
)
combobox_species.grid(row=1, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Порода").grid(row=2, column=0, sticky="w", pady=2)
combobox_breed = ttk.Combobox(
    frm_inputs,
    values=[],
    state="readonly"
)
combobox_breed.grid(row=2, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Дата рождения\n(YYYY-MM-DD)").grid(row=3, column=0, sticky="w", pady=2)
entry_birth = ttk.Entry(frm_inputs); entry_birth.grid(row=3, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="ИЛИ оценка возраста\n(месяцы)").grid(row=4, column=0, sticky="w", pady=2)
entry_est = ttk.Entry(frm_inputs); entry_est.grid(row=4, column=1, sticky="ew", pady=2)

ttk.Label(frm_inputs, text="Дата поступления\n(YYYY-MM-DD)").grid(row=5, column=0, sticky="w", pady=2)
entry_arrival = ttk.Entry(frm_inputs); entry_arrival.grid(row=5, column=1, sticky="ew", pady=2)

# 3) Фрейм “Клетка / Карантин”
frm_quarantine = ttk.LabelFrame(tab_shelter, text="Клетка / Карантин")
frm_quarantine.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
frm_quarantine.columnconfigure(0, weight=0)
frm_quarantine.columnconfigure(1, weight=1)

ttk.Label(frm_quarantine, text="Клетка").grid(row=0, column=0, sticky="w", pady=2)
entry_cage = ttk.Entry(frm_quarantine); entry_cage.grid(row=0, column=1, sticky="ew", pady=2)
entry_cage.insert(0, get_default_quarantine_cage())

ttk.Label(frm_quarantine, text="Окончание\nкарантина").grid(row=1, column=0, sticky="w", pady=2)
entry_quarantine = ttk.Entry(frm_quarantine); entry_quarantine.grid(row=1, column=1, sticky="ew", pady=2)
entry_quarantine.insert(0, (date.today() + timedelta(days=10)).isoformat())

# 4) Фрейм кнопок
frm_buttons = ttk.Frame(tab_shelter)
frm_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
frm_buttons.columnconfigure(0, weight=1)
frm_buttons.columnconfigure(1, weight=1)

btn_add = ttk.Button(frm_buttons, text="Добавить", command=add)
btn_add.grid(row=0, column=0, sticky="ew", padx=5)
btn_refresh = ttk.Button(frm_buttons, text="Обновить список", command=refresh_list)
btn_refresh.grid(row=0, column=1, sticky="ew", padx=5)

# 5) Таблица животных
columns = (
    "ID", "Имя", "Вид",
    "Дата рождения", "Возраст (мес.)",
    "Дата поступления",
    "Клетка", "Осталось дней карантина",
    "Adopt", "Del"
)

table_frame = ttk.Frame(tab_shelter)
table_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
table_frame.columnconfigure(0, weight=1)
table_frame.rowconfigure(0, weight=1)

tree = ttk.Treeview(table_frame, columns=columns, show='headings')
for col in columns:
    tree.heading(col, text=col if col not in ("Adopt", "Del") else "")
# настраиваем ширины
tree.column("ID", width=30, anchor='center')
tree.column("Имя", width=100, anchor='w')
tree.column("Вид", width=150, anchor='w')
tree.column("Дата рождения", width=100, anchor='center')
tree.column("Возраст (мес.)", width=90, anchor='center')
tree.column("Дата поступления", width=100, anchor='center')
tree.column("Клетка", width=70, anchor='center')
tree.column("Осталось дней карантина", width=150, anchor='center')
tree.column("Adopt", width=30, anchor='center')
tree.column("Del", width=30, anchor='center')

vsb = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=vsb.set)
tree.grid(row=0, column=0, sticky='nsew')
vsb.grid(row=0, column=1, sticky='ns')

tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# === Tab “Переданы” ===
tab_adopted.columnconfigure(0, weight=1)
tab_adopted.rowconfigure(1, weight=1)
tab_adopted.grid_propagate(False)
tab_adopted.rowconfigure(1, weight=1)
tab_adopted.columnconfigure(0, weight=1)

ttk.Label(tab_adopted, text="Сданные животные", font=("", 14)).grid(row=0, column=0, pady=5)

# Frame для таблицы (растягивается по ширине и высоте)
frm_adopt = ttk.Frame(tab_adopted)
frm_adopt.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
frm_adopt.rowconfigure(0, weight=1)
frm_adopt.columnconfigure(0, weight=1)

# Новые колонки: убрали собственный ID, добавили все поля из animals
columns_adopted = (
    "ID животного", "Имя", "Вид",
    "Дата рождения", "Возраст (мес.)", "Дата поступления",
    "Имя владельца", "Контакт", "Дата передачи"
)
tree_adopted = ttk.Treeview(
    frm_adopt,
    columns=columns_adopted,
    show='headings'
)
# обычный вертикальный
vsb2 = ttk.Scrollbar(frm_adopt, orient='vertical', command=tree_adopted.yview)
tree_adopted.configure(yscrollcommand=vsb2.set)

# горизонтальный — чтобы при широкой таблице не “уезжать” за край
hsb2 = ttk.Scrollbar(frm_adopt, orient='horizontal', command=tree_adopted.xview)
tree_adopted.configure(xscrollcommand=hsb2.set)

# размещаем
tree_adopted.grid(row=0, column=0, sticky='nsew')
vsb2.grid(row=0, column=1, sticky='ns')
hsb2.grid(row=1, column=0, columnspan=2, sticky='ew')

# Заголовки и авторастяжка
for c in columns_adopted:
    tree_adopted.heading(c, text=c)
    tree_adopted.column(c, anchor='center')

def refresh_adopted_list():
    tree_adopted.delete(*tree_adopted.get_children())
    today = date.today()

    for rec in database.get_all_adoptions():
        # rec = (id, animal_id, name, species,
        #        birth_date, age_estimated, arrival_date,
        #        owner_name, owner_contact, adoption_date)
        (_, animal_id, name, species, bd, est_flag,
         arr, owner, contact, ad_date) = rec

        # пересчитать возраст
        bdate = date.fromisoformat(bd)
        months = (today.year*12 + today.month) - (bdate.year*12 + bdate.month)
        age_disp = f"~{months}" if est_flag else str(months)
        bd_disp  = f"~{bd}" if est_flag else bd
        arr_disp = arr or ""

        tree_adopted.insert('', 'end', values=(
            animal_id, name, species,
            bd_disp, age_disp, arr_disp,
            owner, contact, ad_date
        ))

    autofit_columns(tree_adopted, columns_adopted)

# === Инициализация и первый показ данных ===
database.init_db()
refresh_list()
refresh_adopted_list()
def on_species_selected(event):
    sp = combobox_species.get()
    combobox_breed['values'] = species_map.get(sp, [])
    combobox_breed.set('')  # очистить прошлый выбор

combobox_species.bind("<<ComboboxSelected>>", on_species_selected)

# ======= БИНДИНГИ =======
tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# — теги для раскраски строк
tree.tag_configure('quarantine', background='#FFF59D')
tree.tag_configure('expired', background='#C8E6C9')

# Привязка клавиш
root.bind("<F11>", toggle_fullscreen)
root.bind("<Escape>", lambda e: toggle_fullscreen() if fullscreen else None)
tree.bind("<Button-1>", on_tree_click)
tree.bind("<Double-1>", on_double_click)

# словарь для хранения ID таймеров мигания
blink_timers = {}

# Запуск
refresh_list()
root.mainloop()

