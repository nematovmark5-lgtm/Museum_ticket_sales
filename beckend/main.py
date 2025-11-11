import sys
import mysql.connector
import random
import json
from datetime import datetime, timedelta, date
from mysql.connector import Error
import webview
import threading
import http.server
import socketserver
import os
import time


class DatabaseManager:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'Mark',
            'password': '0987654321',
            'database': 'museum_system',
            'port': 3306,
            'autocommit': True
        }
        self.conn = None
        self.connect()

    def connect(self):
        try:
            if self.conn and self.conn.is_connected():
                self.conn.close()

            self.conn = mysql.connector.connect(**self.config)
            print("Успешное подключение к БД")
            return True
        except Error as e:
            print(f"Ошибка подключения к БД: {e}")
            return False

    def get_connection(self):
        try:
            if self.conn is None or not self.conn.is_connected():
                print("Переподключение к БД...")
                self.connect()
            return self.conn
        except Error as e:
            print(f"Ошибка получения соединения: {e}")
            return None

    def execute_query(self, query, params=None, fetch=False):
        conn = self.get_connection()
        if not conn:
            raise Exception("Нет соединения с базой данных")

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall()
                serializable_result = []
                for row in result:
                    serializable_row = {}
                    for key, value in row.items():
                        if hasattr(value, '__class__') and 'Decimal' in str(value.__class__):
                            serializable_row[key] = float(value)
                        elif isinstance(value, (datetime, date)):
                            serializable_row[key] = value.isoformat()
                        elif isinstance(value, timedelta):
                            serializable_row[key] = str(value)
                        elif isinstance(value, bytes):
                            serializable_row[key] = value.decode('utf-8', errors='ignore')
                        else:
                            serializable_row[key] = value
                    serializable_result.append(serializable_row)
                return serializable_result
            else:
                conn.commit()
                return cursor.rowcount if cursor else 0

        except Error as e:
            print(f"Ошибка выполнения запроса: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def authenticate_museum(self, code, password):
        try:
            result = self.execute_query(
                "SELECT code, name, ticket_price FROM museums WHERE code = %s AND password = %s",
                (code, password),
                fetch=True
            )
            return result[0] if result else None
        except Exception as e:
            print(f"Ошибка аутентификации: {e}")
            return None

    def register_visitor(self, name, phone=None, surname=None, email=None, login=None, password=None):
        try:
            actual_login = email if email else login

            # Проверяем, существует ли уже посетитель с таким email/логином
            existing_visitor = self.execute_query(
                "SELECT id FROM visitors WHERE login = %s",
                (actual_login,),
                fetch=True
            ) if actual_login else None

            if existing_visitor:
                return existing_visitor[0]['id']

            # Если посетителя нет, создаем нового
            result = self.execute_query(
                "INSERT INTO visitors (name, phone, surname, login, password) VALUES (%s, %s, %s, %s, %s)",
                (name, phone, surname, actual_login, password)
            )

            # Получаем ID нового посетителя
            if result:
                new_visitor = self.execute_query(
                    "SELECT id FROM visitors WHERE login = %s ORDER BY id DESC LIMIT 1",
                    (actual_login,),
                    fetch=True
                ) if actual_login else self.execute_query(
                    "SELECT id FROM visitors ORDER BY id DESC LIMIT 1",
                    fetch=True
                )
                return new_visitor[0]['id'] if new_visitor else None
            return None
        except Error as e:
            print(f"Ошибка регистрации посетителя: {e}")
            return None

    def create_single_ticket(self, museum_code, visitor_id, ticket_type, price, visit_date, visit_time):
        """Создает один билет с уникальным номером"""
        try:
            ticket_number = f"T{int(datetime.now().timestamp() * 1000)}{random.randint(1000, 9999)}"

            result = self.execute_query(
                """INSERT INTO tickets (ticket_number, visitor_id, ticket_type, price, museum_code, 
                visit_date, visit_time, quantity, status) VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'offline')""",
                (ticket_number, visitor_id, ticket_type, float(price), museum_code,
                 visit_date, visit_time)
            )

            if result:
                print(f"Билет создан: {ticket_number}")
                return {
                    'ticket_number': ticket_number,
                    'visitor_id': visitor_id,
                    'ticket_type': ticket_type,
                    'price': price,
                    'visit_date': visit_date,
                    'visit_time': visit_time,
                    'quantity': 1,
                    'status': 'offline'
                }
            return None
        except Error as e:
            print(f"Ошибка создания билета: {e}")
            return None

    def create_multiple_tickets(self, museum_code, visitor_id, tickets_data, visit_date, visit_time):
        """Создает несколько билетов с разными типами"""
        try:
            created_tickets = []
            total_price = 0

            for ticket_data in tickets_data:
                ticket_type = ticket_data['type']
                price = ticket_data['price']

                # Создаем отдельный билет для каждого типа
                ticket = self.create_single_ticket(
                    museum_code, visitor_id, ticket_type, price, visit_date, visit_time
                )

                if ticket:
                    created_tickets.append(ticket)
                    total_price += price

            # Обновляем статистику продаж
            if created_tickets:
                museum_id_result = self.execute_query(
                    "SELECT id FROM museums WHERE code = %s",
                    (museum_code,),
                    fetch=True
                )

                if museum_id_result:
                    museum_id = museum_id_result[0]['id']
                    self.execute_query(
                        """INSERT INTO sales (museums_id, quantity_tickets_sold, income, date, status) 
                        VALUES (%s, %s, %s, %s, 'offline')""",
                        (museum_id, len(created_tickets), float(total_price), visit_date)
                    )

            return created_tickets
        except Error as e:
            print(f"Ошибка создания нескольких билетов: {e}")
            return []

    def get_tickets_by_museum(self, museum_code, hide_checked=True):
        try:
            if hide_checked:
                result = self.execute_query("""
                    SELECT t.ticket_number, v.name, v.surname, v.login as email, v.phone, t.ticket_type, t.price, t.issued_at, 
                           t.visit_date, t.visit_time, t.quantity, t.museum_code, t.status, t.`check`, t.reason
                    FROM tickets t 
                    JOIN visitors v ON t.visitor_id = v.id 
                    WHERE t.museum_code = %s AND (t.`check` IS NULL OR t.`check` != 'проверено')
                    ORDER BY t.issued_at DESC
                """, (museum_code,), fetch=True)
            else:
                result = self.execute_query("""
                    SELECT t.ticket_number, v.name, v.surname, v.login as email, v.phone, t.ticket_type, t.price, t.issued_at, 
                           t.visit_date, t.visit_time, t.quantity, t.museum_code, t.status, t.`check`, t.reason
                    FROM tickets t 
                    JOIN visitors v ON t.visitor_id = v.id 
                    WHERE t.museum_code = %s 
                    ORDER BY t.issued_at DESC
                """, (museum_code,), fetch=True)
            return result
        except Exception as e:
            print(f"Ошибка получения билетов: {e}")
            return []

    def search_tickets(self, museum_code, search_term):
        try:
            result = self.execute_query("""
                SELECT t.ticket_number, v.name, v.surname, v.login as email, v.phone, t.ticket_type, t.price, t.issued_at, 
                       t.visit_date, t.visit_time, t.quantity, t.museum_code, t.status, t.`check`, t.reason
                FROM tickets t 
                JOIN visitors v ON t.visitor_id = v.id 
                WHERE t.museum_code = %s AND (t.`check` IS NULL OR t.`check` != 'проверено')
                AND (t.ticket_number LIKE %s 
                    OR v.name LIKE %s 
                    OR v.surname LIKE %s 
                    OR t.ticket_type LIKE %s 
                    OR CAST(t.price AS CHAR) LIKE %s)
                ORDER BY t.issued_at DESC
            """, (museum_code, f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%',
                  f'%{search_term}%'), fetch=True)

            return result
        except Exception as e:
            print(f"Ошибка поиска билетов: {e}")
            return []

    def get_time_slots(self, museum_code, date_str):
        try:
            result = self.execute_query("""
                SELECT id, museum_code, date, start_time, end_time, available_tickets
                FROM time_slots 
                WHERE museum_code = %s AND date = %s AND available_tickets > 0
                ORDER BY start_time
            """, (museum_code, date_str), fetch=True)

            if not result:
                result = self.create_standard_slots(museum_code, date_str)

            return result
        except Exception as e:
            print(f"Ошибка получения временных слотов: {e}")
            return []

    def create_standard_slots(self, museum_code, date_str):
        try:
            standard_slots = [
                ("10:00:00", "12:00:00", 5),
                ("12:00:00", "14:00:00", 5),
                ("14:00:00", "16:00:00", 5),
                ("16:00:00", "18:00:00", 5)
            ]

            for start_time, end_time, available in standard_slots:
                self.execute_query("""
                    INSERT INTO time_slots (museum_code, date, start_time, end_time, available_tickets)
                    VALUES (%s, %s, %s, %s, %s)
                """, (museum_code, date_str, start_time, end_time, available))

            result = self.execute_query("""
                SELECT id, museum_code, date, start_time, end_time, available_tickets
                FROM time_slots 
                WHERE museum_code = %s AND date = %s
                ORDER BY start_time
            """, (museum_code, date_str), fetch=True)

            return result
        except Error as e:
            print(f"Ошибка создания слотов: {e}")
            return []

    def reserve_time_slot(self, museum_code, date_str, start_time, quantity):
        try:
            slot_result = self.execute_query("""
                SELECT id, available_tickets 
                FROM time_slots 
                WHERE museum_code = %s AND date = %s AND start_time = %s
            """, (museum_code, date_str, start_time), fetch=True)

            if not slot_result:
                return {'success': False, 'error': 'Временной слот не найден'}

            slot = slot_result[0]
            available_tickets = slot['available_tickets']

            if available_tickets < quantity:
                return {
                    'success': False,
                    'error': f'Недостаточно билетов. Доступно: {available_tickets}, запрошено: {quantity}'
                }

            self.execute_query("""
                UPDATE time_slots 
                SET available_tickets = available_tickets - %s 
                WHERE id = %s
            """, (quantity, slot['id']))

            return {
                'success': True,
                'reserved_quantity': quantity,
                'remaining_tickets': available_tickets - quantity
            }

        except Error as e:
            print(f"Ошибка бронирования слота: {e}")
            return {'success': False, 'error': f'Database error: {str(e)}'}

    def update_ticket_check(self, ticket_number, check_status, reason=None):
        try:
            result = self.execute_query(
                "UPDATE tickets SET `check` = %s, reason = %s WHERE ticket_number = %s",
                (check_status, reason, ticket_number)
            )

            return {'success': True}
        except Error as e:
            print(f"Ошибка обновления статуса проверки билета: {e}")
            return {'success': False, 'error': str(e)}

    def get_available_tickets_count(self, museum_code, date_str, start_time):
        """Получает количество доступных билетов в указанном слоте"""
        try:
            result = self.execute_query("""
                SELECT available_tickets 
                FROM time_slots 
                WHERE museum_code = %s AND date = %s AND start_time = %s
            """, (museum_code, date_str, start_time), fetch=True)

            return result[0]['available_tickets'] if result else 0
        except Exception as e:
            print(f"Ошибка получения доступных билетов: {e}")
            return 0


class MuseumAPI:
    def __init__(self):
        self.db = DatabaseManager()
        self.current_museum = None

    def authenticate(self, code, password):
        try:
            museum = self.db.authenticate_museum(code, password)
            if museum:
                self.current_museum = museum
                return {'success': True, 'museum': museum}
            else:
                return {'success': False, 'error': 'Неверный код или пароль'}
        except Exception as e:
            print(f"Ошибка аутентификации: {e}")
            return {'success': False, 'error': 'Ошибка подключения к базе данных'}

    def get_time_slots(self, date):
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            slots = self.db.get_time_slots(self.current_museum['code'], date)
            return {'success': True, 'slots': slots}
        except Exception as e:
            print(f"Ошибка получения слотов: {e}")
            return {'success': False, 'error': 'Ошибка получения данных'}

    def get_available_tickets(self, date, start_time):
        """Получает количество доступных билетов для выбранного слота"""
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            available = self.db.get_available_tickets_count(
                self.current_museum['code'], date, start_time
            )
            return {'success': True, 'available_tickets': available}
        except Exception as e:
            print(f"Ошибка получения доступных билетов: {e}")
            return {'success': False, 'error': 'Ошибка получения данных'}

    def calculate_ticket_price(self, ticket_type, quantity=1):
        """Рассчитывает цену для одного билета определенного типа"""
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        base_price = float(self.current_museum['ticket_price'])
        multipliers = {
            'Стандартный': 1.0,
            'Льготный': 0.6,
            'Детский': 0.4,
            'Студенческий': 0.5,
            'Пенсионный': 0.4
        }
        result = base_price * multipliers.get(ticket_type, 1.0) * quantity
        return {'success': True, 'price': round(result, 2)}

    def create_tickets(self, visitor_data, tickets_data, time_slot_data):
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            if not visitor_data.get('name'):
                return {'success': False, 'error': 'Заполните поле "Имя"'}

            if not tickets_data:
                return {'success': False, 'error': 'Добавьте хотя бы один билет'}

            visitor_id = self.db.register_visitor(
                visitor_data['name'],
                visitor_data.get('phone'),
                visitor_data.get('surname'),
                visitor_data.get('email'),
                visitor_data.get('login'),
                visitor_data.get('password')
            )

            if not visitor_id:
                return {'success': False, 'error': 'Ошибка регистрации посетителя'}

            total_quantity = len(tickets_data)

            reserve_result = self.db.reserve_time_slot(
                self.current_museum['code'],
                time_slot_data['date'],
                time_slot_data['start_time'],
                total_quantity
            )

            if not reserve_result['success']:
                return {'success': False, 'error': reserve_result['error']}

            # Создаем отдельные билеты для каждого типа
            result = self.db.create_multiple_tickets(
                self.current_museum['code'],
                visitor_id,
                tickets_data,
                time_slot_data['date'],
                time_slot_data['start_time']
            )

            if result:
                return {
                    'success': True,
                    'tickets': result,
                    'total_tickets': len(result)
                }
            else:
                return {'success': False, 'error': 'Ошибка создания билетов'}
        except Exception as e:
            print(f"Ошибка создания билетов: {e}")
            return {'success': False, 'error': 'Ошибка базы данных'}

    def get_tickets(self):
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            tickets = self.db.get_tickets_by_museum(self.current_museum['code'])
            return {'success': True, 'tickets': tickets}
        except Exception as e:
            print(f"Ошибка получения билетов: {e}")
            return {'success': False, 'error': 'Ошибка получения данных'}

    def search_tickets(self, search_term):
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            tickets = self.db.search_tickets(self.current_museum['code'], search_term)
            return {'success': True, 'tickets': tickets}
        except Exception as e:
            print(f"Ошибка поиска билетов: {e}")
            return {'success': False, 'error': 'Ошибка поиска'}

    def update_ticket_check(self, ticket_number, check_status, reason=None):
        if not self.current_museum:
            return {'success': False, 'error': 'Не авторизован'}

        try:
            result = self.db.update_ticket_check(ticket_number, check_status, reason)
            return result
        except Exception as e:
            print(f"Ошибка обновления статуса проверки билета: {e}")
            return {'success': False, 'error': str(e)}

    def logout(self):
        self.current_museum = None
        return {'success': True}


HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Музейная система</title>
    <style>
        :root {
            --primary: #0da2e7;
            --primary-dark: #0b8bc7;
            --primary-light: #e0f2fe;
            --secondary: #2c3e50;
            --accent: #34495e;
            --background: #f8fafc;
            --surface: #ffffff;
            --text: #1a1a1a;
            --text-light: #6b7280;
            --border: #e5e7eb;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        .app-container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Header */
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }

        .museum-info {
            font-weight: 600;
            color: var(--secondary);
        }

        .last-update {
            font-size: 0.8rem;
            color: var(--text-light);
            margin-top: 0.25rem;
        }

        .logout-btn {
            background: var(--error);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .logout-btn:hover {
            background: #dc2626;
            transform: translateY(-1px);
        }

        /* Main Content */
        .main-content {
            flex: 1;
            padding: 2rem;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }

        .content-wrapper {
            width: 100%;
            max-width: 1200px;
        }

        /* Login Screen */
        .login-screen {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 70vh;
        }

        .login-card {
            background: var(--surface);
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 440px;
            border: 1px solid var(--border);
        }

        .login-title {
            text-align: center;
            margin-bottom: 2rem;
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--secondary);
        }

        /* Tabs */
        .tabs-container {
            background: var(--surface);
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            border: 1px solid var(--border);
        }

        .tabs-header {
            display: flex;
            background: var(--secondary);
            border-bottom: 1px solid var(--border);
        }

        .tab {
            flex: 1;
            padding: 1.25rem 2rem;
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            font-size: 1rem;
        }

        .tab:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .tab.active {
            background: var(--primary);
        }

        .tab-content {
            display: none;
            padding: 2.5rem;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Cards */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .card-header {
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--secondary);
            margin-bottom: 0.5rem;
        }

        /* Forms */
        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-label {
            display: block;
            margin-bottom: 0.75rem;
            font-weight: 600;
            color: var(--secondary);
        }

        .form-control {
            width: 100%;
            padding: 1rem 1.25rem;
            border: 2px solid var(--border);
            border-radius: 10px;
            font-size: 1rem;
            transition: all 0.3s ease;
            background: var(--surface);
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(13, 162, 231, 0.1);
        }

        .optional-label {
            color: var(--text-light);
            font-weight: 500;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            padding: 1rem 2rem;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(13, 162, 231, 0.3);
        }

        .btn-secondary {
            background: var(--accent);
            color: white;
        }

        .btn-secondary:hover {
            background: var(--secondary);
            transform: translateY(-2px);
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .btn-success:hover {
            background: #0da271;
            transform: translateY(-2px);
        }

        .btn-danger {
            background: var(--error);
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
            transform: translateY(-2px);
        }

        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }

        .btn-full {
            width: 100%;
        }

        /* Time Slots */
        .time-slots {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }

        .time-slot {
            padding: 1.25rem;
            border: 2px solid var(--border);
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: var(--surface);
        }

        .time-slot:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
        }

        .time-slot.selected {
            border-color: var(--primary);
            background: var(--primary-light);
            transform: translateY(-2px);
        }

        .time-slot-time {
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--secondary);
            margin-bottom: 0.5rem;
        }

        .time-slot-available {
            font-size: 0.9rem;
            color: var(--text-light);
        }

        /* Tables - Компактный стиль */
        .table-container {
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .table {
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            font-size: 0.85rem;
        }

        .table th,
        .table td {
            padding: 0.6rem 0.8rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }

        .table th {
            background: var(--secondary);
            color: white;
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .table tr:hover {
            background: var(--primary-light);
        }

        .table tr.search-highlight {
            background: #e0f2fe !important;
            border-left: 3px solid var(--primary);
        }

        .status-badge {
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-online {
            background: #d1fae5;
            color: #065f46;
        }

        .status-offline {
            background: #fef3c7;
            color: #92400e;
        }

        .action-buttons {
            display: flex;
            gap: 0.3rem;
        }

        .reason-select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-top: 0.5rem;
        }

        /* Alerts */
        .alert {
            padding: 1.25rem 1.5rem;
            border-radius: 10px;
            margin: 1.5rem 0;
            border-left: 4px solid;
        }

        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border-left-color: var(--success);
        }

        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border-left-color: var(--error);
        }

        .alert-info {
            background: #dbeafe;
            color: #1e40af;
            border-left-color: #3b82f6;
        }

        .alert-warning {
            background: #fef3c7;
            color: #92400e;
            border-left-color: var(--warning);
        }

        /* Loading */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top: 3px solid currentColor;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Price Display */
        .price-display {
            font-size: 2rem;
            font-weight: 800;
            color: var(--primary);
            text-align: center;
            margin: 1rem 0;
        }

        /* Form Row */
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        /* Search Section */
        .search-section {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
            margin-bottom: 1.5rem;
        }

        .search-input-container {
            flex: 1;
        }

        /* Utility Classes */
        .text-center { text-align: center; }
        .mt-2 { margin-top: 2rem; }
        .mb-2 { margin-bottom: 2rem; }
        .hidden { display: none; }
        .required-field::after {
            content: " *";
            color: var(--error);
        }

        /* Ticket List Styles */
        .ticket-list {
            margin: 1.5rem 0;
        }

        .ticket-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            border: 2px solid var(--border);
            border-radius: 10px;
            margin-bottom: 1rem;
            background: var(--surface);
        }

        .ticket-item:last-child {
            margin-bottom: 0;
        }

        .ticket-type-select {
            flex: 1;
        }

        .ticket-price {
            font-weight: 600;
            color: var(--primary);
            min-width: 80px;
            text-align: right;
        }

        .remove-ticket {
            background: var(--error);
            color: white;
            border: none;
            border-radius: 6px;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .remove-ticket:hover {
            background: #dc2626;
            transform: scale(1.1);
        }

        .add-ticket-btn {
            background: var(--success);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .add-ticket-btn:hover {
            background: #0da271;
            transform: translateY(-2px);
        }

        .ticket-counter {
            font-size: 0.9rem;
            color: var(--text-light);
            margin-bottom: 1rem;
        }

        .ticket-counter.limit-reached {
            color: var(--error);
            font-weight: bold;
        }

        .ticket-counter.near-limit {
            color: var(--warning);
        }

        .availability-info {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-weight: 600;
        }

        .availability-warning {
            background: #fef3c7;
            color: #92400e;
            border-left: 4px solid var(--warning);
        }

        .availability-error {
            background: #fee2e2;
            color: #991b1b;
            border-left: 4px solid var(--error);
        }

        .availability-success {
            background: #d1fae5;
            color: #065f46;
            border-left: 4px solid var(--success);
        }
    </style>
</head>
<body>
    <div class="app-container">
        <header class="header">
            <div class="header-content">
                <div class="logo">
                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"></path>
                        <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"></path>
                        <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"></path>
                        <path d="M10 6h4"></path>
                        <path d="M10 10h4"></path>
                        <path d="M10 14h4"></path>
                        <path d="M10 18h4"></path>
                    </svg>
                    <span>Музейная система</span>
                </div>
                <div>
                    <div id="museum-info-header" class="museum-info"></div>
                    <div id="last-update-header" class="last-update"></div>
                </div>
                <button id="logout-btn" class="logout-btn hidden" onclick="logout()">Выйти</button>
            </div>
        </header>

        <main class="main-content">
            <div class="content-wrapper">
                <!-- Login Screen -->
                <div id="login-screen" class="login-screen">
                    <div class="login-card">
                        <h2 class="login-title">Вход в систему</h2>
                        <form id="login-form">
                            <div class="form-group">
                                <label class="form-label required-field">Код музея</label>
                                <input type="text" id="museum-code" class="form-control" placeholder="Введите код музея" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label required-field">Пароль</label>
                                <input type="password" id="password" class="form-control" placeholder="Введите пароль" required>
                            </div>
                            <button type="submit" class="btn btn-primary btn-full">
                                <span id="login-text">Войти в систему</span>
                                <span id="login-loading" class="loading hidden"></span>
                            </button>
                        </form>
                        <div id="login-message"></div>
                    </div>
                </div>

                <!-- Main Application -->
                <div id="main-app" class="hidden">
                    <div class="tabs-container">
                        <div class="tabs-header">
                            <button class="tab active" onclick="showTab('ticket-sale')">Продажа билетов</button>
                            <button class="tab" onclick="showTab('tickets-list')">Список билетов</button>
                        </div>

                        <!-- Ticket Sale Tab -->
                        <div id="ticket-sale" class="tab-content active">
                            <div class="card">
                                <div class="card-header">
                                    <h3 class="card-title">Продажа билетов</h3>
                                    <div>
                                        <div id="museum-info"></div>
                                        <div id="last-update-ticket" class="last-update"></div>
                                    </div>
                                </div>

                                <form id="ticket-form">
                                    <div class="form-group">
                                        <label class="form-label required-field">Дата посещения</label>
                                        <input type="date" id="visit-date" class="form-control" required>
                                    </div>

                                    <div class="form-group">
                                        <label class="form-label required-field">Время посещения</label>
                                        <div id="time-slots" class="time-slots"></div>
                                    </div>

                                    <div class="form-group">
                                        <label class="form-label required-field">Билеты</label>
                                        <div class="ticket-counter" id="ticket-counter">Добавлено билетов: 0 из 10</div>
                                        <div id="availability-info"></div>
                                        <div class="ticket-list" id="ticket-list">
                                            <!-- Билеты будут добавляться динамически -->
                                        </div>
                                        <button type="button" class="add-ticket-btn" onclick="addTicket()">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                <path d="M12 5v14M5 12h14"/>
                                            </svg>
                                            Добавить билет
                                        </button>
                                    </div>

                                    <div class="form-group">
                                        <label class="form-label">Информация о посетителе</label>
                                        <div class="form-row">
                                            <div>
                                                <label class="form-label required-field">Имя</label>
                                                <input type="text" id="visitor-name" class="form-control" placeholder="Имя" required>
                                            </div>
                                            <div>
                                                <label class="form-label optional-label">Фамилия</label>
                                                <input type="text" id="visitor-surname" class="form-control" placeholder="Фамилия (необязательно)">
                                            </div>
                                        </div>
                                        <div class="form-row mt-2">
                                            <div>
                                                <label class="form-label optional-label">Телефон</label>
                                                <input type="tel" id="visitor-phone" class="form-control" placeholder="Телефон (необязательно)">
                                            </div>
                                            <div>
                                                <label class="form-label optional-label">Email</label>
                                                <input type="email" id="visitor-email" class="form-control" placeholder="Email (необязательно)">
                                            </div>
                                        </div>
                                    </div>

                                    <div class="price-display">
                                        <span id="total-price">0.00</span> ₽
                                    </div>

                                    <button type="submit" class="btn btn-primary btn-full">
                                        <span id="create-ticket-text">Оформить билеты</span>
                                        <span id="create-ticket-loading" class="loading hidden"></span>
                                    </button>
                                </form>
                            </div>
                        </div>

                        <!-- Tickets List Tab -->
                        <div id="tickets-list" class="tab-content">
                            <div class="card">
                                <div class="card-header">
                                    <h3 class="card-title">Список билетов</h3>
                                    <div>
                                        <button id="refresh-tickets" class="btn btn-secondary" onclick="loadTickets()">Обновить список</button>
                                        <div id="last-update-tickets" class="last-update"></div>
                                    </div>
                                </div>

                                <div class="alert alert-info">
                                    <strong>После сканирования билета билет автоматически закрывается!</strong>
                                </div>

                                <!-- Поиск -->
                                <div class="search-section">
                                    <div class="search-input-container">
                                        <label class="form-label">Поиск билетов:</label>
                                        <input type="text" id="search-tickets" class="form-control" placeholder="Поиск по номеру, имени, фамилии, типу, цене..." oninput="handleSearch()">
                                    </div>
                                    <div>
                                        <button class="btn btn-secondary" onclick="clearSearch()">Очистить</button>
                                    </div>
                                </div>

                                <div class="table-container">
                                    <table class="table">
                                        <thead>
                                            <tr>
                                                <th>№ Билета</th>
                                                <th>Посетитель</th>
                                                <th>Тип</th>
                                                <th>Цена</th>
                                                <th>Дата/Время</th>
                                                <th>Статус</th>
                                                <th>Действия</th>
                                            </tr>
                                        </thead>
                                        <tbody id="tickets-table-body">
                                        </tbody>
                                    </table>
                                </div>

                                <div id="search-info" class="text-center mt-2" style="color: var(--text-light);"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        let currentMuseum = null;
        let selectedTimeSlot = null;
        let currentSearchTerm = '';
        let searchTimeout = null;
        let ticketCounter = 0;
        let tickets = [];
        let maxTicketsAllowed = 10; // Максимум по умолчанию
        let currentAvailableTickets = 0;

        document.addEventListener('DOMContentLoaded', function() {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('visit-date').value = today;
            document.getElementById('visit-date').min = today;

            document.getElementById('login-form').addEventListener('submit', handleLogin);
            document.getElementById('ticket-form').addEventListener('submit', handleTicketsCreation);
            document.getElementById('visit-date').addEventListener('change', loadTimeSlots);

            // Добавляем первый билет по умолчанию
            addTicket();
        });

        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            document.getElementById(tabName).classList.add('active');
            document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');

            if (tabName === 'tickets-list') {
                loadTickets();
            }
        }

        async function handleLogin(e) {
            e.preventDefault();

            const code = document.getElementById('museum-code').value;
            const password = document.getElementById('password').value;

            if (!code || !password) {
                showMessage('login-message', 'Заполните все поля', 'error');
                return;
            }

            setLoading('login', true);

            try {
                const result = await window.pywebview.api.authenticate(code, password);

                if (result.success) {
                    currentMuseum = result.museum;
                    showMainApp();
                    showMessage('login-message', 'Успешный вход!', 'success');
                } else {
                    showMessage('login-message', result.error, 'error');
                }
            } catch (error) {
                showMessage('login-message', 'Ошибка подключения', 'error');
            } finally {
                setLoading('login', false);
            }
        }

        function showMainApp() {
            document.getElementById('login-screen').classList.add('hidden');
            document.getElementById('main-app').classList.remove('hidden');
            document.getElementById('logout-btn').classList.remove('hidden');

            document.getElementById('museum-info').textContent = currentMuseum.name;
            document.getElementById('museum-info-header').textContent = currentMuseum.name;

            updateLastUpdate();
            loadTimeSlots();
        }

        async function logout() {
            try {
                await window.pywebview.api.logout();
                currentMuseum = null;
                document.getElementById('main-app').classList.add('hidden');
                document.getElementById('login-screen').classList.remove('hidden');
                document.getElementById('logout-btn').classList.add('hidden');
                document.getElementById('login-form').reset();
                showMessage('login-message', '', 'success');
            } catch (error) {
                console.error('Ошибка выхода:', error);
            }
        }

        async function loadTimeSlots() {
            if (!currentMuseum) return;

            const date = document.getElementById('visit-date').value;
            if (!date) return;

            try {
                const result = await window.pywebview.api.get_time_slots(date);
                const container = document.getElementById('time-slots');

                if (result.success) {
                    container.innerHTML = '';
                    selectedTimeSlot = null;
                    currentAvailableTickets = 0;
                    maxTicketsAllowed = 10;

                    if (result.slots.length === 0) {
                        container.innerHTML = '<div class="text-center">Нет доступных слотов</div>';
                        updateTicketCounter();
                        showAvailabilityInfo();
                        return;
                    }

                    result.slots.forEach(slot => {
                        const slotElement = document.createElement('div');
                        slotElement.className = 'time-slot';
                        slotElement.innerHTML = `
                            <div class="time-slot-time">${slot.start_time} - ${slot.end_time}</div>
                            <div class="time-slot-available">Доступно: ${slot.available_tickets} билетов</div>
                        `;

                        slotElement.addEventListener('click', () => selectTimeSlot(slotElement, slot));
                        container.appendChild(slotElement);
                    });

                    updateTicketCounter();
                    showAvailabilityInfo();
                } else {
                    container.innerHTML = `<div class="text-center">${result.error}</div>`;
                }
            } catch (error) {
                console.error('Ошибка загрузки слотов:', error);
                document.getElementById('time-slots').innerHTML = '<div class="text-center">Ошибка загрузки</div>';
            }
        }

        async function selectTimeSlot(element, slot) {
            document.querySelectorAll('.time-slot').forEach(el => {
                el.classList.remove('selected');
            });

            element.classList.add('selected');
            selectedTimeSlot = slot;

            // Получаем количество доступных билетов для выбранного слота
            try {
                const result = await window.pywebview.api.get_available_tickets(
                    document.getElementById('visit-date').value,
                    slot.start_time
                );

                if (result.success) {
                    currentAvailableTickets = result.available_tickets;
                    maxTicketsAllowed = Math.min(10, currentAvailableTickets); // Не более 10 билетов

                    // Обновляем счетчик билетов
                    updateTicketCounter();

                    // Показываем информацию о доступности
                    showAvailabilityInfo();

                    // Проверяем, не превышает ли текущее количество билетов доступное
                    if (tickets.length > maxTicketsAllowed) {
                        showMessage('ticket-sale', `Доступно только ${maxTicketsAllowed} билетов. Удалены лишние билеты.`, 'warning');

                        // Удаляем лишние билеты
                        while (tickets.length > maxTicketsAllowed) {
                            removeLastTicket();
                        }
                    }
                }
            } catch (error) {
                console.error('Ошибка получения доступных билетов:', error);
            }
        }

        function removeLastTicket() {
            if (tickets.length > 1) {
                const lastTicketId = tickets[tickets.length - 1].id;
                removeTicket(lastTicketId);
            }
        }

        function addTicket() {
            if (tickets.length >= maxTicketsAllowed) {
                showMessage('ticket-sale', `Максимум ${maxTicketsAllowed} билетов в выбранном слоте`, 'error');
                return;
            }

            const ticketId = ticketCounter++;
            const ticketList = document.getElementById('ticket-list');

            const ticketItem = document.createElement('div');
            ticketItem.className = 'ticket-item';
            ticketItem.id = `ticket-${ticketId}`;
            ticketItem.innerHTML = `
                <select class="form-control ticket-type-select" onchange="updateTicketPrice(${ticketId})">
                    <option value="">Выберите тип билета</option>
                    <option value="Стандартный">Стандартный</option>
                    <option value="Льготный">Льготный</option>
                    <option value="Детский">Детский</option>
                    <option value="Студенческий">Студенческий</option>
                    <option value="Пенсионный">Пенсионный</option>
                </select>
                <div class="ticket-price" id="ticket-price-${ticketId}">0.00 ₽</div>
                <button type="button" class="remove-ticket" onclick="removeTicket(${ticketId})">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 6 6 18M6 6l12 12"/>
                    </svg>
                </button>
            `;

            ticketList.appendChild(ticketItem);
            tickets.push({ id: ticketId, type: '', price: 0 });
            updateTicketCounter();
        }

        function removeTicket(ticketId) {
            if (tickets.length <= 1) {
                showMessage('ticket-sale', 'Должен остаться хотя бы один билет', 'error');
                return;
            }

            const ticketElement = document.getElementById(`ticket-${ticketId}`);
            if (ticketElement) {
                ticketElement.remove();
            }

            tickets = tickets.filter(ticket => ticket.id !== ticketId);
            updateTicketCounter();
            calculateTotalPrice();
        }

        async function updateTicketPrice(ticketId) {
            if (!currentMuseum) return;

            const selectElement = document.querySelector(`#ticket-${ticketId} .ticket-type-select`);
            const ticketType = selectElement.value;

            if (!ticketType) {
                document.getElementById(`ticket-price-${ticketId}`).textContent = '0.00 ₽';
                updateTicketInList(ticketId, '', 0);
                return;
            }

            try {
                const result = await window.pywebview.api.calculate_ticket_price(ticketType);
                if (result.success) {
                    const price = result.price;
                    document.getElementById(`ticket-price-${ticketId}`).textContent = `${price.toFixed(2)} ₽`;
                    updateTicketInList(ticketId, ticketType, price);
                    calculateTotalPrice();
                }
            } catch (error) {
                console.error('Ошибка расчета цены:', error);
            }
        }

        function updateTicketInList(ticketId, type, price) {
            const ticketIndex = tickets.findIndex(ticket => ticket.id === ticketId);
            if (ticketIndex !== -1) {
                tickets[ticketIndex].type = type;
                tickets[ticketIndex].price = price;
            }
        }

        function updateTicketCounter() {
            const counterElement = document.getElementById('ticket-counter');
            counterElement.textContent = `Добавлено билетов: ${tickets.length} из ${maxTicketsAllowed}`;

            // Добавляем визуальное предупреждение при приближении к лимиту
            if (tickets.length >= maxTicketsAllowed) {
                counterElement.className = 'ticket-counter limit-reached';
            } else if (tickets.length >= maxTicketsAllowed - 2) {
                counterElement.className = 'ticket-counter near-limit';
            } else {
                counterElement.className = 'ticket-counter';
            }
        }

        function showAvailabilityInfo() {
            // Удаляем старую информацию
            const oldInfo = document.getElementById('availability-info');
            if (oldInfo) {
                oldInfo.remove();
            }

            const ticketList = document.getElementById('ticket-list');
            const infoElement = document.createElement('div');
            infoElement.id = 'availability-info';
            infoElement.className = 'availability-info';

            if (!selectedTimeSlot) {
                infoElement.textContent = 'Выберите временной слот для просмотра доступности';
                infoElement.className = 'availability-info';
            } else if (currentAvailableTickets === 0) {
                infoElement.textContent = 'В выбранном слоте нет доступных билетов';
                infoElement.className = 'availability-error';
            } else if (currentAvailableTickets <= 3) {
                infoElement.textContent = `Осталось всего ${currentAvailableTickets} билетов в этом слоте`;
                infoElement.className = 'availability-warning';
            } else {
                infoElement.textContent = `Доступно билетов: ${currentAvailableTickets}`;
                infoElement.className = 'availability-success';
            }

            ticketList.parentNode.insertBefore(infoElement, ticketList);
        }

        function calculateTotalPrice() {
            const totalPrice = tickets.reduce((sum, ticket) => sum + ticket.price, 0);
            document.getElementById('total-price').textContent = totalPrice.toFixed(2);
        }

        async function handleTicketsCreation(e) {
            e.preventDefault();

            if (!currentMuseum) {
                showMessage('ticket-sale', 'Не авторизован', 'error');
                return;
            }

            const visitDate = document.getElementById('visit-date').value;
            const visitorName = document.getElementById('visitor-name').value;

            if (!visitDate || !visitorName) {
                showMessage('ticket-sale', 'Заполните обязательные поля', 'error');
                return;
            }

            if (!selectedTimeSlot) {
                showMessage('ticket-sale', 'Выберите временной слот', 'error');
                return;
            }

            // Дополнительная проверка доступности
            if (tickets.length > currentAvailableTickets) {
                showMessage('ticket-sale', `Недостаточно билетов. Доступно: ${currentAvailableTickets}`, 'error');
                return;
            }

            // Проверяем, что все билеты имеют выбранный тип
            const invalidTickets = tickets.filter(ticket => !ticket.type);
            if (invalidTickets.length > 0) {
                showMessage('ticket-sale', 'Выберите тип для всех билетов', 'error');
                return;
            }

            setLoading('create-ticket', true);

            try {
                const visitorData = {
                    name: visitorName,
                    surname: document.getElementById('visitor-surname').value,
                    phone: document.getElementById('visitor-phone').value,
                    email: document.getElementById('visitor-email').value
                };

                const ticketsData = tickets.map(ticket => ({
                    type: ticket.type,
                    price: ticket.price
                }));

                const timeSlotData = {
                    date: visitDate,
                    start_time: selectedTimeSlot.start_time
                };

                const result = await window.pywebview.api.create_tickets(visitorData, ticketsData, timeSlotData);

                if (result.success) {
                    const ticketNumbers = result.tickets.map(t => t.ticket_number).join(', ');
                    showMessage('ticket-sale', `Создано ${result.total_tickets} билетов! Номера: ${ticketNumbers}`, 'success');

                    // Сохраняем текущую дату перед сбросом формы
                    const currentDate = document.getElementById('visit-date').value;

                    // Сбрасываем только поля посетителя и билеты, но не дату
                    document.getElementById('visitor-name').value = '';
                    document.getElementById('visitor-surname').value = '';
                    document.getElementById('visitor-phone').value = '';
                    document.getElementById('visitor-email').value = '';

                    selectedTimeSlot = null;
                    document.querySelectorAll('.time-slot').forEach(el => {
                        el.classList.remove('selected');
                    });

                    // Сбрасываем список билетов
                    document.getElementById('ticket-list').innerHTML = '';
                    tickets = [];
                    ticketCounter = 0;
                    addTicket(); // Добавляем первый билет по умолчанию
                    calculateTotalPrice();
                    updateTicketCounter();
                    showAvailabilityInfo();

                    // Восстанавливаем дату и загружаем слоты для нее
                    document.getElementById('visit-date').value = currentDate;
                    loadTimeSlots();
                } else {
                    showMessage('ticket-sale', result.error, 'error');
                }
            } catch (error) {
                showMessage('ticket-sale', 'Ошибка создания билетов', 'error');
            } finally {
                setLoading('create-ticket', false);
            }
        }

        async function loadTickets() {
            if (!currentMuseum) return;

            try {
                const result = await window.pywebview.api.get_tickets();
                const tbody = document.getElementById('tickets-table-body');
                const searchInfo = document.getElementById('search-info');

                if (result.success) {
                    tbody.innerHTML = '';
                    searchInfo.textContent = '';

                    if (result.tickets.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Нет билетов для проверки</td></tr>';
                        return;
                    }

                    result.tickets.forEach(ticket => {
                        const row = createTicketRow(ticket, false);
                        tbody.appendChild(row);
                    });

                    updateLastUpdate('tickets');
                } else {
                    tbody.innerHTML = `<tr><td colspan="7" class="text-center">${result.error}</td></tr>`;
                }
            } catch (error) {
                console.error('Ошибка загрузки билетов:', error);
                document.getElementById('tickets-table-body').innerHTML = '<tr><td colspan="7" class="text-center">Ошибка загрузки</td></tr>';
            }
        }

        function createTicketRow(ticket, isSearchResult = false) {
            const row = document.createElement('tr');
            if (isSearchResult) {
                row.classList.add('search-highlight');
            }

            let statusClass = ticket.status === 'online' ? 'status-online' : 'status-offline';
            let statusText = ticket.status === 'online' ? 'Online' : 'Offline';

            row.innerHTML = `
                <td>${ticket.ticket_number}</td>
                <td>${ticket.name} ${ticket.surname || ''}</td>
                <td>${ticket.ticket_type}</td>
                <td>${parseFloat(ticket.price).toFixed(2)} ₽</td>
                <td>${ticket.visit_date} ${ticket.visit_time || ''}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td class="action-buttons">
                    <button class="btn btn-success btn-sm" onclick="verifyTicket('${ticket.ticket_number}')">Проверено</button>
                    <button class="btn btn-danger btn-sm" onclick="showRejectReason('${ticket.ticket_number}')">Отказано</button>
                </td>
            `;
            return row;
        }

        function handleSearch() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchTickets();
            }, 300);
        }

        async function searchTickets() {
            if (!currentMuseum) return;

            const searchTerm = document.getElementById('search-tickets').value.trim();
            currentSearchTerm = searchTerm;

            if (!searchTerm) {
                loadTickets();
                return;
            }

            try {
                const result = await window.pywebview.api.search_tickets(searchTerm);
                const tbody = document.getElementById('tickets-table-body');
                const searchInfo = document.getElementById('search-info');

                if (result.success) {
                    tbody.innerHTML = '';
                    searchInfo.textContent = '';

                    if (result.tickets.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Ничего не найдено</td></tr>';
                        searchInfo.textContent = 'По вашему запросу ничего не найдено';
                        return;
                    }

                    result.tickets.forEach(ticket => {
                        const row = createTicketRow(ticket, true);
                        tbody.appendChild(row);
                    });

                    searchInfo.textContent = `Найдено билетов: ${result.tickets.length}`;
                } else {
                    tbody.innerHTML = `<tr><td colspan="7" class="text-center">${result.error}</td></tr>`;
                }
            } catch (error) {
                console.error('Ошибка поиска:', error);
                document.getElementById('tickets-table-body').innerHTML = '<tr><td colspan="7" class="text-center">Ошибка поиска</td></tr>';
            }
        }

        function clearSearch() {
            document.getElementById('search-tickets').value = '';
            currentSearchTerm = '';
            loadTickets();
        }

        async function verifyTicket(ticketNumber) {
            if (!confirm('Отметить билет как проверенный?')) return;

            try {
                const result = await window.pywebview.api.update_ticket_check(ticketNumber, 'проверено');

                if (result.success) {
                    showMessage('tickets-list', 'Билет проверен', 'success');
                    if (currentSearchTerm) {
                        searchTickets();
                    } else {
                        loadTickets();
                    }
                } else {
                    showMessage('tickets-list', result.error, 'error');
                }
            } catch (error) {
                showMessage('tickets-list', 'Ошибка обновления статуса', 'error');
            }
        }

        function showRejectReason(ticketNumber) {
            const reason = prompt(`Выберите причину отказа для билета ${ticketNumber}:
1 - Недостоверность данных
2 - Возраст клиента не соответствует
3 - Билет уже использован
4 - Просроченный билет
5 - Другая причина

Введите номер причины:`);

            if (reason) {
                const reasons = {
                    '1': '(Отказано) Недостоверность данных',
                    '2': '(Отказано) Возраст клиента не соответствует', 
                    '3': '(Отказано) Билет уже использован',
                    '4': '(Отказано) Просроченный билет',
                    '5': '(Отказано) Другая причина'
                };

                const reasonText = reasons[reason] || 'Другая причина';
                rejectTicket(ticketNumber, reasonText);
            }
        }

        async function rejectTicket(ticketNumber, reason) {
            try {
                const result = await window.pywebview.api.update_ticket_check(ticketNumber, 'проверено', reason);

                if (result.success) {
                    showMessage('tickets-list', 'Билет отклонен', 'success');
                    if (currentSearchTerm) {
                        searchTickets();
                    } else {
                        loadTickets();
                    }
                } else {
                    showMessage('tickets-list', result.error, 'error');
                }
            } catch (error) {
                showMessage('tickets-list', 'Ошибка обновления статуса', 'error');
            }
        }

        function setLoading(buttonId, isLoading) {
            const textElement = document.getElementById(`${buttonId}-text`);
            const loadingElement = document.getElementById(`${buttonId}-loading`);

            if (isLoading) {
                textElement.classList.add('hidden');
                loadingElement.classList.remove('hidden');
            } else {
                textElement.classList.remove('hidden');
                loadingElement.classList.add('hidden');
            }
        }

        function showMessage(containerId, message, type) {
            const container = document.getElementById(containerId);
            let messageElement = container.querySelector('.alert');

            if (!messageElement) {
                messageElement = document.createElement('div');
                messageElement.className = `alert alert-${type}`;
                container.appendChild(messageElement);
            }

            messageElement.textContent = message;
            messageElement.className = `alert alert-${type}`;

            if (!message) {
                messageElement.style.display = 'none';
            } else {
                messageElement.style.display = 'block';
            }
        }

        function updateLastUpdate(section = '') {
            const now = new Date().toLocaleString('ru-RU');
            const sections = {
                '': 'last-update-header',
                'ticket': 'last-update-ticket', 
                'tickets': 'last-update-tickets'
            };

            const elementId = sections[section] || 'last-update-header';
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = `Обновлено: ${now}`;
            }
        }
    </script>
</body>
</html>
"""


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            super().do_GET()


def run_server(port=8080):
    with socketserver.TCPServer(("", port), RequestHandler) as httpd:
        print(f"Сервер запущен на порту {port}")
        httpd.serve_forever()


def start_gui():
    api = MuseumAPI()
    window = webview.create_window(
        'Музейная система',
        url='http://localhost:8080',
        width=1400,
        height=900,
        min_size=(1200, 800),
        js_api=api
    )
    webview.start()


if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(2)

    start_gui()