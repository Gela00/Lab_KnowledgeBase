import tkinter as tk
from tkinter import scrolledtext
import re


class FactHighlighter:
    """Класс для подсветки соединителей, операторов и переменных в текстовых виджетах"""

    @staticmethod
    def setup_highlighting(text_widget):
        """Настраивает подсветку для текстового виджета"""
        # Для соединителей (И, ИЛИ, ИНАЧЕ) - красный
        text_widget.tag_configure("connector_tag",
                                  foreground="#CC0000",
                                  font=("Arial", 9, "bold"))

        # Для операторов (=, >, <, >=, <=, !=) - голубой
        text_widget.tag_configure("operator_tag",
                                  foreground="#0066CC",
                                  font=("Arial", 9, "bold"))

        # Для переменных ($имя или {имя}) - синий
        text_widget.tag_configure("variable_tag",
                                  foreground="#0055AA",
                                  font=("Arial", 9, "bold"),
                                  background="#E6F0FF")

        text_widget.bind('<KeyRelease>', lambda e: FactHighlighter.highlight_all(text_widget))
        text_widget.bind('<ButtonRelease-1>', lambda e: FactHighlighter.highlight_all(text_widget))

        FactHighlighter.highlight_all(text_widget)

    @staticmethod
    def highlight_all(text_widget):
        """Подсветка всех элементов"""
        try:
            cursor_pos = text_widget.index(tk.INSERT)
        except:
            cursor_pos = "1.0"

        try:
            sel_start = text_widget.index(tk.SEL_FIRST)
            sel_end = text_widget.index(tk.SEL_LAST)
            had_selection = True
        except:
            had_selection = False

        text_widget.tag_remove("connector_tag", "1.0", tk.END)
        text_widget.tag_remove("operator_tag", "1.0", tk.END)
        text_widget.tag_remove("variable_tag", "1.0", tk.END)

        content = text_widget.get("1.0", tk.END)
        lines = content.split('\n')

        for line_idx, line in enumerate(lines, 1):
            if not line.strip():
                continue

            # Подсвечиваем соединители (И, ИЛИ, ИНАЧЕ) - красным
            for pattern in [r'\bИ\b', r'\bИЛИ\b', r'\bИНАЧЕ\b']:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    start, end = match.span()
                    text_widget.tag_add("connector_tag", f"{line_idx}.{start}", f"{line_idx}.{end}")

            # Подсвечиваем операторы (=, >, <, >=, <=, !=) - голубым
            operator_patterns = [r'>=', r'<=', r'!=', r'=', r'>', r'<']
            for op in operator_patterns:
                for match in re.finditer(re.escape(op), line):
                    start, end = match.span()
                    text_widget.tag_add("operator_tag", f"{line_idx}.{start}", f"{line_idx}.{end}")

            # Подсвечиваем переменные ($имя или {имя}) - синим фоном
            var_patterns = [r'\$\w+', r'\{[^}]+\}']
            for pattern in var_patterns:
                for match in re.finditer(pattern, line):
                    start, end = match.span()
                    text_widget.tag_add("variable_tag", f"{line_idx}.{start}", f"{line_idx}.{end}")

        if had_selection:
            try:
                text_widget.tag_add(tk.SEL, sel_start, sel_end)
            except:
                pass

        try:
            text_widget.mark_set(tk.INSERT, cursor_pos)
        except:
            pass

    @staticmethod
    def highlight_facts(text_widget):
        """Метод для обратной совместимости"""
        FactHighlighter.highlight_all(text_widget)

    @staticmethod
    def highlight_connectors(text_widget):
        """Метод для обратной совместимости"""
        FactHighlighter.highlight_all(text_widget)

    @staticmethod
    def normalize_operators(text_widget):
        """Нормализует операторы (приводит к верхнему регистру)"""
        content = text_widget.get("1.0", tk.END)

        try:
            cursor_pos = text_widget.index(tk.INSERT)
        except:
            cursor_pos = "1.0"

        try:
            sel_start = text_widget.index(tk.SEL_FIRST)
            sel_end = text_widget.index(tk.SEL_LAST)
            had_selection = True
        except:
            had_selection = False

        # Заменяем соединители на заглавные
        new_content = content
        replacements = [
            (r'\bи\b', ' И '),
            (r'\bили\b', ' ИЛИ '),
            (r'\bиначе\b', ' ИНАЧЕ '),
        ]

        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE)

        # Приводим операторы к правильному виду
        new_content = re.sub(r'\s*(>=|<=|!=|=|>|<)\s*', r' \1 ', new_content)
        new_content = re.sub(r' +', ' ', new_content)
        new_content = re.sub(r'^ ', '', new_content)
        new_content = re.sub(r' $', '', new_content)

        if new_content != content:
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", new_content)

            if had_selection:
                try:
                    text_widget.tag_add(tk.SEL, sel_start, sel_end)
                except:
                    pass

            try:
                text_widget.mark_set(tk.INSERT, cursor_pos)
            except:
                pass

        FactHighlighter.highlight_all(text_widget)