import configparser
import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
import database  # файл database.py
from datetime import date, timedelta
import re 
import tkinter.simpledialog as sd
import os
import glob
import shutil

database.init_db()

# номер колонки в Treeview → имя поля в БД
COLUMN_MAP = {
    "#2": "name",                # колонка «Имя»
    "#3": "species",             # колонка «Вид»
    "#4": "birth_date",          # колонка «Дата рождения»
    "#6": "arrival_date",        # колонка «Дата поступления»
    "#7": "cage_number",         # колонка «Клетка»
    "#8": "quarantine_until",    # колонка «Осталось дней карантина»
}

# Переменные
notified_animals = set()
blink_list_timer = None
blink_list_state = False
blink_index = None
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
today = date.today()
cfg = {}
with open("cfg.txt", encoding="utf-8") as f:
    for raw in f:
        line = raw.split('#', 1)[0].strip()  # отсекаем всё после #
        if not line or '=' not in line:
            continue
        key, val = line.split('=', 1)
        try:
            cfg[key.strip()] = int(val.strip())
        except ValueError:
            # если не число — можно хранить как строку или пропускать
            cfg[key.strip()] = val.strip()
tip = None

# Функции действий

def open_event_dialog(aid, refresh_cb):
    dlg = tk.Toplevel(root)
    name = database.get_animal_by_id(aid)[1]
    dlg.title(f"Новое событие для #{aid} ({name})")

    # Поля
    ttk.Label(dlg, text="Тип события:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    ent_type = ttk.Entry(dlg); ent_type.grid(row=0, column=1, sticky='ew', padx=5, pady=2)

    ttk.Label(dlg, text="Дата начала (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', padx=5, pady=2)
    ent_ds = ttk.Entry(dlg); ent_ds.grid(row=1, column=1, sticky='ew', padx=5, pady=2)

    ttk.Label(dlg, text="Дата окончания (опционально):").grid(row=2, column=0, sticky='w', padx=5, pady=2)
    ent_de = ttk.Entry(dlg); ent_de.grid(row=2, column=1, sticky='ew', padx=5, pady=2)

    ttk.Label(dlg, text="Заключение:").grid(row=3, column=0, sticky='nw', padx=5, pady=2)
    txt_concl = tk.Text(dlg, height=4); txt_concl.grid(row=3, column=1, sticky='ew', padx=5, pady=2)

    ttk.Label(dlg, text="Результаты:").grid(row=4, column=0, sticky='nw', padx=5, pady=2)
    txt_res = tk.Text(dlg, height=4); txt_res.grid(row=4, column=1, sticky='ew', padx=5, pady=2)

    # Выбор документов
    doc_paths = []
    def choose_docs():
        files = filedialog.askopenfilenames(title="Выберите файлы")
        if files:
            doc_paths[:] = files
            lbl_docs.config(text=f"{len(files)} файл(ов) выбрано")
    btn_docs = ttk.Button(dlg, text="Прикрепить документы…", command=choose_docs)
    btn_docs.grid(row=5, column=0, columnspan=2, pady=5)
    lbl_docs = ttk.Label(dlg, text="Файлы не выбраны")
    lbl_docs.grid(row=6, column=0, columnspan=2, pady=(0,5))

    # кнопки
    def on_confirm():
        etype = ent_type.get().strip()
        ds = ent_ds.get().strip()
        de = ent_de.get().strip() or None
        concl = txt_concl.get("1.0", "end").strip() or None
        res = txt_res.get("1.0", "end").strip() or None
        if not etype or not ds:
            messagebox.showwarning("Ошибка", "Укажите тип и дату начала")
            return

        # 1) создаём запись
        eid = database.add_event(aid, etype, ds, de, concl, res)

        # 2) копируем файлы (если есть) в docs/aid/ с префиксом eid_
        dest_dir = os.path.join("docs", str(aid))
        os.makedirs(dest_dir, exist_ok=True)
        for p in doc_paths:
            fn = f"{eid}_{os.path.basename(p)}"
            shutil.copy(p, os.path.join(dest_dir, fn))

        dlg.destroy()
        refresh_cb()

    frm_btn = ttk.Frame(dlg)
    frm_btn.grid(row=7, column=0, columnspan=2, pady=10)
    ttk.Button(frm_btn, text="Отмена", command=dlg.destroy).grid(row=0, column=0, padx=5)
    ttk.Button(frm_btn, text="Создать", command=on_confirm).grid(row=0, column=1, padx=5)

    # растягиваем поля
    dlg.columnconfigure(1, weight=1)
    dlg.transient(root)
    dlg.grab_set()
    ent_type.focus()


def update_med_tab_title():
    base = "Медицина"
    if notified_animals:
        notebook.tab(tab_med,
                     text=base,
                     image=_yellow_dot,
                     compound='right')
    else:
        notebook.tab(tab_med,
                     text=base,
                     image=_blank_img,
                     compound='right')

def blink_list_item(index):
    global blink_list_timer, blink_list_state, blink_index
    # отменяем старое мигание
    if blink_list_timer is not None:
        root.after_cancel(blink_list_timer)
        # сбросим предыдущую строку
        if blink_index is not None:
            lst_med.itemconfig(blink_index, bg='')
    blink_index = index
    blink_list_state = False

    def _blink():
        global blink_list_state, blink_list_timer
        # чередуем bg и пустой
        color = 'yellow' if blink_list_state else ''
        lst_med.itemconfig(blink_index, bg=color)
        blink_list_state = not blink_list_state
        blink_list_timer = root.after(250, _blink)

    _blink()

def stop_list_blink():
    global blink_list_timer, blink_index
    if blink_list_timer is not None:
        root.after_cancel(blink_list_timer)
        blink_list_timer = None
    if blink_index is not None:
        lst_med.itemconfig(blink_index, bg='')
        blink_index = None

def on_med_select(event):
    sel = lst_med.curselection()
    if not sel:
        return
    text = lst_med.get(sel[0])
    # ожидаем формат "ID:<число>: <имя>"
    parts = text.split(":", 2)
    if len(parts) < 3:
        return
    id_part = parts[1].strip()
    if not id_part.isdigit():
        return
    aid = int(id_part)
    open_medical(aid)



# минимальный тултип для Listbox
tip = None
def on_motion(event):
    global tip
    # получаем индекс ближайшего элемента
    idx = lst_med.nearest(event.y)
    # bbox = (x, y, width, height) или () если элемент не виден
    bbox = lst_med.bbox(idx)
    # если нет bbox или курсор не внутри области bbox — скрываем тултип
    if not bbox:
        if tip:
            tip.destroy()
            tip = None
        return
    x0, y0, w0, h0 = bbox
    # проверяем, что event.y действительно в пределах этой строки
    if event.y < y0 or event.y > y0 + h0:
        if tip:
            tip.destroy()
            tip = None
        return

    # теперь можно показывать тултип
    full = med_names[idx]
    if tip:
        tip.destroy()
    tip = tk.Toplevel(lst_med)
    tip.wm_overrideredirect(True)
    # позиционируем рядом с элементом
    abs_x = lst_med.winfo_rootx() + w0 + 2
    abs_y = lst_med.winfo_rooty() + y0
    tip.geometry(f"+{abs_x}+{abs_y}")
    tk.Label(tip, text=full, background="lightyellow").pack()

def on_leave(event):
    global tip
    if tip:
        tip.destroy()
        tip = None

def schedule_dialog(aid, refresh_cb):
    d = sd.askstring("Назначить процедуру", "Тип,дата(YYYY-MM-DD):")
    if not d: return
    typ, dt = map(str.strip, d.split(",",1))
    database.schedule_procedure(aid, typ, dt)
    refresh_cb()

def complete_dialog(tree, refresh_cb):
    sel = tree.selection()
    if not sel: return
    pid = int(sel[0])
    res = sd.askstring("Результат", "Введите результат:")
    if not res: return
    completed_at = date.today().isoformat()
    database.complete_procedure(pid, completed_at, res)
    refresh_cb()

def open_medical(aid):
    # Переключаемся на вкладку «Медицина»
    notebook.select(tab_med)

    if aid in notified_animals:
        notified_animals.remove(aid)
        update_med_tab_title()
        refresh_med_list()
        stop_list_blink()

    # Очищаем detail_frame
    for w in detail_frame.winfo_children():
        w.destroy()

    # 3. Адаптивный заголовок с корректным начальным размером
    name = database.get_animal_by_id(aid)[1]
    label_text = f"Медкарта животного #{aid} ({name})"

    style = ttk.Style()
    style.configure("Wrap.TLabel", justify="left")

    header_label = ttk.Label(
        detail_frame,
        text=label_text,
        font=("", 14),
        style="Wrap.TLabel",
        anchor="w",
        wraplength=400  # Начальное примерное значение
    )

    header_label.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 5))

    # Функция для обновления переноса
    def update_wrap(event):
        # Берем ширину фрейма минус отступы (20px)
        new_width = detail_frame.winfo_width() - 20
        # Устанавливаем минимальную ширину 100px для избежания "спагетти-текста"
        header_label.configure(wraplength=max(100, new_width))

    # Вызываем сразу после создания, чтобы установить начальное значение
    header_label.update_idletasks()  # Ждем отрисовки
    update_wrap(None)  # Инициализация

    # Привязываем к изменению размера
    detail_frame.bind("<Configure>", update_wrap)

    # 4. Создаём Canvas+Scrollbar для всего контента
    canvas = tk.Canvas(detail_frame, borderwidth=0)
    vsb = ttk.Scrollbar(detail_frame, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    # Фикс для правильного изменения размера
    def _on_frame_configure(e):
        # Обновляем привязку области прокрутки
        canvas.configure(scrollregion=canvas.bbox("all"))
        # Принудительно устанавливаем ширину фрейма равной ширине canvas
        canvas.itemconfig('all', width=e.width)

    # Настройка расширения содержимого
    detail_frame.rowconfigure(1, weight=1)
    detail_frame.columnconfigure(0, weight=1)
    canvas.columnconfigure(0, weight=1)
    scroll_frame.columnconfigure(0, weight=1)  # Добавляем расширение для scroll_frame

    # Привязка событий
    scroll_frame.bind("<Configure>", _on_frame_configure)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig("all", width=e.width))

    # Встраиваем scroll_frame в canvas
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw", tags="all")
    canvas.configure(yscrollcommand=vsb.set)

    # Размещение элементов
    canvas.grid(row=1, column=0, sticky='nsew')
    vsb.grid(row=1, column=1, sticky='ns')

    # 5. Заполняем scroll_frame по порядку:

    # --- Документы ---
    docs = sorted(glob.glob(f"docs/{aid}/*"), key=os.path.getctime)
    docs_frame = ttk.LabelFrame(scroll_frame, text="Документы")
    docs_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5), padx=2)
    docs_frame.columnconfigure(0, weight=1)

    # Добавляем глобальную переменную для контроля обновлений
    global update_lock
    update_lock = False

    def update_doc_buttons(event=None):
        global update_lock
        if update_lock:
            return
        
        try:
            update_lock = True
            frame_width = docs_frame.winfo_width()
            
            # Удаляем старые виджеты
            for w in docs_frame.winfo_children():
                w.destroy()
            
            if not docs:
                def open_docs_folder(aid):
                    # Создаем путь к папке и гарантируем её существование
                    folder_path = os.path.abspath(os.path.join("docs", str(aid)))
                    os.makedirs(folder_path, exist_ok=True)
                    
                    # Открываем папку в проводнике (работает на Windows)
                    if os.name == 'nt':  # Для Windows
                        os.startfile(folder_path)
                    else:  # Для MacOS/Linux (может потребовать настройки)
                        os.system(f'open "{folder_path}"' if sys.platform == 'darwin' else f'xdg-open "{folder_path}"')

                # В вашем коде кнопки:
                btn = tk.Button(
                    docs_frame,
                    text="Документов нет, нажмите чтобы добавить",
                    bg="red", 
                    fg="white",
                    command=lambda: open_docs_folder(aid)  # Передаем актуальный aid
                )
                btn.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
                return
            
            # Рассчитываем размеры
            temp_frame = ttk.Frame(docs_frame)
            temp_buttons = []
            for path in docs:
                btn = ttk.Button(temp_frame, text=os.path.basename(path))
                btn.grid()
                temp_frame.update_idletasks()
                temp_buttons.append(btn.winfo_width() + 10)
                btn.destroy()
            
            max_width = max(temp_buttons) if temp_buttons else 1
            columns = max(1, (frame_width - 20) // max_width)
            
            # Размещаем кнопки
            row = col = 0
            for i, path in enumerate(docs):
                if col >= columns:
                    row += 1
                    col = 0
                
                btn = ttk.Button(
                    docs_frame,
                    text=os.path.basename(path),
                    command=lambda p=path: os.startfile(p)
                )
                btn.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
                col += 1
            
            # Настройка колонок
            for c in range(columns):
                docs_frame.columnconfigure(c, weight=1)
        
        finally:
            update_lock = False

    # Первый вызов
    update_doc_buttons()

    # Оптимизированная привязка с троттлингом
    def delayed_update(event):
        docs_frame.after(100, update_doc_buttons)

    docs_frame.bind("<Configure>", delayed_update)

    btn_new_event = ttk.Button(
        scroll_frame,
        text="Добавить событие",
        command=lambda: open_event_dialog(aid, lambda: open_medical(aid))
    )
    btn_new_event.grid(row=3, column=0, sticky='w', pady=(0,10))

        # === Блок «События» ===
    # получаем список событий из БД
    # ожидается формат: [(type, date_start, date_end_or_None, conclusion, [doc_paths], results_str_or_None), ...]
    events = database.get_animal_events(aid)

    # Заголовок блока
    ttk.Label(scroll_frame, text="События", font=("", 12)).grid(
        row=2, column=0, sticky='w', pady=(10, 5)
    )

    # Canvas для горизонтальной прокрутки
    events_canvas = tk.Canvas(scroll_frame, height=2000, borderwidth=0)
    hsb = ttk.Scrollbar(scroll_frame, orient="horizontal", command=events_canvas.xview)
    events_frame = ttk.Frame(events_canvas)

    events_frame.bind(
        "<Configure>",
        lambda e: events_canvas.configure(scrollregion=events_canvas.bbox("all"))
    )
    events_canvas.create_window((0, 0), window=events_frame, anchor="nw")
    events_canvas.configure(xscrollcommand=hsb.set)

    events_canvas.grid(row=5, column=0, sticky='ew')
    hsb.grid(row=4, column=0, sticky='ew')
    COL_W = 1000
    PAD_X = 5

    # Наполняем
    for idx, (etype, ds, de, concl, doc_list, results, eid) in enumerate(events):
        col = ttk.Frame(events_frame, width=COL_W, relief='groove', padding=5)
        col.grid(row=0, column=idx, padx=(0 if idx==0 else PAD_X, 0), sticky='n')

        def attach_event_doc(event_id=eid):
            path = filedialog.askopenfilename(title="Выберите документ")
            if not path:
                return
            dest_dir = os.path.join("docs", str(aid))
            os.makedirs(dest_dir, exist_ok=True)
            fn = f"{event_id}_{os.path.basename(path)}"
            shutil.copy(path, os.path.join(dest_dir, fn))
            open_medical(aid)  # перерисуем карточку

        # 1) Тип события
        ttk.Label(col, text=etype, font=("", 10, "bold")).pack(anchor='w', pady=(0,4))

        # 2) Даты
        date_text = ds if not de or ds==de else f"{ds} — {de}"
        ttk.Label(col, text=date_text).pack(anchor='w', pady=(0,4))

        # 3) Профзаключение
        ttk.Label(col, text="Заключение:", font=("", 9, "underline")).pack(anchor='w')
        ttk.Label(col, text=concl or "—", wraplength=COL_W-10).pack(anchor='w', pady=(0,4))

        # 4) Документы
        ttk.Label(col, text="Документы:", font=("", 9, "underline")).pack(anchor='w', pady=(4,0))
        if doc_list:
            for p in doc_list:
                fn = os.path.basename(p)
                btn = ttk.Button(col, text=fn, command=lambda p=p: os.startfile(p))
                btn.pack(anchor='w', pady=1)
            ttk.Button(col, text="Прикрепить документ…", command=attach_event_doc) \
                .pack(anchor='w', pady=2)
        else:
            tk.Button(
                col, text="Документов нет, прикрепить…",
                bg="red", fg="white",
                command=attach_event_doc
            ).pack(anchor='w', pady=5)

        # 5) Результаты (если есть)
        ttk.Label(col, text="Результаты:", font=("", 9, "underline")).pack(anchor='w', pady=(4,0))
        if results:
            ttk.Label(col, text=results, wraplength=COL_W-10).pack(anchor='w')
        else:
            ttk.Label(col, text="—").pack(anchor='w')


def refresh_med_list():
    lst_med.delete(0, 'end')
    med_names.clear()

    # пересчитаем доступную ширину в пикселях
    list_frame.update_idletasks()
    frame_px = list_frame.winfo_width()
    pad_px = vsb_med.winfo_reqwidth() + 6
    avail_px = max(50, frame_px - pad_px)

    for aid, name in database.get_all_animals_ids():
        full = f"ID:{aid}: {name}"
        # если текст целиком помещается — используем его
        if med_font.measure(full) <= avail_px:
            display = full
        else:
            # бинарный поиск максимальной длины подстроки, влезает ли вместе с '...'
            lo, hi = 0, len(full)
            while lo < hi:
                mid = (lo + hi) // 2
                if med_font.measure(full[:mid] + '...') <= avail_px:
                    lo = mid + 1
                else:
                    hi = mid
            # lo — первая неподходящая длина, поэтому обрезаем на lo-1
            display = full[:lo-1] + '...'

        lst_med.insert('end', display)
        med_names.append(full)


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
    # 1) Обрабатываем только клики по ячейкам
    if tree.identify("region", event.x, event.y) != "cell":
        return

    # 2) Определяем, в какой колонке и строке клик
    col_id = tree.identify_column(event.x)       # "#1", "#2", ...
    col_index = int(col_id.replace("#", "")) - 1
    col_name = tree["columns"][col_index]         # имя колонки
    row_id = tree.identify_row(event.y)           # iid строки
    if not row_id:
        return
    animal_id = int(tree.item(row_id)["values"][0])

    # 3) Ветка «Med» (новая медицинская страница)
    if col_name == "Med":
        open_medical(animal_id)
        return

    # 4) Ветка «Adopt»
    if col_name == "Adopt":
        open_adopt_dialog(animal_id)
        return

    # 5) Ветка «Del»
    if col_name == "Del":
        if messagebox.askyesno("Подтверждение", f"Удалить ID {animal_id}?"):
            database.delete_animal(animal_id)
            refresh_list()
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

def on_adopted_double_click(event):
    if tree_adopted.identify("region", event.x, event.y) != "cell":
        return
    col_id = tree_adopted.identify_column(event.x)
    field = COLUMN_MAP_ADOPTED.get(col_id)
    if not field:
        return  # эту колонку не редактируем

    row_id = tree_adopted.identify_row(event.y)
    if not row_id:
        return

    # вот здесь заменили:
    adoption_id = int(row_id)

    x, y, width, height = tree_adopted.bbox(row_id, col_id)
    old_value = tree_adopted.set(row_id, col_id)
    entry = tk.Entry(tree_adopted)
    entry.place(x=x, y=y, width=width, height=height)
    entry.insert(0, old_value)
    entry.focus()

    def save_edit(e):
        new_value = entry.get().strip()
        # валидация даты передачи
        if field == "adoption_date":
            try:
                date.fromisoformat(new_value)
            except ValueError:
                messagebox.showwarning("Ошибка", "Неверный формат даты")
                entry.focus()
                return

        database.update_adoption_field(adoption_id, field, new_value)
        entry.destroy()
        refresh_adopted_list()

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
    
    # Сохраняем в базу и получаем новый ID
    new_id = database.add_animal(
    name,
    species,
    bdate.isoformat(),
    est_flag,
    arrival,
    cage,
    quarantine_until
    )

    # создаём папку для документов
    os.makedirs(f"docs/{new_id}", exist_ok=True)

    messagebox.showinfo("Готово", f"Животное добавлено с ID {new_id}")

    # Обновляем обе таблицы и список медицины
    refresh_list()
    refresh_adopted_list()

    # Маркируем его «новым»
    notified_animals.add(new_id)
    # Перерисовываем заголовок вкладки и список
    update_med_tab_title()
    refresh_med_list()

    # запускаем мигание только что добавленной строки
    full_name = f"ID:{new_id}: {name}"
    # ищем индекс в med_names
    try:
        idx = med_names.index(full_name)
        blink_list_item(idx)
    except ValueError:
        pass

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
            cage, days_left,"📋", "🤝", "🗑"
        )
        item = tree.insert(
            '',
            'end',
            values=(
                id_, name, full_species,
                bd_disp, age_disp,
                arr,
                cage, days_left,"📋",
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
root.geometry("1000x750")
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

# создаём два изображения: пустое и жёлтое кружочко
_blank_img = tk.PhotoImage(width=1, height=1)

_yellow_dot = tk.PhotoImage(width=12, height=12)
# рисуем закрашенный круг радиусом 5px
for x in range(12):
    for y in range(12):
        if (x-6)**2 + (y-6)**2 <= 6**2:
            _yellow_dot.put("#FFD700", (x, y))  # золотистый

# === Tab “Медицина” ===
tab_med = ttk.Frame(notebook)
notebook.add(tab_med, text="Медицина", image=_blank_img, compound='right')

# сетка: левая колонка фиксированной ширины, правая растягивается
tab_med.columnconfigure(0, weight=0)   # колонка списка — фиксированная
tab_med.columnconfigure(1, weight=1)   # колонка карточки — растягивается
tab_med.rowconfigure(0, weight=0)
tab_med.rowconfigure(1, weight=1)

# Заголовок над списком
ttk.Label(tab_med,
    text="Медкарта животного:"
).grid(row=0, column=0, sticky='nw', padx=5, pady=(5,0))

# Frame для списка + скроллбар
list_frame = ttk.Frame(tab_med)
list_frame.grid(row=1, column=0, sticky='nsw', padx=5, pady=5)
list_frame.rowconfigure(0, weight=1)
list_frame.columnconfigure(0, weight=1)

lst_med = tk.Listbox(list_frame, activestyle='none')
vsb_med = ttk.Scrollbar(list_frame, orient='vertical', command=lst_med.yview)
lst_med.configure(yscrollcommand=vsb_med.set)

lst_med.grid(row=0, column=0, sticky='nsew')
vsb_med.grid(row=0, column=1, sticky='ns')

# === Панель деталей (медкарта), создаётся пустой и будет переопределяться при открытии карточки ===
detail_frame = ttk.Frame(tab_med)
detail_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
detail_frame.columnconfigure(0, weight=1)

med_names = []  # будет хранить полные имена по индексам

med_font = font.nametofont(lst_med.cget("font"))
def adjust_med_list_width(event=None):
    # 1) меряем, сколько пикселей можем занять
    total = tab_med.winfo_width()
    max_px = total // 4
    min_px = med_font.measure('0') * 10
    frame_px = max(min_px, max_px)

    # 2) сразу выставляем ширину фрейма и списка
    list_frame.config(width=frame_px)

    # 3) перерисовываем сам список с новыми ограничениями
    refresh_med_list()


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
frm_quarantine = ttk.LabelFrame(tab_shelter, text="Карантин")
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
    "Клетка", "Осталось дней карантина","Med",
    "Adopt", "Del"
)

table_frame = ttk.Frame(tab_shelter)
table_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)
table_frame.columnconfigure(0, weight=1)
table_frame.rowconfigure(0, weight=1)

