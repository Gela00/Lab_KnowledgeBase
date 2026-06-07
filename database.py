import sqlite3
import json


class Database:
    def __init__(self, db_name="knowledge_base.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.current_area_id = 1
        self.create_tables()
    def create_tables(self):
        # Таблица для предметных областей (создаем первой)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subject_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица для правил
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition TEXT NOT NULL,
                conclusion TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                description TEXT,
                subject_area_id INTEGER REFERENCES subject_areas(id) DEFAULT 1,
                else_conclusion TEXT
            )
        ''')

        # Таблица для фактов (история сессий)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                fact_name TEXT,
                fact_value TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица для трассировки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                step_number INTEGER,
                rule_used TEXT,
                facts_before TEXT,
                facts_added TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Проверяем, есть ли хотя бы одна предметная область
        self.cursor.execute('SELECT COUNT(*) FROM subject_areas')
        count = self.cursor.fetchone()[0]

        if count == 0:
            self.cursor.execute('''
                INSERT INTO subject_areas (name, description) VALUES (?, ?)
            ''', ("Основная", "Предметная область по умолчанию"))

        self.conn.commit()


    def _serialize_value(self, value):
        """Рекурсивно сериализует значения для JSON, преобразуя числа в строки"""
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return value

    def _deserialize_value(self, value):
        """Рекурсивно десериализует значения из JSON, преобразуя строки-числа обратно в числа"""
        if isinstance(value, dict):
            return {k: self._deserialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._deserialize_value(v) for v in value]
        elif isinstance(value, str):
            # Пробуем преобразовать в число
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except (ValueError, TypeError):
                return value
        else:
            return value

    def add_rule_with_area(self, name, condition, conclusion, priority=5, subject_area_id=1, description="",
                           else_conclusion=None):
        """Добавить правило в конкретную предметную область"""
        # Сериализуем значения (числа в строки)
        condition_serialized = self._serialize_value(condition)
        conclusion_serialized = self._serialize_value(conclusion)

        cond_json = json.dumps(condition_serialized, ensure_ascii=False)
        concl_json = json.dumps(conclusion_serialized, ensure_ascii=False)
        else_json = json.dumps(self._serialize_value(else_conclusion), ensure_ascii=False) if else_conclusion else None

        self.cursor.execute('''
            INSERT INTO rules (name, condition, conclusion, priority, description, subject_area_id, else_conclusion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, cond_json, concl_json, priority, description, subject_area_id, else_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_rule_with_area(self, rule_id, name, condition, conclusion, priority=5, subject_area_id=1,
                              description="", else_conclusion=None):
        """Обновить правило с указанием предметной области"""
        # Сериализуем значения (числа в строки)
        condition_serialized = self._serialize_value(condition)
        conclusion_serialized = self._serialize_value(conclusion)

        cond_json = json.dumps(condition_serialized, ensure_ascii=False)
        concl_json = json.dumps(conclusion_serialized, ensure_ascii=False)
        else_json = json.dumps(self._serialize_value(else_conclusion), ensure_ascii=False) if else_conclusion else None

        self.cursor.execute('''
            UPDATE rules 
            SET name = ?, condition = ?, conclusion = ?, priority = ?, 
                description = ?, subject_area_id = ?, else_conclusion = ?
            WHERE id = ?
        ''', (name, cond_json, concl_json, priority, description, subject_area_id, else_json, rule_id))
        self.conn.commit()
        return rule_id

    def get_all_rules(self):
        """Получить все правила"""
        self.cursor.execute('SELECT * FROM rules ORDER BY priority DESC')
        rows = self.cursor.fetchall()

        rules = []
        for row in rows:
            condition = json.loads(row[2])
            conclusion = json.loads(row[3])
            else_concl = json.loads(row[7]) if row[7] else None

            # Десериализуем значения (строки-числа обратно в числа)
            condition = self._deserialize_value(condition)
            conclusion = self._deserialize_value(conclusion)
            else_concl = self._deserialize_value(else_concl) if else_concl else None

            rules.append({
                'id': row[0],
                'name': row[1],
                'condition': condition,
                'conclusion': conclusion,
                'priority': row[4],
                'description': row[5],
                'subject_area_id': row[6],
                'else_conclusion': else_concl
            })
        return rules

    def get_rules_by_subject_area(self, area_id):
        """Получить правила из конкретной предметной области"""
        self.cursor.execute('''
            SELECT id, name, condition, conclusion, priority, description, else_conclusion
            FROM rules 
            WHERE subject_area_id = ?
            ORDER BY priority DESC
        ''', (area_id,))
        rows = self.cursor.fetchall()

        rules = []
        for row in rows:
            condition = json.loads(row[2])
            conclusion = json.loads(row[3])
            else_concl = json.loads(row[6]) if row[6] else None

            # Десериализуем значения (строки-числа обратно в числа)
            condition = self._deserialize_value(condition)
            conclusion = self._deserialize_value(conclusion)
            else_concl = self._deserialize_value(else_concl) if else_concl else None

            rule = {
                'id': row[0],
                'name': row[1],
                'condition': condition,
                'conclusion': conclusion,
                'priority': row[4],
                'description': row[5],
                'else_conclusion': else_concl
            }
            rules.append(rule)
        return rules

    def delete_rule(self, rule_id):
        """Удалить правило"""
        self.cursor.execute('DELETE FROM rules WHERE id = ?', (rule_id,))
        self.conn.commit()

    def get_all_subject_areas(self):
        """Получить все предметные области"""
        self.cursor.execute('SELECT id, name, description FROM subject_areas ORDER BY id')
        rows = self.cursor.fetchall()
        return [{'id': row[0], 'name': row[1], 'description': row[2]} for row in rows]

    def add_subject_area(self, name, description=""):
        """Добавить новую предметную область"""
        try:
            self.cursor.execute('''
                INSERT INTO subject_areas (name, description) VALUES (?, ?)
            ''', (name, description))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def delete_subject_area(self, area_id):
        """Удалить предметную область и все ее правила"""
        self.cursor.execute('DELETE FROM rules WHERE subject_area_id = ?', (area_id,))
        self.cursor.execute('DELETE FROM subject_areas WHERE id = ?', (area_id,))
        self.conn.commit()

    def rule_name_exists_in_area(self, name, area_id, exclude_rule_id=None):
        """Проверить, существует ли правило с таким именем в предметной области"""
        if exclude_rule_id:
            self.cursor.execute('''
                SELECT COUNT(*) FROM rules 
                WHERE name = ? AND subject_area_id = ? AND id != ?
            ''', (name, area_id, exclude_rule_id))
        else:
            self.cursor.execute('''
                SELECT COUNT(*) FROM rules 
                WHERE name = ? AND subject_area_id = ?
            ''', (name, area_id))

        count = self.cursor.fetchone()[0]
        return count > 0

    def get_current_subject_area_id(self):
        """Получить ID текущей выбранной предметной области"""
        if hasattr(self, 'current_area_id') and self.current_area_id:
            self.cursor.execute('SELECT COUNT(*) FROM subject_areas WHERE id = ?', (self.current_area_id,))
            count = self.cursor.fetchone()[0]
            if count > 0:
                return self.current_area_id

        self.cursor.execute('SELECT id FROM subject_areas ORDER BY id LIMIT 1')
        row = self.cursor.fetchone()
        if row:
            self.current_area_id = row[0]
            return self.current_area_id
        return 1

    def set_current_subject_area(self, area_id):
        """Установить текущую предметную область"""
        self.current_area_id = area_id

    def delete_all_rules_in_area(self, area_id):
        """Удалить все правила в предметной области"""
        self.cursor.execute('DELETE FROM rules WHERE subject_area_id = ?', (area_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def update_rule(self, rule_id, name, condition, conclusion, priority=5, description=""):
        """Обновить существующее правило (сохраняя старую предметную область)"""
        cond_json = json.dumps(condition, ensure_ascii=False)
        concl_json = json.dumps(conclusion, ensure_ascii=False)

        self.cursor.execute('''
            UPDATE rules 
            SET name = ?, condition = ?, conclusion = ?, priority = ?, description = ?
            WHERE id = ?
        ''', (name, cond_json, concl_json, priority, description, rule_id))
        self.conn.commit()
        return rule_id

    def get_initial_facts(self, session_id):
        """Получить исходные факты для сессии (без выведенных)"""
        self.cursor.execute('''
            SELECT fact_name, fact_value FROM facts 
            WHERE session_id = ?
        ''', (session_id,))
        results = self.cursor.fetchall()
        return {row[0]: row[1] for row in results}

    def delete_all_rules(self):
        """Удалить все правила из базы данных"""
        self.cursor.execute('DELETE FROM rules')
        self.conn.commit()

    def create_subject_area_table(self):
        """Создать таблицу для предметных областей"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subject_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Проверяем, существует ли колонка subject_area_id в таблице rules
        self.cursor.execute("PRAGMA table_info(rules)")
        columns = [column[1] for column in self.cursor.fetchall()]

        if 'subject_area_id' not in columns:
            # Добавляем колонку только если её нет
            self.cursor.execute('''
                ALTER TABLE rules ADD COLUMN subject_area_id INTEGER REFERENCES subject_areas(id) DEFAULT 1
            ''')

        # Проверяем, есть ли хотя бы одна предметная область
        self.cursor.execute('SELECT COUNT(*) FROM subject_areas')
        count = self.cursor.fetchone()[0]

        if count == 0:
            # Создаем область по умолчанию
            self.cursor.execute('''
                INSERT INTO subject_areas (name, description) VALUES (?, ?)
            ''', ("Основная", "Предметная область по умолчанию"))

            # Обновляем существующие правила, чтобы они ссылались на область по умолчанию
            self.cursor.execute('''
                UPDATE rules SET subject_area_id = 1 WHERE subject_area_id IS NULL
            ''')

        self.conn.commit()
