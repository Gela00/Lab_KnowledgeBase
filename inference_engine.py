import json
import uuid
import math
import re

class InferenceEngine:
    def __init__(self, database):
        self.db = database
        self.session_id = str(uuid.uuid4())[:8]
        self.facts = {}
        self.trace = []
        self.rules = []
        self.applied_rules = set()
        self.fact_priorities = {}

    def load_rules_from_db(self):
        """Загрузить все правила из базы"""
        self.rules = self.db.get_all_rules()
        # Сортируем правила по приоритету
        self.rules.sort(key=lambda x: x['priority'], reverse=True)
        return self.rules

    def set_facts(self, facts_dict):
        """Установить исходные факты"""
        self.facts = {}
        self.fact_priorities = {}
        self.trace = []
        self.applied_rules = set()
        self.fact_sources = {}

        for fact_name, fact_value in facts_dict.items():
            # Извлекаем значение, если оно в словаре с оператором
            if isinstance(fact_value, dict):
                # Для условий с операторами (например, {"возраст": {">=": 18}})
                # В фактах мы храним конкретное значение, а не условие
                # Поэтому здесь нужно извлечь значение для сравнения
                # Но если значение - словарь с оператором, это проблема
                # В исходных фактах не должно быть операторов
                for op, val in fact_value.items():
                    # Преобразуем значение в правильный тип
                    self.facts[fact_name] = self._convert_value_type(val)
                    self.fact_sources[fact_name] = "исходный факт"
            elif isinstance(fact_value, list):
                # Для списка (может быть в будущем)
                self.facts[fact_name] = self._convert_value_type(fact_value[0]) if fact_value else ""
                self.fact_sources[fact_name] = "исходный факт"
            else:
                self.facts[fact_name] = self._convert_value_type(fact_value)
                self.fact_sources[fact_name] = "исходный факт"

        for fact_name, fact_value in self.facts.items():
            self.db.cursor.execute('''
                INSERT INTO facts (session_id, fact_name, fact_value)
                VALUES (?, ?, ?)
            ''', (self.session_id, fact_name, str(fact_value)))
        self.db.conn.commit()

    def _convert_value_type(self, value):
        """Преобразует значение в правильный тип (число или строку)"""
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # Пробуем преобразовать в число
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except (ValueError, TypeError):
                return value
        return value

    def evaluate_condition(self, condition, facts):
        """Проверить, выполняется ли условие правила"""
        for attr, condition_value in condition.items():
            # Поддержка ИЛИ
            if attr == "__or__" and isinstance(condition_value, list):
                for alternative in condition_value:
                    alt_met, alt_reason = self.evaluate_single_condition(alternative, facts)
                    if alt_met:
                        return True, ""
                return False, "ни одна из альтернатив не выполнена"

            if attr not in facts:
                return False, f"отсутствует факт: '{attr}'"

            fact_value = facts[attr]

            # Приводим fact_value к правильному типу
            fact_value_converted = self._convert_value_type(fact_value)

            if isinstance(condition_value, dict):
                for operator, target_value in condition_value.items():
                    # Приводим target_value к правильному типу
                    target_converted = self._convert_value_type(target_value)

                    result = False
                    try:
                        if operator in [">", "<", ">=", "<="]:
                            # Для числовых сравнений
                            fact_num = float(fact_value_converted)
                            target_num = float(target_converted)

                            if operator == ">":
                                result = fact_num > target_num
                            elif operator == "<":
                                result = fact_num < target_num
                            elif operator == ">=":
                                result = fact_num >= target_num
                            elif operator == "<=":
                                result = fact_num <= target_num
                        else:
                            # Для равенства и неравенства
                            if operator == "==" or operator == "=":
                                result = str(fact_value_converted) == str(target_converted)
                            elif operator == "!=":
                                result = str(fact_value_converted) != str(target_converted)
                    except (ValueError, TypeError) as e:
                        return False, f"ошибка сравнения '{attr}': {e}"

                    if not result:
                        return False, f"'{attr}' {operator} {target_converted} (текущее '{fact_value}')"
            else:
                target_converted = self._convert_value_type(condition_value)
                if str(fact_value_converted) != str(target_converted):
                    return False, f"'{attr}' = {target_converted} (текущее '{fact_value}')"

        return True, ""

    def evaluate_single_condition(self, condition, facts):
        """Проверка одного условия (без ИЛИ)"""
        for attr, condition_value in condition.items():
            if attr not in facts:
                return False, f"отсутствует факт: '{attr}'"

            fact_value = facts[attr]
            fact_value_converted = self._convert_value_type(fact_value)

            if isinstance(condition_value, dict):
                for operator, target_value in condition_value.items():
                    target_converted = self._convert_value_type(target_value)

                    result = False
                    try:
                        if operator in [">", "<", ">=", "<="]:
                            fact_num = float(fact_value_converted)
                            target_num = float(target_converted)

                            if operator == ">":
                                result = fact_num > target_num
                            elif operator == "<":
                                result = fact_num < target_num
                            elif operator == ">=":
                                result = fact_num >= target_num
                            elif operator == "<=":
                                result = fact_num <= target_num
                        else:
                            if operator == "==" or operator == "=":
                                result = str(fact_value_converted) == str(target_converted)
                            elif operator == "!=":
                                result = str(fact_value_converted) != str(target_converted)
                    except (ValueError, TypeError):
                        result = False

                    if not result:
                        return False, f"'{attr}' {operator} {target_converted} (текущее '{fact_value}')"
            else:
                target_converted = self._convert_value_type(condition_value)
                if str(fact_value_converted) != str(target_converted):
                    return False, f"'{attr}' = {target_converted} (текущее '{fact_value}')"

        return True, ""


    def get_satisfied_conditions(self, condition, facts):
        """Возвращает список выполненных условий в читаемом виде"""
        satisfied = []

        for attr, condition_value in condition.items():
            if attr not in facts:
                continue

            fact_value = facts[attr]
            fact_value_converted = self._convert_value_type(fact_value)

            if isinstance(condition_value, dict):
                for operator, target_value in condition_value.items():
                    target_converted = self._convert_value_type(target_value)

                    result = False
                    try:
                        if operator in [">", "<", ">=", "<="]:
                            fact_num = float(fact_value_converted)
                            target_num = float(target_converted)

                            if operator == ">":
                                result = fact_num > target_num
                            elif operator == "<":
                                result = fact_num < target_num
                            elif operator == ">=":
                                result = fact_num >= target_num
                            elif operator == "<=":
                                result = fact_num <= target_num
                        else:
                            if operator == "==" or operator == "=":
                                result = str(fact_value_converted) == str(target_converted)
                            elif operator == "!=":
                                result = str(fact_value_converted) != str(target_converted)
                    except (ValueError, TypeError):
                        result = False

                    if result:
                        satisfied.append(f"'{attr}' {operator} {target_converted}")
            else:
                target_converted = self._convert_value_type(condition_value)
                if str(fact_value_converted) == str(target_converted):
                    satisfied.append(f"'{attr}' = {target_converted}")

        return satisfied

    def evaluate_expression(self, expression, facts):
        """Вычисляет математическое выражение с подстановкой значений фактов"""
        if not isinstance(expression, str):
            return expression

        # Если выражение в кавычках - возвращаем как строку без кавычек
        if expression.startswith('"') and expression.endswith('"'):
            return expression[1:-1]
        if expression.startswith("'") and expression.endswith("'"):
            return expression[1:-1]

        # Заменяем переменные вида $имя или {имя} на их значения
        result_expr = expression

        # Находим все переменные в выражении
        import re
        var_pattern = r'\$([a-zA-Zа-яА-Я_][a-zA-Zа-яА-Я0-9_]*)|{([a-zA-Zа-яА-Я_][a-zA-Zа-яА-Я0-9_]*)}'

        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            if var_name in facts:
                value = facts[var_name]
                # Преобразуем в число, если возможно
                try:
                    return str(float(value))
                except (ValueError, TypeError):
                    return str(value)
            return match.group(0)

        result_expr = re.sub(var_pattern, replace_var, result_expr)

        # Пробуем вычислить математическое выражение
        try:
            # Разрешенные операции: + - * / // % **
            # Используем eval с ограничениями для безопасности
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round, "int": int, "float": float})

            # Вычисляем выражение
            result = eval(result_expr, {"__builtins__": {}}, allowed_names)
            return result
        except (SyntaxError, NameError, TypeError, ZeroDivisionError, ValueError):
            # Если не удалось вычислить, возвращаем как строку
            return result_expr

    def apply_rule(self, rule):
        """Применить правило с поддержкой ELSE, математических выражений и приоритетов"""
        new_facts = []
        rule_priority = rule['priority']
        rule_name = rule['name']

        # Получаем else_conclusion из правила (если есть)
        else_conclusion = rule.get('else_conclusion')

        # Проверяем условие правила
        condition_met, reason = self.evaluate_condition(rule['condition'], self.facts)

        # Выбираем, какое заключение применять
        if condition_met:
            conclusion_to_use = rule['conclusion']
            result_type = "THEN"
        elif else_conclusion is not None:
            # Условие не выполнено, но есть ELSE
            conclusion_to_use = else_conclusion
            result_type = "ELSE"
        else:
            # Условие не выполнено, ELSE нет — ничего не делаем
            return []

        # Применяем выбранное заключение
        for attr, value in conclusion_to_use.items():
            # Определяем фактическое значение
            if isinstance(value, str):
                # Проверяем, является ли значение математическим выражением
                # Если строка не в кавычках и содержит математические операторы
                if not (value.startswith('"') and value.endswith('"')) and \
                        not (value.startswith("'") and value.endswith("'")):
                    # Проверяем наличие математических операторов или переменных
                    if any(op in value for op in ['+', '-', '*', '/', '//', '%', '**']) or \
                            '$' in value or '{' in value and '}' in value:
                        actual_value = self.evaluate_expression(value, self.facts)
                    elif value.startswith('$'):
                        source_fact = value[1:]
                        if source_fact in self.facts:
                            actual_value = self.facts[source_fact]
                        else:
                            continue
                    elif value.startswith('{') and value.endswith('}'):
                        source_fact = value[1:-1]
                        if source_fact in self.facts:
                            actual_value = self.facts[source_fact]
                        else:
                            continue
                    else:
                        # Обычная строка (не математическое выражение)
                        actual_value = self._convert_value_type(value)
                else:
                    # Строка в кавычках - удаляем кавычки
                    actual_value = value[1:-1]
            else:
                actual_value = self._convert_value_type(value)

            # Преобразуем значение в правильный тип
            actual_value = self._convert_value_type(actual_value)

            # ПРОВЕРКА ПРИОРИТЕТА
            if attr in self.fact_priorities:
                existing_priority = self.fact_priorities[attr]
                if existing_priority > rule_priority:
                    continue
                elif existing_priority == rule_priority and attr in self.facts:
                    continue

            # ДОБАВЛЕНИЕ ИЛИ ОБНОВЛЕНИЕ ФАКТА
            if attr not in self.facts:
                self.facts[attr] = actual_value
                self.fact_priorities[attr] = rule_priority
                self.fact_sources[attr] = f"{rule_name} [{result_type}]"
                if result_type == "THEN":
                    new_facts.append(f" {attr} = {actual_value} (из основной части ТО)")
                else:
                    new_facts.append(f" {attr} = {actual_value} (из ветки ИНАЧЕ)")

            elif self.facts[attr] != actual_value:
                old_value = self.facts[attr]
                old_priority = self.fact_priorities.get(attr, 0)

                if rule_priority > old_priority:
                    self.facts[attr] = actual_value
                    self.fact_priorities[attr] = rule_priority
                    self.fact_sources[attr] = f"{rule_name} [{result_type}]"
                    if result_type == "THEN":
                        new_facts.append(f"    {attr} = {actual_value} (обновлено из ТО, было {old_value})")
                    else:
                        new_facts.append(f"    {attr} = {actual_value} (обновлено из ИНАЧЕ, было {old_value})")

        return new_facts

    def forward_chaining(self):
        """Прямой вывод с поддержкой ELSE"""
        if not self.rules:
            self.load_rules_from_db()

        initial_facts_count = len(self.facts)
        iteration = 1
        max_iterations = 20
        rules_applied = True
        global_step = 1

        self.trace = []
        self.trace.append(f"--- ПРОХОД {iteration} ---")

        while iteration <= max_iterations and rules_applied:
            rules_applied = False
            iteration_has_steps = False

            for rule in self.rules:
                condition_met, reason = self.evaluate_condition(rule['condition'], self.facts)
                else_conclusion = rule.get('else_conclusion')
                will_fire = condition_met or (else_conclusion is not None)

                if will_fire:
                    satisfied_conditions = self.get_satisfied_conditions(rule['condition'], self.facts)
                    conditions_str = ", ".join(satisfied_conditions) if satisfied_conditions else "нет"
                    new_facts = self.apply_rule(rule)

                    if condition_met:
                        fired_part = "THEN"
                    else:
                        fired_part = "ELSE"

                    if new_facts:
                        rules_applied = True
                        iteration_has_steps = True

                        formatted_facts = []
                        for fact in new_facts:
                            if " (было " in fact:
                                parts = fact.split(" (было ")
                                fact_part = parts[0]
                                old_part = parts[1].rstrip(")")
                                formatted_facts.append(f"{fact_part} (было '{old_part}')")
                            else:
                                # Убираем лишние пробелы и символы из фактов
                                clean_fact = fact.strip()
                                if clean_fact.startswith('+'):
                                    clean_fact = clean_fact[1:].strip()
                                formatted_facts.append(clean_fact)

                        self.trace.append({
                            'type': 'step_with_colors',
                            'step_num': global_step,
                            'rule_name': rule['name'],
                            'condition_met': condition_met,
                            'conditions_str': conditions_str,
                            'reason': reason,
                            'formatted_facts': formatted_facts,
                            'conclusion': self.format_conclusion(
                                rule['conclusion'] if condition_met else else_conclusion)
                        })
                        global_step += 1
                    else:
                        # Нет новых фактов - тоже добавляем шаг, но не увеличиваем счетчик для пропуска
                        iteration_has_steps = True
                        step_info = f"Шаг {global_step}. Правило '{rule['name']}' ПОДХОДИТ, но новых фактов не добавлено\n"
                        if condition_met:
                            step_info += f"   Условие выполнено: {conditions_str}\n"
                        else:
                            step_info += f"   Условие НЕ выполнено: {reason}\n"
                            step_info += f"   Выполняется ветка ИНАЧЕ (ELSE)\n"
                        self.trace.append(step_info)
                        global_step += 1
                else:
                    # Правило не подходит
                    step_info = f"Шаг {global_step}. Правило '{rule['name']}' НЕ ПОДХОДИТ\n"
                    step_info += f"   Условие не выполнено: {reason}\n"
                    self.trace.append(step_info)
                    global_step += 1

            if rules_applied and iteration_has_steps:
                iteration += 1
                if iteration <= max_iterations:
                    self.trace.append(f"\n--- ПРОХОД {iteration} ---")
            elif not rules_applied:
                break

        self.trace.append(f"\n--- СТАТИСТИКА ---")
        self.trace.append(f"* Выполнено проходов: {iteration - 1}")
        self.trace.append(f"* Добавлено новых фактов: {len(self.facts) - initial_facts_count}")
        self.trace.append(f"* Итоговое количество фактов: {len(self.facts)}")

        return self.facts, self.trace


    def backward_chaining(self, target_fact, target_value, depth=0, visited=None, trace=None, step_num=None,
                          current_pass=None):
        """Обратный вывод с пошаговой трассировкой"""
        if visited is None:
            visited = set()
        if trace is None:
            trace = []
        if step_num is None:
            step_num = [1]
        if current_pass is None:
            current_pass = [1]
            trace.append(f"\n--- ПРОХОД {current_pass[0]} ---")

        goal = f"{target_fact} = {target_value}"

        if goal in visited or depth > 10:
            return [], trace

        visited.add(goal)

        # Проверка: есть ли факт в рабочей памяти
        if target_fact in self.facts and str(self.facts[target_fact]) == str(target_value):
            source = getattr(self, 'fact_sources', {}).get(target_fact, "неизвестно")

            if source == "исходный факт":
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'ИСХОДНЫЙ_ФАКТ',
                    'message': f"Цель '{goal}' является исходным фактом (введен пользователем)"
                })
                step_num[0] += 1
                return [{
                    'type': 'fact',
                    'goal': goal,
                    'fact_name': target_fact,
                    'fact_value': target_value,
                    'is_original': True,
                    'source': source
                }], trace
            else:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'ВЫВЕДЕННЫЙ_ФАКТ',
                    'message': f"Цель '{goal}' была выведена правилом '{source}', ищем как она была получена"
                })
                step_num[0] += 1

        # Ищем правила, которые могут вывести эту цель
        matching_rules = []
        for rule in self.rules:
            conclusion = rule['conclusion']
            if target_fact in conclusion and str(conclusion[target_fact]) == str(target_value):
                matching_rules.append(rule)

        if not matching_rules:
            if target_fact in self.facts and str(self.facts[target_fact]) == str(target_value):
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'ИСХОДНЫЙ_ФАКТ',
                    'message': f"Цель '{goal}' присутствует в памяти, но нет правил для ее вывода - это исходный факт"
                })
                step_num[0] += 1
                return [{
                    'type': 'fact',
                    'goal': goal,
                    'fact_name': target_fact,
                    'fact_value': target_value,
                    'is_original': True
                }], trace
            else:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'НЕТ_ПРАВИЛ',
                    'message': f"Нет правил, которые могли бы вывести '{goal}'"
                })
                step_num[0] += 1
                return [], trace

        # Проверяем каждое подходящее правило
        for rule in matching_rules:
            trace.append({
                'step': step_num[0],
                'pass': current_pass[0],
                'goal': goal,
                'rule': rule['name'],
                'status': 'ПРОВЕРКА_ПРАВИЛА',
                'message': f"Проверка правила '{rule['name']}': может ли оно вывести '{goal}'"
            })
            step_num[0] += 1

            conditions_met = True
            sub_goals = []
            new_pass_triggered = False

            for cond_fact, cond_value in rule['condition'].items():
                cond_str = self.format_condition_item(cond_fact, cond_value)

                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'rule': rule['name'],
                    'condition': cond_str,
                    'status': 'ПРОВЕРКА_УСЛОВИЯ',
                    'message': f"Проверка условия: {cond_str}"
                })
                step_num[0] += 1

                if cond_fact in self.facts:
                    fact_value = self.facts[cond_fact]
                    condition_met = self.check_simple_condition(cond_fact, cond_value, fact_value)

                    if condition_met:
                        source = getattr(self, 'fact_sources', {}).get(cond_fact, "неизвестно")
                        source_text = f" (выведен правилом '{source}')" if source != "исходный факт" else " (исходный факт)"
                        trace.append({
                            'step': step_num[0],
                            'pass': current_pass[0],
                            'goal': goal,
                            'rule': rule['name'],
                            'condition': cond_str,
                            'status': 'УСЛОВИЕ_ВЫПОЛНЕНО',
                            'message': f"Условие '{cond_str}' выполнено: факт уже есть в памяти со значением '{fact_value}'{source_text}"
                        })
                        step_num[0] += 1
                    else:
                        trace.append({
                            'step': step_num[0],
                            'pass': current_pass[0],
                            'goal': goal,
                            'rule': rule['name'],
                            'condition': cond_str,
                            'status': 'УСЛОВИЕ_НЕ_ВЫПОЛНЕНО',
                            'message': f"Условие '{cond_str}' не выполнено: текущее значение '{fact_value}'"
                        })
                        conditions_met = False
                        step_num[0] += 1
                else:
                    # Новый проход для подцели
                    if not new_pass_triggered:
                        current_pass[0] += 1
                        new_pass_triggered = True
                        trace.append(f"\n--- ПРОХОД {current_pass[0]} ---")

                    trace.append({
                        'step': step_num[0],
                        'pass': current_pass[0],
                        'goal': goal,
                        'rule': rule['name'],
                        'condition': cond_str,
                        'status': 'НОВАЯ_ПОДЦЕЛЬ',
                        'message': f"Данных '{cond_str}' нет в памяти, факт становится новой целью"
                    })
                    step_num[0] += 1

                    if isinstance(cond_value, dict):
                        for operator2, target2 in cond_value.items():
                            sub_result, sub_trace = self.backward_chaining_with_operator(
                                cond_fact, operator2, target2, depth + 1, visited.copy(), trace, step_num, current_pass
                            )
                            trace = sub_trace
                            if sub_result:
                                sub_goals.extend(sub_result)
                                trace.append({
                                    'step': step_num[0],
                                    'pass': current_pass[0],
                                    'goal': goal,
                                    'rule': rule['name'],
                                    'condition': cond_str,
                                    'status': 'ПОДЦЕЛЬ_ПОДТВЕРЖДЕНА',
                                    'message': f"Цель '{cond_str}' подтверждена"
                                })
                                step_num[0] += 1
                            else:
                                trace.append({
                                    'step': step_num[0],
                                    'pass': current_pass[0],
                                    'goal': goal,
                                    'rule': rule['name'],
                                    'condition': cond_str,
                                    'status': 'ПОДЦЕЛЬ_НЕ_ПОДТВЕРЖДЕНА',
                                    'message': f"Цель '{cond_str}' не может быть подтверждена"
                                })
                                conditions_met = False
                                step_num[0] += 1
                    else:
                        sub_result, sub_trace = self.backward_chaining(
                            cond_fact, cond_value, depth + 1, visited.copy(), trace, step_num, current_pass
                        )
                        trace = sub_trace
                        if sub_result:
                            sub_goals.extend(sub_result)
                            trace.append({
                                'step': step_num[0],
                                'pass': current_pass[0],
                                'goal': goal,
                                'rule': rule['name'],
                                'condition': cond_str,
                                'status': 'ПОДЦЕЛЬ_ПОДТВЕРЖДЕНА',
                                'message': f"Цель '{cond_str}' подтверждена"
                            })
                            step_num[0] += 1
                        else:
                            trace.append({
                                'step': step_num[0],
                                'pass': current_pass[0],
                                'goal': goal,
                                'rule': rule['name'],
                                'condition': cond_str,
                                'status': 'ПОДЦЕЛЬ_НЕ_ПОДТВЕРЖДЕНА',
                                'message': f"Цель '{cond_str}' не может быть подтверждена"
                            })
                            conditions_met = False
                            step_num[0] += 1

            if conditions_met:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'rule': rule['name'],
                    'status': 'ПРАВИЛО_СРАБОТАЛО',
                    'message': f"Правило '{rule['name']}' подтверждает цель '{goal}'"
                })
                step_num[0] += 1
                return [{
                    'type': 'rule',
                    'goal': goal,
                    'rule_name': rule['name'],
                    'sub_goals': sub_goals
                }], trace
            else:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'rule': rule['name'],
                    'status': 'ПРАВИЛО_НЕ_СРАБОТАЛО',
                    'message': f"Правило '{rule['name']}' не может подтвердить '{goal}': не все условия выполнены"
                })
                step_num[0] += 1

        return [], trace

    def backward_chaining_with_operator(self, target_fact, operator, target_value, depth=0, visited=None, trace=None,
                                        step_num=None, current_pass=None):
        """Обратный вывод для условий с операторами сравнения"""
        if visited is None:
            visited = set()
        if trace is None:
            trace = []
        if step_num is None:
            step_num = [1]
        if current_pass is None:
            current_pass = [1]
            trace.append(f"\n--- ПРОХОД {current_pass[0]} ---")

        goal = f"{target_fact} {operator} {target_value}"

        if goal in visited or depth > 10:
            return [], trace

        visited.add(goal)

        # Проверяем, есть ли факт в рабочей памяти
        if target_fact in self.facts:
            fact_value = self.facts[target_fact]
            condition_met = self.check_operator_condition(fact_value, operator, target_value)

            if condition_met:
                source = getattr(self, 'fact_sources', {}).get(target_fact, "неизвестно")
                source_text = f" (выведен правилом '{source}')" if source != "исходный факт" else " (исходный факт)"
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'НАЙДЕН_В_ПАМЯТИ',
                    'message': f"Цель '{goal}' подтверждена: в памяти есть '{target_fact}' = '{fact_value}'{source_text}"
                })
                step_num[0] += 1
                return [{
                    'type': 'fact',
                    'goal': goal,
                    'fact_name': target_fact,
                    'fact_value': fact_value,
                    'is_original': source == "исходный факт"
                }], trace
            else:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'status': 'НЕ_ВЫПОЛНЕНО',
                    'message': f"Цель '{goal}' не выполнена: '{target_fact}' = '{fact_value}'"
                })
                step_num[0] += 1
                return [], trace

        # Ищем правила, которые могут вывести это условие
        matching_rules = []
        for rule in self.rules:
            conclusion = rule['conclusion']
            if target_fact in conclusion:
                rule_value = conclusion[target_fact]
                if self.check_operator_condition(rule_value, operator, target_value):
                    matching_rules.append(rule)

        if not matching_rules:
            trace.append({
                'step': step_num[0],
                'pass': current_pass[0],
                'goal': goal,
                'status': 'НЕТ_ПРАВИЛ',
                'message': f"Нет правил, которые могли бы вывести условие '{goal}'"
            })
            step_num[0] += 1
            return [], trace

        for rule in matching_rules:
            trace.append({
                'step': step_num[0],
                'pass': current_pass[0],
                'goal': goal,
                'rule': rule['name'],
                'status': 'ПРОВЕРКА_ПРАВИЛА',
                'message': f"Проверка правила '{rule['name']}': может ли оно вывести '{goal}'"
            })
            step_num[0] += 1

            conditions_met = True
            sub_goals = []
            new_pass_triggered = False

            for cond_fact, cond_value in rule['condition'].items():
                cond_str = self.format_condition_item(cond_fact, cond_value)

                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'rule': rule['name'],
                    'condition': cond_str,
                    'status': 'ПРОВЕРКА_УСЛОВИЯ',
                    'message': f"Проверка условия: {cond_str}"
                })
                step_num[0] += 1

                if cond_fact in self.facts:
                    fact_value = self.facts[cond_fact]
                    condition_met = self.check_simple_condition(cond_fact, cond_value, fact_value)

                    if condition_met:
                        source = getattr(self, 'fact_sources', {}).get(cond_fact, "неизвестно")
                        source_text = f" (выведен правилом '{source}')" if source != "исходный факт" else " (исходный факт)"
                        trace.append({
                            'step': step_num[0],
                            'pass': current_pass[0],
                            'goal': goal,
                            'rule': rule['name'],
                            'condition': cond_str,
                            'status': 'УСЛОВИЕ_ВЫПОЛНЕНО',
                            'message': f"Условие '{cond_str}' выполнено: факт уже есть в памяти со значением '{fact_value}'{source_text}"
                        })
                        step_num[0] += 1
                    else:
                        trace.append({
                            'step': step_num[0],
                            'pass': current_pass[0],
                            'goal': goal,
                            'rule': rule['name'],
                            'condition': cond_str,
                            'status': 'УСЛОВИЕ_НЕ_ВЫПОЛНЕНО',
                            'message': f"Условие '{cond_str}' не выполнено: текущее значение '{fact_value}'"
                        })
                        conditions_met = False
                        step_num[0] += 1
                else:
                    if not new_pass_triggered:
                        current_pass[0] += 1
                        new_pass_triggered = True
                        trace.append(f"\n--- ПРОХОД {current_pass[0]} ---")

                    trace.append({
                        'step': step_num[0],
                        'pass': current_pass[0],
                        'goal': goal,
                        'rule': rule['name'],
                        'condition': cond_str,
                        'status': 'НОВАЯ_ПОДЦЕЛЬ',
                        'message': f"Данных '{cond_str}' нет в памяти, факт становится новой целью"
                    })
                    step_num[0] += 1

                    if isinstance(cond_value, dict):
                        for operator2, target2 in cond_value.items():
                            sub_result, sub_trace = self.backward_chaining_with_operator(
                                cond_fact, operator2, target2, depth + 1, visited.copy(), trace, step_num, current_pass
                            )
                            trace = sub_trace
                            if sub_result:
                                sub_goals.extend(sub_result)
                                trace.append({
                                    'step': step_num[0],
                                    'pass': current_pass[0],
                                    'goal': goal,
                                    'rule': rule['name'],
                                    'condition': cond_str,
                                    'status': 'ПОДЦЕЛЬ_ПОДТВЕРЖДЕНА',
                                    'message': f"Цель '{cond_str}' подтверждена"
                                })
                                step_num[0] += 1
                            else:
                                trace.append({
                                    'step': step_num[0],
                                    'pass': current_pass[0],
                                    'goal': goal,
                                    'rule': rule['name'],
                                    'condition': cond_str,
                                    'status': 'ПОДЦЕЛЬ_НЕ_ПОДТВЕРЖДЕНА',
                                    'message': f"Цель '{cond_str}' не может быть подтверждена"
                                })
                                conditions_met = False
                                step_num[0] += 1
                    else:
                        sub_result, sub_trace = self.backward_chaining(
                            cond_fact, cond_value, depth + 1, visited.copy(), trace, step_num, current_pass
                        )
                        trace = sub_trace
                        if sub_result:
                            sub_goals.extend(sub_result)
                            trace.append({
                                'step': step_num[0],
                                'pass': current_pass[0],
                                'goal': goal,
                                'rule': rule['name'],
                                'condition': cond_str,
                                'status': 'ПОДЦЕЛЬ_ПОДТВЕРЖДЕНА',
                                'message': f"Цель '{cond_str}' подтверждена"
                            })
                            step_num[0] += 1
                        else:
                            trace.append({
                                'step': step_num[0],
                                'pass': current_pass[0],
                                'goal': goal,
                                'rule': rule['name'],
                                'condition': cond_str,
                                'status': 'ПОДЦЕЛЬ_НЕ_ПОДТВЕРЖДЕНА',
                                'message': f"Цель '{cond_str}' не может быть подтверждена"
                            })
                            conditions_met = False
                            step_num[0] += 1

            if conditions_met:
                trace.append({
                    'step': step_num[0],
                    'pass': current_pass[0],
                    'goal': goal,
                    'rule': rule['name'],
                    'status': 'ПРАВИЛО_СРАБОТАЛО',
                    'message': f"Правило '{rule['name']}' подтверждает цель '{goal}'"
                })
                step_num[0] += 1
                return [{
                    'type': 'rule',
                    'goal': goal,
                    'rule_name': rule['name'],
                    'sub_goals': sub_goals
                }], trace

        return [], trace

    def check_simple_condition(self, cond_fact, cond_value, fact_value):
        """Проверяет простое условие"""
        fact_value_converted = self._convert_value_type(fact_value)

        if isinstance(cond_value, dict):
            for operator, target in cond_value.items():
                return self.check_operator_condition(fact_value_converted, operator, target)
        else:
            target_converted = self._convert_value_type(cond_value)
            return str(fact_value_converted) == str(target_converted)

    def check_operator_condition(self, fact_value, operator, target_value):
        """Проверяет условие с оператором"""
        # Преобразуем значения для сравнения
        try:
            fact_num = float(fact_value) if not isinstance(fact_value, (int, float)) else float(fact_value)
            target_num = float(target_value) if not isinstance(target_value, (int, float)) else float(target_value)

            if operator == ">":
                return fact_num > target_num
            elif operator == "<":
                return fact_num < target_num
            elif operator == ">=":
                return fact_num >= target_num
            elif operator == "<=":
                return fact_num <= target_num
            elif operator == "==" or operator == "=":
                return fact_num == target_num
            elif operator == "!=":
                return fact_num != target_num
        except (ValueError, TypeError):
            # Если не числа, сравниваем как строки
            if operator in [">", "<", ">=", "<="]:
                return False
            elif operator == "==" or operator == "=":
                return str(fact_value) == str(target_value)
            elif operator == "!=":
                return str(fact_value) != str(target_value)

        return False

    def format_conclusion(self, conclusion):
        """Форматирует заключение для отображения"""
        if not conclusion:
            return ""
        parts = [f"{key} = {value}" for key, value in conclusion.items()]
        return "; ".join(parts)

    def format_condition_item(self, cond_fact, cond_value):
        """Форматирует одно условие для отображения"""
        if isinstance(cond_value, dict):
            for operator, target in cond_value.items():
                return f"{cond_fact} {operator} {target}"
        else:
            return f"{cond_fact} = {cond_value}"

    def format_backward_trace(self, trace, goal):
        """Форматирует трассировку обратного вывода для отображения"""
        result = f"Подтверждение цели \"{goal}\":\n\n"

        for item in trace:
            if isinstance(item, str):
                result += f"{item}\n"
            elif isinstance(item, dict):
                step = item.get('step', '?')
                pass_num = item.get('pass', '?')
                status = item.get('status', '')
                message = item.get('message', '')

                if status == 'ИСХОДНЫЙ_ФАКТ':
                    result += f"Шаг {step}. {message}\n"
                    result += f"\n--- ИТОГО ---\n"
                    result += f"Цель \"{goal}\" является исходным фактом.\n"
                    return result
                elif status == 'ВЫВЕДЕННЫЙ_ФАКТ':
                    result += f"Шаг {step}. {message}\n"
                elif status == 'ПРОВЕРКА_ПРАВИЛА':
                    result += f"\nШаг {step}. {message}\n"
                elif status == 'ПРОВЕРКА_УСЛОВИЯ':
                    result += f"Шаг {step}. {message}\n"
                elif status == 'НОВАЯ_ПОДЦЕЛЬ':
                    result += f"Шаг {step}. {message}\n"
                elif status == 'УСЛОВИЕ_ВЫПОЛНЕНО':
                    result += f"Шаг {step}. ✓ {message}\n"
                elif status == 'УСЛОВИЕ_НЕ_ВЫПОЛНЕНО':
                    result += f"Шаг {step}. ✗ {message}\n"
                elif status == 'ПОДЦЕЛЬ_ПОДТВЕРЖДЕНА':
                    result += f"Шаг {step}. ✓ {message}\n"
                elif status == 'ПОДЦЕЛЬ_НЕ_ПОДТВЕРЖДЕНА':
                    result += f"Шаг {step}. ✗ {message}\n"
                elif status == 'НАЙДЕН_В_ПАМЯТИ':
                    result += f"Шаг {step}. ✓ {message}\n"
                elif status == 'НЕ_ВЫПОЛНЕНО':
                    result += f"Шаг {step}. ✗ {message}\n"
                elif status == 'ПРАВИЛО_СРАБОТАЛО':
                    result += f"Шаг {step}. ✓ {message}\n"
                    result += f"\n--- ИТОГО ---\n"
                    result += f"Цель \"{goal}\" подтверждена с помощью правил.\n"
                elif status == 'ПРАВИЛО_НЕ_СРАБОТАЛО':
                    result += f"Шаг {step}. ✗ {message}\n"
                elif status == 'НЕТ_ПРАВИЛ':
                    result += f"Шаг {step}. {message}\n"

        return result

    def format_explanation(self, explanations, depth=0):
        """Форматирует объяснение"""
        result = ""
        indent = "  " * depth

        rule_based = [e for e in explanations if e.get('rule_based', False)]
        original = [e for e in explanations if e.get('is_original', False)]

        rule_based.sort(key=lambda x: x.get('depth', 0))

        for exp in rule_based:
            exp_indent = "  " * exp.get('depth', 0)
            result += f"{exp_indent}Правило: {exp['rule']}\n"
            result += f"{exp_indent}Доказывает: {exp['goal']}\n"

            for cond in exp['conditions']:
                result += f"{exp_indent}* {cond['fact']}: {cond['status']}\n"

            if exp['all_met']:
                result += f"{exp_indent}Все условия выполнены\n"
            else:
                result += f"{exp_indent}Не все условия выполнены\n"
            result += f"{exp_indent}{'-' * 30}\n\n"

        for exp in original:
            exp_indent = "  " * exp.get('depth', 0)
            result += f"{exp_indent}Исходный факт: {exp['goal']}\n"
            result += f"{exp_indent}{'-' * 30}\n\n"

        return result

    def load_rules_from_area(self, area_id):
        """Загрузить правила из конкретной предметной области"""
        self.rules = self.db.get_rules_by_subject_area(area_id)
        self.rules.sort(key=lambda x: x['priority'], reverse=True)
        return self.rules