tree = ttk.Treeview(table_frame, columns=columns, show='headings')
for col in columns:
    tree.heading(col, text=col if col not in ("Med","Adopt", "Del") else "")
# настраиваем ширины
tree.column("ID", width=30, anchor='center')
tree.column("Имя", width=100, anchor='w')
tree.column("Вид", width=150, anchor='w')
tree.column("Дата рождения", width=100, anchor='center')
tree.column("Возраст (мес.)", width=90, anchor='center')
tree.column("Дата поступления", width=100, anchor='center')
tree.column("Клетка", width=70, anchor='center')
tree.column("Осталось дней карантина", width=150, anchor='center')
tree.column("Med", width=20, anchor='center')
tree.column("Adopt", width=20, anchor='center')
tree.column("Del", width=20, anchor='center')

vsb = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=vsb.set)
tree.grid(row=0, column=0, sticky='nsew')
vsb.grid(row=0, column=1, sticky='ns')

# === Tab “Переданы” ===
tab_adopted.columnconfigure(0, weight=1)
tab_adopted.rowconfigure(1, weight=1)
tab_adopted.grid_propagate(False)
tab_adopted.rowconfigure(1, weight=1)
tab_adopted.columnconfigure(0, weight=1)

ttk.Label(tab_adopted, text="Переданные животные", font=("", 14)).grid(row=0, column=0, pady=5)

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

