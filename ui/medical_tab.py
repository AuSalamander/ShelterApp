"""
Вкладка "Медицина" - медицинские карточки животных
"""
import tkinter as tk
from tkinter import ttk, font, messagebox, filedialog
import os
import glob
import json
from models import AnimalManager, EventManager
from utils import truncate_text_for_width
from ui.dialogs import EventDialog
import database
from config import config


class MedicalTab:
    """Вкладка медицины с карточками животных"""
    
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.notified_animals = set()
        self.blink_timer = None
        self.blink_state = False
        self.blink_index = None
        self.med_names = []
        self.tip = None
        self.update_lock = False
        
        self.setup_ui()
        self.setup_bindings()
        self.create_notification_images()
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Настройка сетки
        self.frame.columnconfigure(0, weight=0)  # список фиксированной ширины
        self.frame.columnconfigure(1, weight=1)  # карточка растягивается
        self.frame.rowconfigure(0, weight=0)
        self.frame.rowconfigure(1, weight=1)
        
        # Заголовок
        ttk.Label(self.frame, text="Медкарта животного:").grid(
            row=0, column=0, sticky='nw', padx=5, pady=(5,0)
        )
        
        # Фрейм для списка
        self.list_frame = ttk.Frame(self.frame)
        self.list_frame.grid(row=1, column=0, sticky='nsw', padx=5, pady=5)
        self.list_frame.rowconfigure(0, weight=1)
        self.list_frame.columnconfigure(0, weight=1)
        
        # Список животных
        self.lst_med = tk.Listbox(self.list_frame, activestyle='none')
        self.vsb_med = ttk.Scrollbar(self.list_frame, orient='vertical', command=self.lst_med.yview)
        self.lst_med.configure(yscrollcommand=self.vsb_med.set)
        
        self.lst_med.grid(row=0, column=0, sticky='nsew')
        self.vsb_med.grid(row=0, column=1, sticky='ns')
        
        # Панель деталей
        self.detail_frame = ttk.Frame(self.frame)
        self.detail_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        self.detail_frame.columnconfigure(0, weight=1)
        
        # Получаем шрифт для расчетов
        self.med_font = font.nametofont(self.lst_med.cget("font"))
    
    def setup_bindings(self):
        """Настройка обработчиков событий"""
        self.lst_med.bind("<<ListboxSelect>>", self.on_med_select)
        self.lst_med.bind("<Motion>", self.on_motion)
        self.lst_med.bind("<Leave>", self.on_leave)
        self.list_frame.bind('<Configure>', self.adjust_list_width)
    
    def create_notification_images(self):
        """Создание изображений для уведомлений"""
        self.blank_img = tk.PhotoImage(width=1, height=1)
        
        self.yellow_dot = tk.PhotoImage(width=12, height=12)
        # Рисуем желтый круг
        for x in range(12):
            for y in range(12):
                if (x-6)**2 + (y-6)**2 <= 6**2:
                    self.yellow_dot.put("#FFD700", (x, y))
    
    def refresh_list(self):
        """Обновление списка животных"""
        self.lst_med.delete(0, 'end')
        self.med_names.clear()
        
        # Пересчитываем доступную ширину
        self.list_frame.update_idletasks()
        frame_px = self.list_frame.winfo_width()
        pad_px = self.vsb_med.winfo_reqwidth() + 6
        avail_px = max(50, frame_px - pad_px)
        
        # Загружаем животных
        for aid, name in database.get_all_animals_ids():
            full = f"ID:{aid}: {name}"
            # если текст целиком помещается — используем его
            if self.med_font.measure(full) <= avail_px:
                display = full
            else:
                # бинарный поиск максимальной длины подстроки, влезает ли вместе с '...'
                lo, hi = 0, len(full)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if self.med_font.measure(full[:mid] + '...') <= avail_px:
                        lo = mid + 1
                    else:
                        hi = mid
                # lo — первая неподходящая длина, поэтому обрезаем на lo-1
                display = full[:lo-1] + '...'
            
            self.lst_med.insert('end', display)
            self.med_names.append(full)
    
    def adjust_list_width(self, event=None):
        """Автоматическая подгонка ширины списка"""
        total = self.frame.winfo_width()
        max_px = total // 4
        min_px = self.med_font.measure('0') * 10
        frame_px = max(min_px, max_px)
        
        self.list_frame.config(width=frame_px)
        self.refresh_list()
    
    def on_med_select(self, event):
        """Обработчик выбора животного из списка"""
        sel = self.lst_med.curselection()
        if not sel:
            return
        
        text = self.lst_med.get(sel[0])
        # Ожидаем формат "ID:<число>: <имя>"
        parts = text.split(":", 2)
        if len(parts) < 3:
            return
        
        id_part = parts[1].strip()
        if not id_part.isdigit():
            return
        
        aid = int(id_part)
        self.open_medical_card(aid)
    
    def open_medical_card(self, animal_id):
        """Открытие медицинской карточки животного"""
        # Переключаемся на вкладку медицины
        if hasattr(self.parent, 'select'):
            self.parent.select(self.frame)
        
        # Убираем уведомление
        if animal_id in self.notified_animals:
            self.notified_animals.remove(animal_id)
            self.update_tab_title()
            self.stop_blink()
        
        # Очищаем панель деталей
        for w in self.detail_frame.winfo_children():
            w.destroy()
        
        # Получаем данные животного
        animal_data = database.get_animal_by_id(animal_id)
        if not animal_data:
            return
        
        name = animal_data[1]
        
        # Создаем заголовок
        label_text = f"Медкарта животного #{animal_id} ({name})"
        
        style = ttk.Style()
        style.configure("Wrap.TLabel", justify="left")
        
        header_label = ttk.Label(
            self.detail_frame,
            text=label_text,
            font=("", 14),
            style="Wrap.TLabel",
            anchor="w",
            wraplength=400
        )
        header_label.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 5))
        
        # Функция для обновления переноса
        def update_wrap(event):
            new_width = self.detail_frame.winfo_width() - 20
            header_label.configure(wraplength=max(100, new_width))

        header_label.update_idletasks()
        update_wrap(None)
        self.detail_frame.bind("<Configure>", update_wrap)
        
        # Создаем скроллируемую область
        canvas = tk.Canvas(self.detail_frame, borderwidth=0)
        vsb = ttk.Scrollbar(self.detail_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig('all', width=e.width)

        scroll_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("all", width=e.width))
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", tags="all")
        canvas.configure(yscrollcommand=vsb.set)
        
        # Размещение элементов
        self.detail_frame.rowconfigure(1, weight=1)
        self.detail_frame.columnconfigure(0, weight=1)
        canvas.columnconfigure(0, weight=1)
        scroll_frame.columnconfigure(0, weight=1)
        
        canvas.grid(row=1, column=0, sticky='nsew')
        vsb.grid(row=1, column=1, sticky='ns')
        
        # Заполняем содержимое
        self.create_medical_content(scroll_frame, animal_id)
    
    def create_medical_content(self, parent, animal_id):
        """Создание содержимого медицинской карточки"""
        # === Документы ===
        docs = sorted(glob.glob(f"docs/{animal_id}/*"), key=os.path.getctime)
        docs_frame = ttk.LabelFrame(parent, text="Документы")
        docs_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5), padx=2)
        docs_frame.columnconfigure(0, weight=1)

        def update_doc_buttons(event=None):
            if self.update_lock:
                return
            
            try:
                self.update_lock = True
                frame_width = docs_frame.winfo_width()
                
                # Удаляем старые виджеты
                for w in docs_frame.winfo_children():
                    w.destroy()
                
                if not docs:
                    def open_docs_folder():
                        folder_path = os.path.abspath(os.path.join("docs", str(animal_id)))
                        os.makedirs(folder_path, exist_ok=True)
                        if os.name == 'nt':
                            os.startfile(folder_path)
                        else:
                            os.system(f'open "{folder_path}"' if os.sys.platform == 'darwin' else f'xdg-open "{folder_path}"')

                    btn = tk.Button(
                        docs_frame,
                        text="Документов нет, нажмите чтобы добавить",
                        bg="red", 
                        fg="white",
                        command=open_docs_folder
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
                self.update_lock = False

        # Первый вызов
        update_doc_buttons()

        # Оптимизированная привязка с троттлингом
        def delayed_update(event):
            docs_frame.after(5, update_doc_buttons)

        docs_frame.bind("<Configure>", delayed_update)

        # === Блок «События» ===
        # Кнопка добавления события
        btn_new_event = ttk.Button(
            parent,
            text="Добавить событие",
            command=lambda: self.open_event_dialog(animal_id)
        )
        btn_new_event.grid(row=3, column=0, sticky='w', pady=(0,10))
        events = database.get_animal_events(animal_id)

        # Заголовок блока
        ttk.Label(parent, text="События", font=("", 12)).grid(
            row=2, column=0, sticky='w', pady=(10, 5)
        )

        if not events:
            ttk.Label(parent, text="Событий пока нет").grid(row=4, column=0, sticky='w', pady=10)
        else:
            events_canvas = tk.Canvas(parent, height=1000, borderwidth=0, highlightthickness=0)
            hsb = ttk.Scrollbar(parent, orient="horizontal", command=events_canvas.xview)
            events_frame = ttk.Frame(events_canvas)

            events_frame.bind(
            "<Configure>",
            lambda e: events_canvas.configure(scrollregion=events_canvas.bbox("all"))
            )
            events_frame_id = events_canvas.create_window((0, 0), window=events_frame, anchor="nw")
            events_canvas.configure(xscrollcommand=hsb.set)

            hsb.grid(row=4, column=0, sticky='ew', pady=(0,2))
            events_canvas.grid(row=5, column=0, sticky='ew')

            COL_W = 400
            PAD_X = 5

            # Наполняем события горизонтально
            for idx, (etype, ds, de, concl, ew_doc_list, results, eid) in enumerate(events):
                col = ttk.Frame(events_frame, width=COL_W, relief='groove', padding=5)
                col.grid(row=0, column=idx, padx=( PAD_X, 0), sticky='ns')

                # === row 0: Тип события ===
                row_type = 0
                lbl_type = ttk.Label(col, text=etype, font=("", 10, "bold"))
                lbl_type.grid(row=row_type, column=0, sticky='w', pady=(0,4))

                # Фабрика колбэка для редактирования типа
                def make_type_editor(frame=col, r=row_type, original=etype, ev_id=eid):
                    def on_edit_type(event):
                        frame.grid_propagate(False)
                        lbl_type.grid_forget()
                        ent = ttk.Entry(frame, font=("", 10, "bold"))
                        ent.insert(0, original)
                        ent.grid(row=r, column=0, sticky='w', pady=(0,4))
                        ent.focus()
                        def save(e=None):
                            new = ent.get().strip()
                            if not new:
                                messagebox.showwarning("Ошибка", "Название не может быть пустым")
                                ent.focus()
                                return
                            database.update_event_field(ev_id, 'type', new)
                            self.open_medical_card(animal_id)
                        ent.bind('<Return>', save)
                        ent.bind('<FocusOut>', save)
                    return on_edit_type

                lbl_type.bind('<Double-1>', make_type_editor())

                # === row 1: Даты ===
                row_dates = 1
                date_text = ds if not de or ds == de else f"{ds} — {de}"
                lbl_dates = ttk.Label(col, text=date_text)
                lbl_dates.grid(row=row_dates, column=0, sticky='w', pady=(0,4))

                def make_dates_editor(frame=col, r=row_dates, orig_ds=ds, orig_de=de, ev_id=eid):
                    def on_edit_dates(event):
                        frame.grid_propagate(False)
                        lbl_dates.grid_forget()
                        frm = ttk.Frame(frame)
                        frm.grid(row=r, column=0, sticky='w', pady=(0,4))
                        ent_start = ttk.Entry(frm, width=10)
                        ent_start.insert(0, orig_ds)
                        ent_end = ttk.Entry(frm, width=10)
                        ent_end.insert(0, orig_de or orig_ds)
                        ent_start.grid(row=0, column=0, padx=(0,5))
                        ent_end.grid(row=0, column=1)
                        ent_start.focus()
                        
                        def save(e=None):
                            new_start = ent_start.get().strip()
                            new_end = ent_end.get().strip() or None
                            
                            if not new_start:
                                messagebox.showwarning("Ошибка", "Дата начала обязательна")
                                ent_start.focus()
                                return
                            
                            try:
                                from datetime import date
                                date.fromisoformat(new_start)
                                if new_end:
                                    date.fromisoformat(new_end)
                            except ValueError:
                                messagebox.showwarning("Ошибка", "Неверный формат даты (YYYY-MM-DD)")
                                return
                            
                            database.update_event_field(ev_id, 'date_start', new_start)
                            database.update_event_field(ev_id, 'date_end', new_end)
                            self.open_medical_card(animal_id)
                        
                        ent_start.bind('<Return>', save)
                        ent_end.bind('<Return>', save)
                    return on_edit_dates

                lbl_dates.bind('<Double-1>', make_dates_editor())

                # === row 2: Примечание ===
                row_concl = 2
                concl_text = concl or "(нет примечания)"
                lbl_concl = ttk.Label(col, text=concl_text, wraplength=COL_W-20)
                lbl_concl.grid(row=row_concl, column=0, sticky='w', pady=(0,4))

                def make_concl_editor(frame=col, r=row_concl, original=concl, ev_id=eid):
                    def on_edit_concl(event):
                        frame.grid_propagate(False)
                        lbl_concl.grid_forget()
                        txt = tk.Text(frame, height=3, width=40)
                        txt.insert('1.0', original or "")
                        txt.grid(row=r, column=0, sticky='w', pady=(0,4))
                        txt.focus()
                        
                        def save(e=None):
                            new_concl = txt.get('1.0', 'end').strip() or None
                            database.update_event_field(ev_id, 'conclusion', new_concl)
                            self.open_medical_card(animal_id)
                        def on_return(event):
                            if event.state & 0x0001:
                                return
                            save()
                            return "break"
                        txt.bind("<Return>", on_return)
                        txt.bind('<FocusOut>', save)
                    return on_edit_concl

                lbl_concl.bind('<Double-1>', make_concl_editor())

                # === row 3: Документы события ===
                ew_docs = database.get_event_docs(eid)
                ew_docs_frame = ttk.LabelFrame(col, text="Документы")
                ew_docs_frame.grid(row=3, column=0, sticky='ew', pady=(0,4), padx=2)
                ew_docs_frame.columnconfigure(0, weight=1)

                # узнаём доступную ширину
                ew_docs_frame.update_idletasks()
                max_px = ew_docs_frame.winfo_width() or COL_W
                pad = 6

                row = 0
                col_idx = 0
                used_px = 0

                if ew_docs:
                    for fn in ew_docs:
                        # создаём временную кнопку, чтобы измерить ширину
                        tmp = ttk.Button(ew_docs_frame, text=fn)
                        tmp.update_idletasks()
                        bw = tmp.winfo_reqwidth() + pad
                        tmp.destroy()

                        # перенос, если не влезает
                        if used_px + bw > max_px and col_idx > 0:
                            row += 1
                            col_idx = 0
                            used_px = 0

                        # контейнер для пары кнопок
                        sub = ttk.Frame(ew_docs_frame)
                        sub.grid(row=row, column=col_idx, sticky='w', padx=2, pady=2)

                        # кнопка «Открыть»
                        btn_open = ttk.Button(
                            sub, text=fn,
                            command=lambda animal_id=animal_id, fn=fn: os.startfile(f"docs/{animal_id}/{fn}")
                        )
                        btn_open.grid(row=0, column=0, sticky='w')

                        # кнопка «×» (удалить ссылку)
                        btn_del = ttk.Button(
                            sub, text="×", width=2,
                            command=lambda ev_id=eid, fn=fn: (
                                database.delete_event_doc(ev_id, fn),
                                self.open_medical_card(animal_id)
                            )
                        )
                        btn_del.grid(row=0, column=1, sticky='w', padx=(4,0))

                        used_px += bw
                        col_idx += 1

                    # кнопка «Прикрепить ещё» сразу под последним рядом
                    ttk.Button(
                        ew_docs_frame,
                        text="Прикрепить документ…",
                        command=lambda eid=eid: self.attach_event_doc_dialog(eid, animal_id)
                    ).grid(row=row+1, column=0, sticky='w', pady=(4,0), padx=2)

                else:
                    # если нет файлов
                    tk.Button(
                        ew_docs_frame,
                        text="Документов нет, прикрепить…",
                        bg="red", fg="white",
                        command=lambda eid=eid: self.attach_event_doc_dialog(eid, animal_id)
                    ).grid(row=0, column=0, sticky='w', pady=(2,4), padx=2)

                # === row 4: Значения ===
                specs = config.get_event_fields(etype)
                frm_res = ttk.LabelFrame(col, text="Результаты")
                frm_res.grid(row=6, column=0, sticky='ew', pady=(4,0))
                frm_res.columnconfigure(0, weight=1)

                try:
                    master_data = json.loads(results) if results else {}
                except:
                    master_data = {}

                for i, (fname, ftype) in enumerate(specs):
                    val = master_data.get(fname, "")

                    lbl = ttk.Label(frm_res, text=f"{fname}: {val}", anchor='w')
                    lbl.grid(row=i, column=0, sticky='ew', padx=2, pady=1)

                    def make_res_editor(frame=frm_res, row=i, field=fname,
                                        orig_data=master_data, ev_id=eid, ftype=ftype):
                        data = orig_data.copy()
                        def on_edit(event):
                            frame.grid_propagate(False)
                            lbl.grid_forget()
                            ent = ttk.Entry(frame)
                            ent.insert(0, str(data.get(field, "")))
                            ent.grid(row=row, column=0, sticky='ew', padx=2, pady=1)
                            ent.focus()
                            def save(e=None):
                                new = ent.get().strip()
                                try:
                                    if ftype == 'int':
                                        cast = int(new)
                                    elif ftype in ('float', 'double'):
                                        cast = float(new)
                                    else:
                                        cast = new
                                except:
                                    messagebox.showwarning("Ошибка", f"Неверный формат для {field}")
                                    ent.focus()
                                    return
                                data[field] = cast
                                # сохраняем JSON полностью обновлённым
                                database.update_event_results(ev_id, json.dumps(data))
                                self.open_medical_card(animal_id)
                            ent.bind('<Return>', save)
                            ent.bind('<FocusOut>', save)
                        return on_edit

                    lbl.bind('<Double-1>', make_res_editor())
                

    def attach_event_doc_dialog(self, event_id, animal_id):
        """Диалог прикрепления документов к событию"""
        
        folder = os.path.abspath(f"docs/{animal_id}")
        os.makedirs(folder, exist_ok=True)
        
        files = filedialog.askopenfilenames(
            title="Выберите файлы для прикрепления к событию",
            initialdir=folder
        )
        
        for file_path in files:
            filename = os.path.basename(file_path)
            database.add_event_doc(event_id, filename)
        
        if files:
            self.open_medical_card(animal_id)
    
    def open_event_dialog(self, animal_id):
        """Открытие диалога создания события"""
        dialog = EventDialog(self.frame, animal_id)
        if dialog.result:
            self.open_medical_card(animal_id)  # Обновляем карточку
    
    def notify_new_animal(self, animal_id):
        """Уведомление о новом животном"""
        self.notified_animals.add(animal_id)
        self.update_tab_title()
        self.refresh_list()
        
        # Запускаем мигание
        full_name = f"ID:{animal_id}"
        for idx, name in enumerate(self.med_names):
            if name.startswith(full_name):
                self.blink_list_item(idx)
                break
    
    def update_tab_title(self):
        """Обновление заголовка вкладки"""
        if hasattr(self.parent, 'tab'):
            if self.notified_animals:
                self.parent.tab(self.frame, text="Медицина", 
                              image=self.yellow_dot, compound='right')
            else:
                self.parent.tab(self.frame, text="Медицина", 
                              image=self.blank_img, compound='right')
    
    def blink_list_item(self, index):
        """Мигание элемента списка"""
        if self.blink_timer is not None:
            self.frame.after_cancel(self.blink_timer)
            if self.blink_index is not None:
                self.lst_med.itemconfig(self.blink_index, bg='')
        
        self.blink_index = index
        self.blink_state = False
        
        def _blink():
            color = 'yellow' if self.blink_state else ''
            self.lst_med.itemconfig(self.blink_index, bg=color)
            self.blink_state = not self.blink_state
            self.blink_timer = self.frame.after(250, _blink)
        
        _blink()
    
    def stop_blink(self):
        """Остановка мигания"""
        if self.blink_timer is not None:
            self.frame.after_cancel(self.blink_timer)
            self.blink_timer = None
        if self.blink_index is not None:
            self.lst_med.itemconfig(self.blink_index, bg='')
            self.blink_index = None
    
    def on_motion(self, event):
        """Обработчик движения мыши для тултипа"""
        idx = self.lst_med.nearest(event.y)
        bbox = self.lst_med.bbox(idx)
        
        if not bbox or idx >= len(self.med_names):
            if self.tip:
                self.tip.destroy()
                self.tip = None
            return
        
        x0, y0, w0, h0 = bbox
        if event.y < y0 or event.y > y0 + h0:
            if self.tip:
                self.tip.destroy()
                self.tip = None
            return
        
        # Показываем тултип
        full = self.med_names[idx]
        if self.tip:
            self.tip.destroy()
        
        self.tip = tk.Toplevel(self.lst_med)
        self.tip.wm_overrideredirect(True)
        abs_x = self.lst_med.winfo_rootx() + w0 + 2
        abs_y = self.lst_med.winfo_rooty() + y0
        self.tip.geometry(f"+{abs_x}+{abs_y}")
        tk.Label(self.tip, text=full, background="lightyellow").pack()
    
    def on_leave(self, event):
        """Обработчик ухода мыши"""
        if self.tip:
            self.tip.destroy()
            self.tip = None
