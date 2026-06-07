import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from database import Database
from inference_engine import InferenceEngine
from fact_highlighter import FactHighlighter
from tkinter import filedialog
from datetime import datetime
import json
import math

class LabComplexApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторный комплекс: Продукционные базы знаний")
        self.root.geometry("900x700")

        self.db = Database()
        self.db.create_subject_area_table()  # Создаем таблицу областей

        self.engine = InferenceEngine(self.db)
        self.last_inferred_facts = {}

        # Инициализируем переменные до создания интерфейса
        self.editing_rule_id = None
        self.editing_rule_name = None
        self.current_area_id = 1
        self.subject_areas = []
        self.subject_area_combo = None

        self.create_menu()
        self.create_tabs()

        self.load_subject_areas()
        self.refresh_rules_list()
        self.setup_all_highlighters()

    def enable_copy_paste(self, widget):
        """Включает копирование/вставку для текстовых полей"""

        def copy(event=None):
            try:
                widget.event_generate("<<Copy>>")
            except:
                pass
            return "break"

        def paste(event=None):
            try:
                widget.event_generate("<<Paste>>")
            except:
                pass
            return "break"

        def cut(event=None):
            try:
                widget.event_generate("<<Cut>>")
            except:
                pass
            return "break"

        def select_all(event=None):
            widget.tag_add("sel", "1.0", "end")
            return "break"

        widget.bind("<Control-c>", copy)
        widget.bind("<Control-C>", copy)
        widget.bind("<Control-v>", paste)
        widget.bind("<Control-V>", paste)
        widget.bind("<Control-x>", cut)
        widget.bind("<Control-X>", cut)
        widget.bind("<Control-a>", select_all)
        widget.bind("<Control-A>", select_all)

        self.create_context_menu(widget)

    def create_context_menu(self, widget):
        """Создает контекстное меню для виджета"""
        menu = tk.Menu(widget, tearoff=0)

        def show_menu(event):
            menu.delete(0, tk.END)
            menu.add_command(label="Копировать",
                             command=lambda: widget.event_generate("<<Copy>>"),
                             accelerator="Ctrl+C")
            menu.add_command(label="Вставить",
                             command=lambda: widget.event_generate("<<Paste>>"),
                             accelerator="Ctrl+V")
            menu.add_command(label="Вырезать",
                             command=lambda: widget.event_generate("<<Cut>>"),
                             accelerator="Ctrl+X")
            menu.add_separator()
            menu.add_command(label="Выделить всё",
                             command=lambda: self.select_all_text(widget),
                             accelerator="Ctrl+A")
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Button-2>", show_menu)

    def select_all_text(self, widget):
        """Выделяет весь текст в виджете"""
        try:
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                widget.tag_add("sel", "1.0", "end")
            elif isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
        except:
            pass

    def enable_entry_copy_paste(self, entry):
        """Включает копирование/вставку для полей ввода Entry"""

        def copy(event=None):
            try:
                entry.event_generate("<<Copy>>")
            except:
                pass
            return "break"

        def paste(event=None):
            try:
                entry.event_generate("<<Paste>>")
            except:
                pass
            return "break"

        def cut(event=None):
            try:
                entry.event_generate("<<Cut>>")
            except:
                pass
            return "break"

        def select_all(event=None):
            entry.select_range(0, tk.END)
            entry.icursor(tk.END)
            return "break"

        entry.bind("<Control-c>", copy)
        entry.bind("<Control-C>", copy)
        entry.bind("<Control-v>", paste)
        entry.bind("<Control-V>", paste)
        entry.bind("<Control-x>", cut)
        entry.bind("<Control-X>", cut)
        entry.bind("<Control-a>", select_all)
        entry.bind("<Control-A>", select_all)

        menu = tk.Menu(entry, tearoff=0)

        def show_menu(event):
            menu.delete(0, tk.END)
            menu.add_command(label="Копировать",
                             command=lambda: entry.event_generate("<<Copy>>"),
                             accelerator="Ctrl+C")
            menu.add_command(label="Вставить",
                             command=lambda: entry.event_generate("<<Paste>>"),
                             accelerator="Ctrl+V")
            menu.add_command(label="Вырезать",
                             command=lambda: entry.event_generate("<<Cut>>"),
                             accelerator="Ctrl+X")
            menu.add_separator()
            menu.add_command(label="Выделить всё",
                             command=lambda: self.select_all_entry(entry),
                             accelerator="Ctrl+A")
            menu.tk_popup(event.x_root, event.y_root)

        entry.bind("<Button-3>", show_menu)
        entry.bind("<Button-2>", show_menu)

    def select_all_entry(self, entry):
        """Выделяет весь текст в Entry"""
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)

    def create_menu(self):
        """Создание верхнего меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Очистить базу", command=self.clear_database)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

    def create_tabs(self):
        """Создание вкладок интерфейса"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_rules = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_rules, text="Редактор правил")
        self.create_rules_tab()

        self.tab_inference = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_inference, text="Прямой вывод")
        self.create_inference_tab()

        self.tab_explain = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_explain, text="Обратный вывод")
        self.create_explain_tab()

    def create_rules_tab(self):
        """Вкладка для создания и просмотра правил"""

        # ВЕРХНЯЯ ЧАСТЬ
        top_area_frame = ttk.LabelFrame(self.tab_rules, text="Управление предметными областями", padding=5)
        top_area_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_area_frame, text="Текущая область:").pack(side=tk.LEFT, padx=5)
        self.subject_area_combo = ttk.Combobox(top_area_frame, width=30, state="readonly")
        self.subject_area_combo.pack(side=tk.LEFT, padx=5)
        self.subject_area_combo.bind('<<ComboboxSelected>>', self.on_subject_area_change)

        ttk.Button(top_area_frame, text="Новая область", command=self.add_subject_area_dialog).pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Button(top_area_frame, text="Удалить область", command=self.delete_subject_area_dialog).pack(side=tk.LEFT,
                                                                                                         padx=5)
        ttk.Button(top_area_frame, text="Просмотр БД", command=self.view_database_structure).pack(side=tk.LEFT, padx=5)

        # ОСНОВНАЯ ЧАСТЬ левая и правая
        left_frame = ttk.LabelFrame(self.tab_rules, text="Добавить/Изменить правило", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(left_frame, text="Название правила:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rule_name = ttk.Entry(left_frame, width=30)
        self.rule_name.grid(row=0, column=1, pady=5, padx=5)
        self.enable_entry_copy_paste(self.rule_name)

        ttk.Label(left_frame, text="Условие (IF):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(left_frame, text='Формат: "факт = значение" или "факт >= значение" (для И используйте " И ")',
                  font=("Arial", 8), foreground="gray").grid(row=2, column=0, columnspan=2, sticky=tk.W)

        self.condition_text = scrolledtext.ScrolledText(left_frame, width=40, height=6)
        self.condition_text.grid(row=3, column=0, columnspan=2, pady=5)
        self.enable_copy_paste(self.condition_text)

        ttk.Label(left_frame, text="Заключение:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Label(left_frame, text='Формат: "факт = значение" (для ИНАЧЕ используйте " ИНАЧЕ ")',
                  font=("Arial", 8), foreground="gray").grid(row=5, column=0, columnspan=2, sticky=tk.W)

        self.conclusion_text = scrolledtext.ScrolledText(left_frame, width=40, height=6)
        self.conclusion_text.grid(row=6, column=0, columnspan=2, pady=5)
        self.enable_copy_paste(self.conclusion_text)

        ttk.Label(left_frame, text="Приоритет (1-10):").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.priority = ttk.Spinbox(left_frame, from_=1, to=10, width=10)
        self.priority.set(5)
        self.priority.grid(row=7, column=1, sticky=tk.W, pady=5)

        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Сохранить", command=self.save_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_rule_form).pack(side=tk.LEFT, padx=5)

        # Правая часть - список существующих правил
        right_frame = ttk.LabelFrame(self.tab_rules, text="Существующие правила", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.rules_listbox = tk.Listbox(right_frame, height=5, width=25)
        self.rules_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.rules_listbox.bind('<<ListboxSelect>>', self.on_rule_select)

        ttk.Label(right_frame, text="Содержимое выбранного правила:", font=("Arial", 9, "bold")).pack(anchor=tk.W,
                                                                                                      pady=(10, 5))

        self.rule_view_text = scrolledtext.ScrolledText(right_frame, height=10, width=40, state=tk.DISABLED)
        self.rule_view_text.pack(fill=tk.BOTH, expand=True, pady=5)

        self.list_buttons_frame = ttk.Frame(right_frame)
        self.list_buttons_frame.pack(fill=tk.X, pady=5)
        ttk.Button(self.list_buttons_frame, text="Изменить", command=self.edit_selected_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.list_buttons_frame, text="Удалить", command=self.delete_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.list_buttons_frame, text="Удалить все", command=self.delete_all_rules_dialog).pack(side=tk.LEFT,
                                                                                                           padx=5)
        ttk.Button(self.list_buttons_frame, text="Все правила", command=self.view_all_rules).pack(side=tk.LEFT, padx=5)

    def save_rule(self):
        """Сохранить правило (с поддержкой ELSE)"""
        try:
            # Нормализуем операторы перед сохранением
            FactHighlighter.normalize_operators(self.condition_text)
            FactHighlighter.normalize_operators(self.conclusion_text)

            name = self.rule_name.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Введите название правила")
                return

            condition_text = self.condition_text.get("1.0", tk.END).strip()
            conclusion_text = self.conclusion_text.get("1.0", tk.END).strip()

            # Разбор условия
            try:
                condition = self.parse_input_to_json(condition_text, "условия")
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Ошибка в условии:\n{e}")
                return

            # Разбор заключения с поддержкой ИНАЧЕ
            conclusion = {}
            else_conclusion = None

            if " ИНАЧЕ " in conclusion_text.upper():
                parts = conclusion_text.split(" ИНАЧЕ ", 1)
                then_part = parts[0].strip()
                else_part = parts[1].strip()
                try:
                    conclusion = self.parse_input_to_json(then_part, "заключения THEN")
                    else_conclusion = self.parse_input_to_json(else_part, "заключения ELSE")
                except ValueError as e:
                    messagebox.showerror("Ошибка", f"Ошибка в заключении:\n{e}")
                    return
            else:
                try:
                    conclusion = self.parse_input_to_json(conclusion_text, "заключения")
                except ValueError as e:
                    messagebox.showerror("Ошибка", f"Ошибка в заключении:\n{e}")
                    return

            priority = int(self.priority.get())
            subject_area_id = self.current_area_id
            current_area_name = self.subject_area_combo.get()

            # Проверка существования правила
            exists = self.db.rule_name_exists_in_area(name, subject_area_id, self.editing_rule_id)

            if exists:
                messagebox.showerror("Ошибка",
                                     f"Правило с названием '{name}' уже существует в области '{current_area_name}'")
                return

            if self.editing_rule_id is not None:
                # Режим редактирования
                self.db.update_rule_with_area(
                    self.editing_rule_id, name, condition, conclusion,
                    priority, subject_area_id, "", else_conclusion
                )
                messagebox.showinfo("Успех", f"Правило '{name}' обновлено в области '{current_area_name}'")
                self.editing_rule_id = None
                self.editing_rule_name = None
            else:
                # Режим создания нового правила
                self.db.add_rule_with_area(
                    name, condition, conclusion, priority, subject_area_id, "", else_conclusion
                )
                messagebox.showinfo("Успех", f"Правило '{name}' добавлено в область '{current_area_name}'")

            # Очищаем форму и обновляем список
            self.clear_rule_form()
            self.refresh_rules_list()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить правило: {e}")
            import traceback
            traceback.print_exc()

    def parse_input_to_json(self, text, field_name):
        """Парсер для ввода данных с поддержкой операторов И и ИЛИ"""
        text = text.strip()
        if not text:
            return {}

        # Сначала пробуем как JSON
        try:
            return json.loads(text)
        except:
            pass

        # Проверяем наличие ИЛИ на верхнем уровне
        if " ИЛИ " in text:
            alternatives = text.split(" ИЛИ ")
            or_conditions = []
            for alt in alternatives:
                alt = alt.strip()
                if alt:
                    # Для каждой альтернативы парсим как И-условие
                    or_conditions.append(self.parse_and_condition(alt))
            return {"__or__": or_conditions}
        else:
            return self.parse_and_condition(text)

    def parse_and_condition(self, text):
        """Разбор условия с операторами И"""
        result = {}
        # Разделяем по " И "
        parts = text.split(" И ")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Поиск оператора (важен порядок)
            operators = [">=", "<=", "!=", "=", ">", "<"]
            found_operator = None
            operator_pos = -1

            for op in operators:
                if op in part:
                    # Для "=" нужно убедиться, что это не часть ">=" или "<="
                    if op == "=" and (">=" in part or "<=" in part):
                        continue
                    found_operator = op
                    operator_pos = part.find(op)
                    break

            if found_operator is None:
                raise ValueError(f"Не найден оператор в условии: {part}")

            left = part[:operator_pos].strip()
            right = part[operator_pos + len(found_operator):].strip()

            if not left or not right:
                raise ValueError(f"Некорректный формат: {part}")

            value = self.parse_value(right)

            if found_operator == "=":
                result[left] = value
            else:
                result[left] = {found_operator: value}

        return result

    def parse_simple_rule_format(self, text):
        """Преобразование фактов с поддержкой И и ИЛИ (упрощенный формат)"""
        text = text.strip()
        if not text:
            return {}

        # Проверяем наличие ИЛИ на верхнем уровне
        if " ИЛИ " in text:
            alternatives = text.split(" ИЛИ ")
            or_conditions = []
            for alt in alternatives:
                alt = alt.strip()
                if alt:
                    or_conditions.append(self.parse_and_condition(alt))
            return {"__or__": or_conditions}
        else:
            return self.parse_and_condition(text)

    def parse_single_condition(self, text):
        """Разбор одного условия (без ИЛИ)"""
        result = {}
        # Разделяем по " И "
        parts = text.split(" И ")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Поиск оператора (важен порядок)
            operators = [">=", "<=", "!=", "=", ">", "<"]
            found_operator = None
            operator_pos = -1

            for op in operators:
                if op in part:
                    if op == "=" and (">=" in part or "<=" in part):
                        continue
                    found_operator = op
                    operator_pos = part.find(op)
                    break

            if found_operator is None:
                raise ValueError(f"Не найден оператор в условии: {part}")

            left = part[:operator_pos].strip()
            right = part[operator_pos + len(found_operator):].strip()

            if not left or not right:
                raise ValueError(f"Некорректный формат: {part}")

            value = self.parse_value(right)

            if found_operator == "=":
                result[left] = value
            else:
                result[left] = {found_operator: value}

        return result

    def parse_value(self, value_str):
        """Преобразует строку в число или строку (с поддержкой кавычек)"""
        value_str = value_str.strip()

        # Если значение в кавычках - сохраняем как строку без кавычек
        if (value_str.startswith('"') and value_str.endswith('"')) or \
                (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # Пробуем преобразовать в число
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            return value_str

    def parse_rule_with_else(self, condition_text, conclusion_text):
        """Разбор правила, которое может содержать ИНАЧЕ"""
        condition = self.parse_input_to_json(condition_text, "условия")

        conclusion = {}
        else_conclusion = None

        # Проверяем, есть ли разделитель "ИНАЧЕ"
        if " ИНАЧЕ " in conclusion_text.upper():
            parts = conclusion_text.upper().split(" ИНАЧЕ ", 1)
            then_part = parts[0].strip()
            else_part = parts[1].strip()

            conclusion = self.parse_input_to_json(then_part, "заключения THEN")
            else_conclusion = self.parse_input_to_json(else_part, "заключения ELSE")
        else:
            conclusion = self.parse_input_to_json(conclusion_text, "заключения")

        return condition, conclusion, else_conclusion

    def edit_selected_rule(self):
        """Редактирование выбранного правила (с поддержкой ELSE)"""
        selection = self.rules_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите правило для редактирования")
            return

        selected_text = self.rules_listbox.get(selection[0])
        if selected_text == "(нет правил в этой области)":
            messagebox.showwarning("Внимание", "Нет правил для редактирования")
            return

        rules = self.db.get_rules_by_subject_area(self.current_area_id)
        if selection[0] >= len(rules):
            return

        rule = rules[selection[0]]

        self.rule_name.delete(0, tk.END)
        self.rule_name.insert(0, rule['name'])

        # Отображаем условие
        self.condition_text.delete("1.0", tk.END)
        condition_str = self.format_condition_for_display(rule['condition'])
        self.condition_text.insert("1.0", condition_str)

        # Отображаем заключение (с ELSE если есть)
        self.conclusion_text.delete("1.0", tk.END)
        conclusion_str = self.format_conclusion_for_display(rule['conclusion'])
        if rule.get('else_conclusion'):
            conclusion_str += " ИНАЧЕ " + self.format_conclusion_for_display(rule['else_conclusion'])
        self.conclusion_text.insert("1.0", conclusion_str)

        self.priority.set(rule['priority'])

        self.editing_rule_id = rule['id']
        self.editing_rule_name = rule['name']

        # Применяем подсветку после загрузки
        FactHighlighter.highlight_connectors(self.condition_text)
        FactHighlighter.highlight_connectors(self.conclusion_text)

        self.notebook.select(0)

    def load_subject_areas(self):
        """Загрузить список предметных областей в комбобокс"""
        areas = self.db.get_all_subject_areas()

        if not areas:
            self.db.add_subject_area("Основная", "Предметная область по умолчанию")
            areas = self.db.get_all_subject_areas()

        self.subject_areas = areas

        if self.subject_area_combo:
            self.subject_area_combo['values'] = [area['name'] for area in areas]

            # Устанавливаем текущую область
            current_id = self.db.get_current_subject_area_id()

            found = False
            for area in areas:
                if area['id'] == current_id:
                    self.subject_area_combo.set(area['name'])
                    self.current_area_id = area['id']
                    found = True
                    break

            if not found and areas:
                self.subject_area_combo.set(areas[0]['name'])
                self.current_area_id = areas[0]['id']
                self.db.set_current_subject_area(self.current_area_id)

            # Обновляем список правил
            self.refresh_rules_list()

    def refresh_rules_list(self):
        """Обновить список правил в интерфейсе"""
        self.rules_listbox.delete(0, tk.END)

        if not hasattr(self, 'current_area_id'):
            self.current_area_id = 1

        rules = self.db.get_rules_by_subject_area(self.current_area_id)

        if not rules:
            self.rules_listbox.insert(tk.END, "(нет правил в этой области)")
        else:
            for rule in rules:
                display_text = f"{rule['name']} (приоритет {rule['priority']})"
                self.rules_listbox.insert(tk.END, display_text)

        # Очищаем область просмотра
        self.rule_view_text.config(state=tk.NORMAL)
        self.rule_view_text.delete("1.0", tk.END)
        self.rule_view_text.config(state=tk.DISABLED)

    def on_subject_area_change(self, event=None):
        """Обработчик смены предметной области"""
        selected_name = self.subject_area_combo.get()
        for area in self.subject_areas:
            if area['name'] == selected_name:
                self.current_area_id = area['id']
                self.db.set_current_subject_area(self.current_area_id)
                # Очищаем форму редактирования
                self.clear_rule_form()
                # Обновляем список правил
                self.refresh_rules_list()
                break

    def add_subject_area_dialog(self):
        """Диалог добавления новой предметной области"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая предметная область")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Название предметной области:", font=("Arial", 10)).pack(pady=10)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="Описание (необязательно):").pack(pady=5)
        desc_entry = ttk.Entry(dialog, width=40)
        desc_entry.pack(pady=5)

        def save_area():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Введите название")
                return

            area_id = self.db.add_subject_area(name, desc_entry.get().strip())
            if area_id:
                messagebox.showinfo("Успех", f"Предметная область '{name}' создана")

                # Обновляем список областей
                self.subject_areas = self.db.get_all_subject_areas()
                self.subject_area_combo['values'] = [area['name'] for area in self.subject_areas]

                # Устанавливаем новую область как текущую
                self.subject_area_combo.set(name)
                self.current_area_id = area_id
                self.db.set_current_subject_area(area_id)

                # Очищаем форму редактирования
                self.clear_rule_form()

                # Обновляем список правил (он будет пустым для новой области)
                self.refresh_rules_list()

                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Область с таким названием уже существует")

        ttk.Button(dialog, text="Создать", command=save_area).pack(pady=10)

    def delete_subject_area_dialog(self):
        """Диалог удаления предметной области"""
        # Получаем актуальный список областей
        self.subject_areas = self.db.get_all_subject_areas()

        if len(self.subject_areas) <= 1:
            messagebox.showwarning("Внимание", "Нельзя удалить последнюю предметную область")
            return

        selected = self.subject_area_combo.get()

        # Находим ID выбранной области
        selected_id = None
        for area in self.subject_areas:
            if area['name'] == selected:
                selected_id = area['id']
                break

        if selected_id is None:
            messagebox.showerror("Ошибка", "Не удалось найти выбранную область")
            return

        answer = messagebox.askyesno(
            "Подтверждение",
            f"Удалить предметную область '{selected}'?\n\nВсе правила из этой области будут также удалены."
        )

        if answer:
            # Удаляем область
            self.db.delete_subject_area(selected_id)

            # Обновляем список областей
            self.subject_areas = self.db.get_all_subject_areas()
            self.subject_area_combo['values'] = [area['name'] for area in self.subject_areas]

            # Переключаемся на первую область
            if self.subject_areas:
                first_area = self.subject_areas[0]
                self.subject_area_combo.set(first_area['name'])
                self.current_area_id = first_area['id']
                self.db.set_current_subject_area(self.current_area_id)

                # Обновляем список правил
                self.refresh_rules_list()
                self.clear_rule_form()

                messagebox.showinfo("Успех",
                                    f"Предметная область '{selected}' удалена. Текущая область: '{first_area['name']}'")

    def delete_all_rules_dialog(self):
        """Диалог подтверждения удаления всех правил"""
        current_area_name = self.subject_area_combo.get()
        answer = messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите удалить ВСЕ правила из предметной области '{current_area_name}'?\n\nЭто действие нельзя отменить."
        )
        if answer:
            self.db.delete_all_rules_in_area(self.current_area_id)
            self.refresh_rules_list()
            self.clear_rule_form()
            messagebox.showinfo("Успех", f"Все правила из области '{current_area_name}' удалены")

    # ============= ОСТАЛЬНЫЕ МЕТОДЫ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ =============

    def on_rule_select(self, event):
        """Событие при выборе правила из списка"""
        selection = self.rules_listbox.curselection()
        if not selection:
            return

        selected_text = self.rules_listbox.get(selection[0])
        if selected_text == "(Нет правил в этой области)":
            return

        rules = self.db.get_rules_by_subject_area(self.current_area_id)
        if selection[0] < len(rules):
            rule = rules[selection[0]]
            self.display_rule_content(rule)

    def display_rule_content(self, rule):
        """Отобразить содержимое правила"""
        self.rule_view_text.config(state=tk.NORMAL)
        self.rule_view_text.delete("1.0", tk.END)

        content = f"Название: {rule['name']}\n"
        content += f"Приоритет: {rule['priority']}\n\n"
        content += f"УСЛОВИЕ (IF):\n{self.format_condition_for_display(rule['condition'])}\n\n"
        content += f"ЗАКЛЮЧЕНИЕ (THEN):\n{self.format_conclusion_for_display(rule['conclusion'])}\n"

        if rule.get('else_conclusion'):
            content += f"\nИНАЧЕ (ELSE):\n{self.format_conclusion_for_display(rule['else_conclusion'])}\n"

        self.rule_view_text.insert("1.0", content)
        self.rule_view_text.config(state=tk.DISABLED)

    def format_condition_for_display(self, condition):
        """Форматирует условие для отображения"""
        if not condition:
            return ""

        # Обработка ИЛИ
        if "__or__" in condition:
            alternatives = condition["__or__"]
            formatted_alts = []
            for alt in alternatives:
                parts = []
                for key, value in alt.items():
                    if isinstance(value, dict):
                        for op, val in value.items():
                            parts.append(f"{key} {op} {val}")
                    else:
                        parts.append(f"{key} = {value}")
                formatted_alts.append(" И ".join(parts))
            return " ИЛИ ".join(formatted_alts)

        # Обычное И
        parts = []
        for key, value in condition.items():
            if isinstance(value, dict):
                for op, val in value.items():
                    parts.append(f"{key} {op} {val}")
            else:
                parts.append(f"{key} = {value}")
        return " И ".join(parts)

    def format_conclusion_for_display(self, conclusion):
        """Форматирует заключение для отображения"""
        if not conclusion:
            return ""
        parts = []
        for key, value in conclusion.items():
            parts.append(f"{key} = {value}")
        return "\n".join(parts)

    def clear_rule_form(self):
        """Очистить форму создания правила"""
        self.rule_name.delete(0, tk.END)
        self.condition_text.delete("1.0", tk.END)
        self.conclusion_text.delete("1.0", tk.END)
        self.priority.set(5)
        self.editing_rule_id = None
        self.editing_rule_name = None
        self.rules_listbox.selection_clear(0, tk.END)
        # Переподсветка
        FactHighlighter.highlight_connectors(self.condition_text)
        FactHighlighter.highlight_connectors(self.conclusion_text)

    def delete_rule(self):
        """Удалить выбранное правило"""
        selection = self.rules_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите правило для удаления")
            return

        selected_text = self.rules_listbox.get(selection[0])
        if selected_text == "(нет правил в этой области)":
            messagebox.showwarning("Внимание", "Нет правил для удаления")
            return

        rules = self.db.get_rules_by_subject_area(self.current_area_id)
        if selection[0] >= len(rules):
            return

        rule_id = rules[selection[0]]['id']
        rule_name = rules[selection[0]]['name']

        if messagebox.askyesno("Подтверждение", f"Удалить правило '{rule_name}'?"):
            self.db.delete_rule(rule_id)
            self.refresh_rules_list()
            self.clear_rule_form()

    def create_inference_tab(self):
        """Вкладка для прямого вывода"""
        top_frame = ttk.LabelFrame(self.tab_inference, text="Введите исходные факты", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Факты:").pack(anchor=tk.W)

        # Рамка для поля ввода и кнопки
        input_frame = ttk.Frame(top_frame)
        input_frame.pack(fill=tk.X, pady=5)

        # Поле ввода фактов (занимает всё доступное место)
        self.facts_input = scrolledtext.ScrolledText(input_frame, height=4)
        self.facts_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.enable_copy_paste(self.facts_input)

        # Кнопка запуска справа
        run_button = ttk.Button(input_frame, text="Запустить прямой вывод",
                                command=self.run_forward_chaining)
        run_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Нижняя часть - результат и трассировка с возможностью изменения размера
        paned_window = ttk.PanedWindow(self.tab_inference, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая часть - результат вывода (широкая)
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=3)

        # Рамка для результата
        result_label_frame = ttk.LabelFrame(left_frame, text="Результат вывода", padding=5)
        result_label_frame.pack(fill=tk.BOTH, expand=True)

        # Текстовое поле для результата
        self.result_text = tk.Text(result_label_frame, height=20, wrap=tk.NONE)

        # Вертикальная прокрутка для результата
        result_scroll_y = ttk.Scrollbar(result_label_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        # Горизонтальная прокрутка для результата
        result_scroll_x = ttk.Scrollbar(result_label_frame, orient=tk.HORIZONTAL, command=self.result_text.xview)

        self.result_text.configure(yscrollcommand=result_scroll_y.set, xscrollcommand=result_scroll_x.set)

        # Размещение
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scroll_y.grid(row=0, column=1, sticky="ns")
        result_scroll_x.grid(row=1, column=0, sticky="ew")

        result_label_frame.grid_rowconfigure(0, weight=1)
        result_label_frame.grid_columnconfigure(0, weight=1)

        self.enable_copy_paste(self.result_text)

        # Правая часть - трассировка (узкая)
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        # Рамка для трассировки
        trace_label_frame = ttk.LabelFrame(right_frame, text="Трассировка (пошагово)", padding=5)
        trace_label_frame.pack(fill=tk.BOTH, expand=True)

        # Текстовое поле для трассировки с wrap=WORD (перенос слов)
        self.trace_text = tk.Text(trace_label_frame, height=20, wrap=tk.WORD)

        # Вертикальная прокрутка для трассировки
        trace_scroll_y = ttk.Scrollbar(trace_label_frame, orient=tk.VERTICAL, command=self.trace_text.yview)
        # Горизонтальная прокрутка для трассировки (на случай длинных строк)
        trace_scroll_x = ttk.Scrollbar(trace_label_frame, orient=tk.HORIZONTAL, command=self.trace_text.xview)

        self.trace_text.configure(yscrollcommand=trace_scroll_y.set, xscrollcommand=trace_scroll_x.set)

        # Размещение
        self.trace_text.grid(row=0, column=0, sticky="nsew")
        trace_scroll_y.grid(row=0, column=1, sticky="ns")
        trace_scroll_x.grid(row=1, column=0, sticky="ew")

        trace_label_frame.grid_rowconfigure(0, weight=1)
        trace_label_frame.grid_columnconfigure(0, weight=1)

        self.enable_copy_paste(self.trace_text)

        # Кнопки для трассировки (внизу)
        trace_buttons_frame = ttk.Frame(trace_label_frame)
        trace_buttons_frame.grid(row=2, column=0, columnspan=2, pady=(5, 0))
        ttk.Button(trace_buttons_frame, text="📋 Копировать",
                   command=lambda: self.copy_to_clipboard(self.trace_text)).pack(side=tk.LEFT, padx=2)
        ttk.Button(trace_buttons_frame, text="💾 Сохранить",
                   command=lambda: self.save_text_to_file(self.trace_text, "Трассировка")).pack(side=tk.LEFT, padx=2)

    def create_explain_tab(self):
        """Вкладка для обратного вывода"""
        top_frame = ttk.LabelFrame(self.tab_explain, text="Цель для подтверждения", padding=10)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(top_frame, text="Цель:").pack(anchor=tk.W)

        # Рамка для поля ввода и кнопки
        input_frame = ttk.Frame(top_frame)
        input_frame.pack(fill=tk.X, pady=5)

        # Поле ввода цели (занимает всё доступное место)
        self.explain_input = scrolledtext.ScrolledText(input_frame, height=3)
        self.explain_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.enable_copy_paste(self.explain_input)

        # Кнопка "Объяснить" справа (не растягивается)
        explain_button = ttk.Button(input_frame, text="Объяснить",
                                    command=self.run_backward_chaining)
        explain_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Нижняя часть - результат объяснения (одно поле на всю ширину)
        bottom_frame = ttk.Frame(self.tab_explain)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Рамка для результата
        result_label_frame = ttk.LabelFrame(bottom_frame, text="Объяснение", padding=10)
        result_label_frame.pack(fill=tk.BOTH, expand=True)

        # Текстовое поле для результата
        self.explain_result = tk.Text(result_label_frame, height=20, wrap=tk.WORD)

        # Вертикальная прокрутка
        result_scroll_y = ttk.Scrollbar(result_label_frame, orient=tk.VERTICAL, command=self.explain_result.yview)
        # Горизонтальная прокрутка (на случай длинных строк)
        result_scroll_x = ttk.Scrollbar(result_label_frame, orient=tk.HORIZONTAL, command=self.explain_result.xview)

        self.explain_result.configure(yscrollcommand=result_scroll_y.set, xscrollcommand=result_scroll_x.set)

        # Размещение
        self.explain_result.grid(row=0, column=0, sticky="nsew")
        result_scroll_y.grid(row=0, column=1, sticky="ns")
        result_scroll_x.grid(row=1, column=0, sticky="ew")

        result_label_frame.grid_rowconfigure(0, weight=1)
        result_label_frame.grid_columnconfigure(0, weight=1)

        self.enable_copy_paste(self.explain_result)

        # Кнопки внизу
        buttons_frame = ttk.Frame(result_label_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(buttons_frame, text="Копировать",
                   command=lambda: self.copy_to_clipboard(self.explain_result)).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons_frame, text="Сохранить",
                   command=lambda: self.save_text_to_file(self.explain_result, "Обратный_вывод")).pack(side=tk.LEFT,
                                                                                                       padx=2)

    def copy_to_clipboard(self, text_widget):
        """Копировать содержимое текстового виджета в буфер обмена"""
        try:
            content = text_widget.get("1.0", tk.END).strip()
            if content:
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать текст: {e}")

    def save_text_to_file(self, text_widget, default_name="export"):
        """Сохранить текст в файл"""
        try:
            content = text_widget.get("1.0", tk.END).strip()
            if not content:
                messagebox.showwarning("Внимание", "Нет текста для сохранения")
                return

            current_area_name = "Неизвестная_область"
            if hasattr(self, 'subject_area_combo') and self.subject_area_combo.get():
                current_area_name = self.subject_area_combo.get()

            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                current_area_name = current_area_name.replace(char, '_')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{current_area_name}_{default_name}_{timestamp}.txt"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
                initialfile=default_filename,
                title=f"Сохранить {default_name}"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Успех", f"Файл сохранен:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def run_forward_chaining(self):
        """Запустить прямой вывод"""
        try:
            # Нормализуем операторы перед обработкой
            FactHighlighter.normalize_operators(self.facts_input)

            facts_text = self.facts_input.get("1.0", tk.END).strip()
            if not facts_text:
                messagebox.showwarning("Внимание", "Введите исходные факты")
                return

            try:
                # Используем тот же парсер, что и для правил
                if " И " in facts_text or " ИЛИ " in facts_text:
                    facts = self.parse_and_condition(facts_text)
                else:
                    facts = self.parse_input_to_json(facts_text, "фактов")
            except ValueError as e:
                messagebox.showerror("Ошибка формата", f"Ошибка при разборе фактов:\n{e}")
                return

            initial_facts = set(facts.keys())

            self.engine.load_rules_from_db()
            self.engine.load_rules_from_area(self.current_area_id)
            self.engine.set_facts(facts)

            final_facts, trace = self.engine.forward_chaining()

            self.last_inferred_facts = final_facts.copy()

            final_facts_set = set(final_facts.keys())
            added_facts = final_facts_set - initial_facts

            # Настраиваем тег для жирного текста
            self.result_text.tag_configure("bold", font=("Arial", 9, "bold"))

            self.result_text.delete("1.0", tk.END)

            # Выводим исходные факты
            self.result_text.insert(tk.END, "ИСХОДНЫЕ ФАКТЫ:\n")
            self.result_text.insert(tk.END, "-" * 40 + "\n")
            for fact in sorted(initial_facts):
                value = final_facts[fact]
                self.result_text.insert(tk.END, f"  • {fact} = {value}\n")

            # Выводим добавленные факты
            if added_facts:
                self.result_text.insert(tk.END, f"\nВЫВЕДЕННЫЕ ФАКТЫ:\n")
                self.result_text.insert(tk.END, "-" * 40 + "\n")
                for fact in sorted(added_facts):
                    value = final_facts[fact]
                    # Вставляем текст
                    self.result_text.insert(tk.END, f"  • {fact} = {value} ")
                    # Вставляем "(добавлен)" жирным
                    start_bold = self.result_text.index(tk.END)
                    self.result_text.insert(tk.END, "(добавлен)")
                    end_bold = self.result_text.index(tk.END)
                    self.result_text.tag_add("bold", start_bold, end_bold)
                    self.result_text.insert(tk.END, "\n")
            else:
                self.result_text.insert(tk.END, f"\nНОВЫХ ФАКТОВ НЕ ВЫВЕДЕНО\n")

            # Статистика
            self.result_text.insert(tk.END, "\n" + "-" * 40 + "\n")
            self.result_text.insert(tk.END, f"Исходных: {len(initial_facts)}  |  Выведено: {len(added_facts)}\n")

            # Трассировка - обрабатываем как строки, так и структурированные данные
            self.trace_text.delete("1.0", tk.END)
            self.trace_text.insert(tk.END, "ПОШАГОВАЯ ТРАССИРОВКА ВЫВОДА\n")
            self.trace_text.insert(tk.END, "-" * 40 + "\n\n")

            # Настраиваем теги для цветов
            # Настраиваем теги для цветов
            self.trace_text.tag_configure("green_fact", foreground="#008000", font=("Arial", 9, "bold"))
            self.trace_text.tag_configure("rule_name_success", foreground="#0066CC",
                                          font=("Arial", 9, "bold"))  # Синий для сработавших
            self.trace_text.tag_configure("rule_name_fail", foreground="#002952",
                                          font=("Arial", 9, "bold"))  # Темно-серый для не сработавших

            if not trace:
                self.trace_text.insert(tk.END, "Ни одно правило не сработало.\n")
            else:
                for step in trace:
                    if isinstance(step, dict) and step.get('type') == 'step_with_colors':
                        # Цветной вывод для сработавших правил
                        self.trace_text.insert(tk.END, f"Шаг {step['step_num']}. Правило '")
                        self.trace_text.insert(tk.END, step['rule_name'], "rule_name_success")  # Синий
                        self.trace_text.insert(tk.END, f"' ПОДХОДИТ\n")

                        if step['condition_met']:
                            self.trace_text.insert(tk.END, f"   ✓ Условие выполнено: {step['conditions_str']}\n")
                        else:
                            self.trace_text.insert(tk.END, f"   ✗ Условие НЕ выполнено: {step['reason']}\n")
                            self.trace_text.insert(tk.END, f"   Идем по ветке ИНАЧЕ (ELSE)\n")

                        self.trace_text.insert(tk.END, f"   В базу добавлены факты: ")

                        # Выводим каждый факт с зеленым цветом
                        for i, fact in enumerate(step['formatted_facts']):
                            if i > 0:
                                self.trace_text.insert(tk.END, ", ")

                            # Ищем часть с добавленным фактом
                            if "(было '" in fact:
                                parts = fact.split(" (было ")
                                fact_part = parts[0]
                                old_part = parts[1].rstrip(")")

                                self.trace_text.insert(tk.END, fact_part, "green_fact")
                                self.trace_text.insert(tk.END, f" (было '{old_part}')")
                            else:
                                self.trace_text.insert(tk.END, fact, "green_fact")

                        self.trace_text.insert(tk.END, f"\n")
                        self.trace_text.insert(tk.END, f"   Заключение: {step['conclusion']}\n\n")

                    elif isinstance(step, str):
                        # Для строковых сообщений проверяем, содержит ли "НЕ ПОДХОДИТ"
                        if "НЕ ПОДХОДИТ" in step:
                            # Разбираем строку, чтобы выделить имя правила темно-синим
                            import re
                            match = re.search(r"Правило '([^']+)'", step)
                            if match:
                                rule_name = match.group(1)
                                parts = step.split(f"Правило '{rule_name}'")
                                self.trace_text.insert(tk.END, parts[0])
                                self.trace_text.insert(tk.END, f"Правило '", "")
                                self.trace_text.insert(tk.END, rule_name, "rule_name_fail")
                                self.trace_text.insert(tk.END, f"'", "")
                                self.trace_text.insert(tk.END, parts[1] if len(parts) > 1 else "")
                            else:
                                self.trace_text.insert(tk.END, step)
                        else:
                            self.trace_text.insert(tk.END, step)
                        self.trace_text.insert(tk.END, "\n")  # Один перевод строки в конце

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            import traceback
            traceback.print_exc()

    def run_backward_chaining(self):
        """Запустить обратный вывод"""
        try:
            # Нормализуем операторы перед обработкой
            FactHighlighter.normalize_operators(self.explain_input)

            explain_text = self.explain_input.get("1.0", tk.END).strip()
            if not explain_text:
                messagebox.showwarning("Внимание", "Введите факт для объяснения")
                return

            try:
                parsed_fact = self.parse_input_to_json(explain_text, "факта для объяснения")
            except ValueError as e:
                messagebox.showerror("Ошибка формата", f"Ошибка при разборе факта:\n{e}\n\n"
                                                       f"Пример правильного формата:\n"
                                                       f"возраст_подтвержден = да\n"
                                                       f"или\n"
                                                       f"возраст >= 18")
                return

            if len(parsed_fact) == 0:
                messagebox.showerror("Ошибка", "Не удалось распознать факт")
                return

            fact_name = list(parsed_fact.keys())[0]
            fact_value = parsed_fact[fact_name]

            self.explain_result.delete("1.0", tk.END)

            # Загружаем правила из текущей области
            self.engine.load_rules_from_area(self.current_area_id)

            # Загружаем факты из последнего прямого вывода
            if self.last_inferred_facts:
                self.engine.facts = self.last_inferred_facts.copy()
                self.engine.fact_priorities = {}
                for fact in self.engine.facts:
                    self.engine.fact_priorities[fact] = 5

                if not hasattr(self.engine, 'fact_sources'):
                    self.engine.fact_sources = {}
            else:
                self.engine.facts = {}
                self.engine.fact_priorities = {}
                self.engine.fact_sources = {}

            if isinstance(fact_value, dict):
                operator = list(fact_value.keys())[0]
                target_value = fact_value[operator]
                goal = f"{fact_name} {operator} {target_value}"

                result, trace = self.engine.backward_chaining_with_operator(fact_name, operator, target_value)

                if not result:
                    self.explain_result.insert(tk.END, f"Не удалось подтвердить цель: {goal}\n")
                    return

                formatted = self.engine.format_backward_trace(trace, goal)
                self.explain_result.insert(tk.END, formatted)
            else:
                goal = f"{fact_name} = {fact_value}"

                result, trace = self.engine.backward_chaining(fact_name, fact_value)

                if not result:
                    self.explain_result.insert(tk.END, f"Не удалось подтвердить цель: {goal}\n")
                    return

                formatted = self.engine.format_backward_trace(trace, goal)
                self.explain_result.insert(tk.END, formatted)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            import traceback
            traceback.print_exc()

    def clear_database(self):
        """Очистить базу данных"""
        if messagebox.askyesno("Внимание", "Удалить все правила?"):
            self.db.delete_all_rules_in_area(self.current_area_id)
            self.refresh_rules_list()

    def view_all_rules(self):
        """Открыть окно для просмотра всех правил текущей области"""
        rules = self.db.get_rules_by_subject_area(self.current_area_id)

        if not rules:
            messagebox.showinfo("Информация", "В текущей предметной области нет правил")
            return

        view_window = tk.Toplevel(self.root)
        view_window.title(f"Просмотр правил - {self.subject_area_combo.get()}")
        view_window.geometry("800x600")
        text_area = scrolledtext.ScrolledText(view_window, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Формируем содержимое
        content = f"ПРЕДМЕТНАЯ ОБЛАСТЬ: {self.subject_area_combo.get()}\n"
        content += f"Всего правил: {len(rules)}\n"
        content += "=" * 60 + "\n\n"

        for i, rule in enumerate(rules, 1):
            content += f"ПРАВИЛО {i}: {rule['name']}\n"
            content += f"Приоритет: {rule['priority']}\n"
            content += f"ЕСЛИ: {self.format_condition_for_display(rule['condition'])}\n"
            content += f"ТО: {self.format_conclusion_for_display(rule['conclusion'])}\n"
            if rule.get('else_conclusion'):
                content += f"ИНАЧЕ: {self.format_conclusion_for_display(rule['else_conclusion'])}\n"
            if rule.get('description'):
                content += f"Описание: {rule['description']}\n"
            content += "-" * 40 + "\n\n"

        text_area.insert("1.0", content)
        text_area.config(state=tk.DISABLED)

        def save_to_file():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt")],
                initialfile=f"правила_{self.subject_area_combo.get()}.txt"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Успех", "Файл сохранен")

        ttk.Button(view_window, text="Сохранить в файл", command=save_to_file).pack(pady=5)

    def view_database_structure(self):
        """Открыть окно с табличной структурой базы знаний"""
        from tkinter import ttk

        db_window = tk.Toplevel(self.root)
        db_window.title("Предметные области в текущей БД")
        db_window.geometry("1000x650")

        # Создаем фрейм для таблицы с рамкой
        table_frame = ttk.LabelFrame(db_window, text="База знаний", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем Treeview с явными колонками
        columns = ("id", "область", "правило", "условие", "заключение", "приоритет")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        # Настройка заголовков и ширины колонок
        tree.heading("id", text="ID")
        tree.heading("область", text="Предметная область")
        tree.heading("правило", text="Название правила")
        tree.heading("условие", text="Условие (IF)")
        tree.heading("заключение", text="Заключение (THEN)")
        tree.heading("приоритет", text="Приор.")

        tree.column("id", width=40, anchor="center")
        tree.column("область", width=120, anchor="w")
        tree.column("правило", width=150, anchor="w")
        tree.column("условие", width=350, anchor="w")
        tree.column("заключение", width=200, anchor="w")
        tree.column("приоритет", width=50, anchor="center")

        # Включаем вертикальные и горизонтальные полосы прокрутки
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Размещение таблицы и скроллбаров
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Настройка стиля для отображения границ
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Arial", 9, "bold"))
        style.configure("Treeview", font=("Arial", 8), rowheight=25)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        # Добавляем данные в таблицу
        areas = self.db.get_all_subject_areas()
        row_id = 0
        for area in areas:
            rules = self.db.get_rules_by_subject_area(area['id'])
            if rules:
                for rule in rules:
                    condition_str = self.format_condition_for_display(rule['condition'])
                    conclusion_str = self.format_conclusion_for_display(rule['conclusion']).replace("\n", "; ")

                    tree.insert("", "end", iid=str(row_id), values=(
                        rule['id'],
                        area['name'],
                        rule['name'],
                        condition_str,
                        conclusion_str,
                        rule['priority']
                    ))
                    row_id += 1
            else:
                # Пустая строка для области без правил
                tree.insert("", "end", iid=str(row_id), values=(
                    "-",
                    area['name'],
                    "(нет правил)",
                    "-",
                    "-",
                    "-"
                ))
                row_id += 1

        info_frame = ttk.Frame(db_window)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        info_label = ttk.Label(info_frame, text=f"Всего правил: {len(tree.get_children())}", font=("Arial", 9))
        info_label.pack(side=tk.LEFT, padx=5)

        def export_table():
            """Экспорт таблицы"""
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
                initialfile=f"база_знаний_{datetime.now().strftime('%Y%m%d')}.csv"
            )
            if file_path:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ["ID", "Предметная область", "Название правила", "Условие", "Заключение", "Приоритет"])
                    for item in tree.get_children():
                        values = tree.item(item, "values")
                        writer.writerow(values)
                messagebox.showinfo("Успех", f"Таблица экспортирована в:\n{file_path}")

        ttk.Button(info_frame, text="Копировать таблицу", command=lambda: self.copy_table_to_clipboard(tree)).pack(
            side=tk.RIGHT, padx=2)
        ttk.Button(info_frame, text="Экспорт в CSV", command=export_table).pack(side=tk.RIGHT, padx=2)

    def copy_table_to_clipboard(self, tree):
        """Скопировать таблицу в буфер обмена"""
        try:
            headers = [tree.heading(col)["text"] for col in tree["columns"]]
            content = "\t".join(headers) + "\n"
            content += "-" * 80 + "\n"

            for item in tree.get_children():
                values = tree.item(item, "values")
                content += "\t".join(str(v) for v in values) + "\n"

            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Успех", "Таблица скопирована в буфер обмена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {e}")

    def setup_all_highlighters(self):
        """Настраивает подсветку для всех текстовых полей"""
        # Для вкладки правил
        FactHighlighter.setup_highlighting(self.condition_text)
        FactHighlighter.setup_highlighting(self.conclusion_text)

        # Для вкладки прямого вывода
        FactHighlighter.setup_highlighting(self.facts_input)

        # Для вкладки обратного вывода
        FactHighlighter.setup_highlighting(self.explain_input)

        # Устанавливаем отступы для всех текстовых полей
        for widget in [self.condition_text, self.conclusion_text,
                       self.facts_input, self.explain_input]:
            widget.config(
                spacing1=4,  # Отступ сверху
                spacing2=2,  # Между строками
                spacing3=4,  # Отступ снизу
                padx=5,  # Внутренний отступ по горизонтали
                pady=3  # Внутренний отступ по вертикали
            )

        # Привязываем нормализацию операторов при потере фокуса
        self.condition_text.bind('<FocusOut>', lambda e: FactHighlighter.normalize_operators(self.condition_text))
        self.conclusion_text.bind('<FocusOut>', lambda e: FactHighlighter.normalize_operators(self.conclusion_text))
        self.facts_input.bind('<FocusOut>', lambda e: FactHighlighter.normalize_operators(self.facts_input))
        self.explain_input.bind('<FocusOut>', lambda e: FactHighlighter.normalize_operators(self.explain_input))

    def show_about(self):
        messagebox.showinfo("О программе",
                            "Лабораторный комплекс для изучения продукционных баз знаний\n\n"
                            "Разработано в рамках дипломной работы\n\n"
                            "Функции:\n"
                            "- Создание и редактирование правил\n"
                            "- Прямой вывод с трассировкой\n"
                            "- Обратный вывод (объяснение результатов)\n\n"
                            "Форматы ввода:\n"
                            "- Упрощенный: возраст >= 18 И есть_паспорт = да\n"
                            "- JSON: {\"возраст\": {\">=\": 18}}")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = LabComplexApp(root)
    root.mainloop()