# сопоставляем col_id → имя поля в adoptions
COLUMN_MAP_ADOPTED = {
    "#1": None,               # "ID животного" — не редактируем
    "#2": None,               # "Имя" — snapshot, можно не править
    "#3": None,               # "Вид" — snapshot, не правим
    "#4": None,               # "Дата рождения" — snapshot
    "#5": None,               # "Возраст (мес.)" — snapshot
    "#6": None,               # "Дата поступления" — snapshot
    "#7": "owner_name",       # редактируем имя владельца
    "#8": "owner_contact",    # редактируем контакт
    "#9": "adoption_date",    # редактируем дату передачи
}

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

    for rec in database.get_all_adoptions():
        # rec = (id, animal_id, name,...,owner,contact,ad_date)
        (adopt_id, animal_id, name, species, bd, est_flag,
         arr, owner, contact, ad_date) = rec

        bdate = date.fromisoformat(bd)
        months = (today.year*12 + today.month) - (bdate.year*12 + bdate.month)
        age_disp = f"~{months}" if est_flag else str(months)
        bd_disp  = f"~{bd}" if est_flag else bd
        arr_disp = arr or ""
        values = (
            animal_id, name, species,
            bd_disp, age_disp, arr_disp,
            owner, contact, ad_date
        )
        # сохраняем adopt_id в tags, чтобы потом знать, какую запись править
        tree_adopted.insert(
            '', 'end',
            iid=str(adopt_id),   # или tags=[str(adopt_id)]
            values=values
        )
    autofit_columns(tree_adopted, columns_adopted)


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
tree_adopted.bind("<Double-1>", on_adopted_double_click)
lst_med.bind("<Motion>", on_motion)
lst_med.bind("<Leave>", on_leave)
lst_med.bind("<<ListboxSelect>>", on_med_select)
list_frame.bind('<Configure>', adjust_med_list_width)

# словарь для хранения ID таймеров мигания
blink_timers = {}

# Запуск
database.init_db()          # Сначала создаём/мигрируем все таблицы
refresh_list()              # Затем наполняем главную таблицу приюта
refresh_adopted_list()      # Потом таблицу «Переданы»
refresh_med_list()          # И, наконец, список для «Медицина»
root.mainloop()

