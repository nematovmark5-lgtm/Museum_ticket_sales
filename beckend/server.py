from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import mysql.connector
from fastapi import Body
from datetime import datetime
import logging
import os
import json
from fastapi import WebSocket, WebSocketDisconnect
import uuid
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Request          
from fastapi.responses import FileResponse, HTMLResponse     
import secrets                                               
import string
import re                                   

# ============================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# ИНИЦИАЛИЗАЦИЯ FASTAPI И CORS
# ============================================================
app = FastAPI(title="Museum Ticket System")





app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# PYDANTIC-МОДЕЛИ
# ============================================================

class TicketShareResponse(BaseModel):
    share_url: str
    token: str

class SharedTicketInfo(BaseModel):
    ticket_number: str
    visitor_name: str
    visitor_surname: Optional[str]
    museum_name: str
    visit_date: Optional[str]
    visit_time: Optional[str]
    ticket_type: str
    price: float
    status: Optional[str]

class AdminTicketUpdate(BaseModel):
    ticket_type: Optional[str] = None
    price: Optional[float] = None
    visit_date: Optional[str] = None
    visit_time: Optional[str] = None
    quantity: Optional[int] = None
    status: Optional[str] = None
    check: Optional[str] = None
    reason: Optional[str] = None

class VisitorCreate(BaseModel):
    login: str
    password: str
    name: str
    surname: Optional[str] = None
    phone: str

class VisitorResponse(BaseModel):
    id: int
    login: str
    name: str
    surname: Optional[str]
    phone: str

class TicketCreate(BaseModel):
    ticket_number: str
    visitor_id: int
    ticket_type: str
    price: float
    museum_code: str
    quantity: int
    visit_date: Optional[str] = None
    visit_time: Optional[str] = None

class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    visitor_id: int
    visitor_name: str
    visitor_surname: Optional[str]
    visitor_phone: Optional[str]
    museum_name: str
    museum_code: str
    ticket_type: str
    price: float
    quantity: int
    visit_date: Optional[str] = None
    visit_time: Optional[str] = None
    issued_at: datetime
    check: Optional[str] = None

class SaleCreate(BaseModel):
    museums_id: int
    quantity_tickets_sold: int
    income: str
    date: str
    status: str

class SaleResponse(BaseModel):
    id: int
    museums_id: int
    quantity_tickets_sold: int
    income: str
    date: str
    status: str

class VisitorLogin(BaseModel):
    login: str
    password: str

class TimeSlotResponse(BaseModel):
    id: int
    is_closed: bool = False
    museum_code: str
    date: str
    start_time: str
    end_time: str
    available_tickets: int

class TimeSlotReserve(BaseModel):
    museum_code: str
    date: str
    start_time: str
    quantity: int

class TimeSlotConfirm(BaseModel):
    museum_code: str
    date: str
    start_time: str
    quantity: int
    visitor_id: int

class CashierVisitorCreate(BaseModel):
    name: str
    surname: Optional[str] = None
    phone: Optional[str] = None


class CouponCreate(BaseModel):
    code: str
    discount_percent: float
    museum_id: Optional[int] = None
    max_uses: int = 0
    expires_at: Optional[str] = None

class CouponValidate(BaseModel):
    code: str
    museum_code: str

class CouponResponse(BaseModel):
    id: int
    code: str
    discount_percent: float
    museum_id: Optional[int] = None
    max_uses: int
    current_uses: int
    is_active: bool
    expires_at: Optional[str] = None



# ============================================================
# ПОДКЛЮЧЕНИЕ К БД
# ============================================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="Mark",
            password="0987654321",            
            database="museum_system",
            autocommit=False
        )
        logger.info("✅ Database connection successful")
        return connection
    except mysql.connector.Error as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# ============================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ
# ============================================================


# ============================================================
# ПУБЛИЧНЫЕ ДАННЫЕ
# ============================================================
@app.get("/api/museums-data")
async def get_museums_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, code, name, ticket_price, category,
                   short_description, description, working_hours,
                   address, images, is_active,
                   slot_start_time, slot_end_time, slot_duration_minutes,
                   slot_days_ahead, slot_tickets_default
            FROM museums
            WHERE is_active = 1
        """)
        museums = cursor.fetchall()
        for museum in museums:
            raw = museum.get('images')
            if isinstance(raw, str):
                try:
                    museum['images'] = json.loads(raw)
                except:
                    museum['images'] = []
            elif raw is None:
                museum['images'] = []
            museum['ticket_price'] = float(museum['ticket_price'])

        # Категории, сгруппированные по музеям
        cursor.execute("SELECT id, museum_id, name, discount_multiplier FROM ticket_categories ORDER BY id")
        all_categories = cursor.fetchall()
        categories_by_museum = {}
        for cat in all_categories:
            mid = cat['museum_id']
            if mid not in categories_by_museum:
                categories_by_museum[mid] = []
            categories_by_museum[mid].append({
                "id": cat['id'],
                "name": cat['name'],
                "discount_multiplier": float(cat['discount_multiplier'])
            })
        for museum in museums:
            museum['ticket_categories'] = categories_by_museum.get(museum['id'], [])

        cursor.execute("SELECT museum_id, closed_date, reason FROM museum_closed_dates")
        closed_dates = cursor.fetchall()
        for cd in closed_dates:
            cd['closed_date'] = cd['closed_date'].isoformat() if hasattr(cd['closed_date'], 'isoformat') else str(cd['closed_date'])

        return {
            "museums": museums,
            "closed_dates": closed_dates
        }
    finally:
        cursor.close()
        conn.close()

# ============================================================
# ВРЕМЕННЫЕ СЛОТЫ
# ============================================================



@app.get("/api/time-slots/{museum_code}/range")
async def get_time_slots_range(museum_code: str, from_date: str, to_date: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, museum_code, date, start_time, end_time, available_tickets, is_closed
            FROM time_slots
            WHERE museum_code = %s AND date BETWEEN %s AND %s
            ORDER BY date, start_time
        """, (museum_code, from_date, to_date))
        slots = cursor.fetchall()

        result = {}
        for slot in slots:
            date_str = str(slot['date'])
            if date_str not in result:
                result[date_str] = []
            result[date_str].append(TimeSlotResponse(
                id=slot['id'],
                is_closed=bool(slot['is_closed']),
                museum_code=slot['museum_code'],
                date=date_str,
                start_time=str(slot['start_time']),
                end_time=str(slot['end_time']),
                available_tickets=slot['available_tickets']
            ))
        return result
    finally:
        cursor.close()
        conn.close()



@app.get("/api/time-slots/{museum_code}/{date}", response_model=List[TimeSlotResponse])
async def get_time_slots(museum_code: str, date: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, slot_start_time, slot_end_time, slot_duration_minutes, slot_tickets_default FROM museums WHERE code = %s",
            (museum_code,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")

        start_time = str(museum['slot_start_time']) if museum['slot_start_time'] else '10:00:00'
        end_time = str(museum['slot_end_time']) if museum['slot_end_time'] else '18:00:00'
        duration = int(museum['slot_duration_minutes']) if museum['slot_duration_minutes'] else 120
        tickets = int(museum['slot_tickets_default']) if museum['slot_tickets_default'] else 10

        cursor.execute("""
            SELECT id, museum_code, date, start_time, end_time, available_tickets, is_closed
            FROM time_slots
            WHERE museum_code = %s AND date = %s
            ORDER BY start_time
        """, (museum_code, date))
        slots = cursor.fetchall()

        if not slots:
            current = datetime.strptime(start_time, '%H:%M:%S')
            end = datetime.strptime(end_time, '%H:%M:%S')
            while current + timedelta(minutes=duration) <= end:
                start_str = current.strftime('%H:%M:%S')
                end_str = (current + timedelta(minutes=duration)).strftime('%H:%M:%S')
                cursor.execute(
                    "INSERT IGNORE INTO time_slots (museum_code, date, start_time, end_time, available_tickets) VALUES (%s, %s, %s, %s, %s)",
                    (museum_code, date, start_str, end_str, tickets))
                current += timedelta(minutes=duration)
            conn.commit()
            cursor.execute("""
                SELECT id, museum_code, date, start_time, end_time, available_tickets, is_closed
                FROM time_slots
                WHERE museum_code = %s AND date = %s
                ORDER BY start_time
            """, (museum_code, date))
            slots = cursor.fetchall()

        formatted = []
        for slot in slots:
            formatted.append(TimeSlotResponse(
                id=slot['id'],
                is_closed=bool(slot['is_closed']),
                museum_code=slot['museum_code'],
                date=str(slot['date']),
                start_time=str(slot['start_time']),
                end_time=str(slot['end_time']),
                available_tickets=slot['available_tickets']
            ))
        return formatted
    finally:
        cursor.close()
        conn.close()


@app.post("/api/time-slots/reserve")
async def reserve_time_slot(reservation: TimeSlotReserve):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, available_tickets FROM time_slots WHERE museum_code=%s AND date=%s AND start_time=%s",
            (reservation.museum_code, reservation.date, reservation.start_time))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Слот не найден")
        if slot['available_tickets'] < reservation.quantity:
            raise HTTPException(status_code=400, detail=f"Недостаточно билетов. Доступно: {slot['available_tickets']}")
        return {"available": True, "available_tickets": slot['available_tickets'], "requested_quantity": reservation.quantity}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/time-slots/confirm-payment")
async def confirm_payment_and_reserve(confirmation: TimeSlotConfirm):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """UPDATE time_slots SET available_tickets = available_tickets - %s
               WHERE museum_code=%s AND date=%s AND start_time=%s AND available_tickets>=%s AND is_closed=0""",
            (confirmation.quantity, confirmation.museum_code, confirmation.date, confirmation.start_time, confirmation.quantity))
        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT available_tickets FROM time_slots WHERE museum_code=%s AND date=%s AND start_time=%s",
                (confirmation.museum_code, confirmation.date, confirmation.start_time))
            slot = cursor.fetchone()
            if not slot:
                raise HTTPException(status_code=404, detail="Слот не найден")
            raise HTTPException(status_code=400, detail=f"Недостаточно билетов. Доступно: {slot['available_tickets']}")
        conn.commit()
        cursor.execute(
            "SELECT available_tickets FROM time_slots WHERE museum_code=%s AND date=%s AND start_time=%s",
            (confirmation.museum_code, confirmation.date, confirmation.start_time))
        remaining = cursor.fetchone()['available_tickets']
        return {"success": True, "reserved_quantity": confirmation.quantity, "remaining_tickets": remaining}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/time-slots/cancel-reservation")
async def cancel_reservation(reservation: TimeSlotReserve):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute(
            "SELECT id, available_tickets FROM time_slots WHERE museum_code=%s AND date=%s AND start_time=%s FOR UPDATE",
            (reservation.museum_code, reservation.date, reservation.start_time))
        slot = cursor.fetchone()
        if not slot:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Слот не найден")
        cursor.execute(
            "UPDATE time_slots SET available_tickets = available_tickets + %s WHERE id = %s",
            (reservation.quantity, slot['id']))
        conn.commit()
        return {"success": True, "cancelled_quantity": reservation.quantity}
    finally:
        cursor.close()
        conn.close()

# ============================================================
# ЗДОРОВЬЕ
# ============================================================
@app.get("/api/health")
async def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ============================================================
# КАРТА МУЗЕЕВ
# ============================================================
@app.get("/api/museums/mapping")
async def get_museums_mapping():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, code FROM museums")
        return {m['code']: m['id'] for m in cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

# ============================================================
# ПРОДАЖИ
# ============================================================
@app.post("/api/sales/", response_model=SaleResponse)
async def create_sale(sale: SaleCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM museums WHERE id = %s", (sale.museums_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Музей не найден")
        cursor.execute(
            "INSERT INTO sales (museums_id, quantity_tickets_sold, income, date, status) VALUES (%s,%s,%s,%s,%s)",
            (sale.museums_id, sale.quantity_tickets_sold, sale.income, sale.date, sale.status))
        conn.commit()
        cursor.execute("SELECT * FROM sales WHERE id = %s", (cursor.lastrowid,))
        new_sale = cursor.fetchone()
        if new_sale['date'] and hasattr(new_sale['date'], 'isoformat'):
            new_sale['date'] = new_sale['date'].isoformat()
        return SaleResponse(**new_sale)
    finally:
        cursor.close()
        conn.close()

# ============================================================
# ПОСЕТИТЕЛИ
# ============================================================
@app.post("/api/visitors/", response_model=VisitorResponse)
async def create_visitor(visitor: VisitorCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM visitors WHERE login = %s", (visitor.login,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        cursor.execute(
            "INSERT INTO visitors (login, password, name, surname, phone) VALUES (%s,%s,%s,%s,%s)",
            (visitor.login, visitor.password, visitor.name, visitor.surname, visitor.phone))
        conn.commit()
        cursor.execute("SELECT * FROM visitors WHERE id = %s", (cursor.lastrowid,))
        return VisitorResponse(**cursor.fetchone())
    finally:
        cursor.close()
        conn.close()

@app.post("/api/visitors/login/", response_model=VisitorResponse)
async def login_visitor(credentials: VisitorLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM visitors WHERE login = %s AND password = %s",
            (credentials.login, credentials.password))
        visitor = cursor.fetchone()
        if not visitor:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        return VisitorResponse(**visitor)
    finally:
        cursor.close()
        conn.close()

# ============================================================
# БИЛЕТЫ
# ============================================================
@app.post("/api/tickets/", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, surname, phone FROM visitors WHERE id = %s", (ticket.visitor_id,))
        visitor = cursor.fetchone()
        if not visitor:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        cursor.execute("SELECT name FROM museums WHERE code = %s", (ticket.museum_code,))
        museum = cursor.fetchone()
        museum_name = museum['name'] if museum else "Неизвестный музей"
        cursor.execute(
            """INSERT INTO tickets (ticket_number, visitor_id, ticket_type, price, museum_code,
               quantity, visit_date, visit_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (ticket.ticket_number, ticket.visitor_id, ticket.ticket_type, ticket.price,
             ticket.museum_code, ticket.quantity, ticket.visit_date, ticket.visit_time))
        conn.commit()
        return TicketResponse(
            id=cursor.lastrowid,
            ticket_number=ticket.ticket_number,
            visitor_id=ticket.visitor_id,
            visitor_name=visitor['name'],
            visitor_surname=visitor['surname'],
            visitor_phone=visitor['phone'],
            museum_name=museum_name,
            museum_code=ticket.museum_code,
            ticket_type=ticket.ticket_type,
            price=ticket.price,
            quantity=ticket.quantity,
            visit_date=ticket.visit_date,
            visit_time=ticket.visit_time,
            issued_at=datetime.now()
        )
    finally:
        cursor.close()
        conn.close()

@app.get("/api/tickets/{visitor_id}", response_model=List[TicketResponse])
async def get_visitor_tickets(visitor_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM visitors WHERE id = %s", (visitor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        cursor.execute("""
            SELECT t.id, t.ticket_number, t.visitor_id, t.ticket_type, t.price, t.museum_code,
                   t.quantity, DATE(t.visit_date) as visit_date, TIME(t.visit_time) as visit_time,
                   t.issued_at, t.check,
                   v.name as visitor_name, v.surname as visitor_surname, v.phone as visitor_phone,
                   COALESCE(m.name, 'Неизвестный музей') as museum_name
            FROM tickets t
            JOIN visitors v ON t.visitor_id = v.id
            LEFT JOIN museums m ON t.museum_code = m.code
            WHERE t.visitor_id = %s ORDER BY t.issued_at DESC
        """, (visitor_id,))
        tickets = cursor.fetchall()
        result = []
        for t in tickets:
            result.append(TicketResponse(
                id=t['id'], ticket_number=t['ticket_number'], visitor_id=t['visitor_id'],
                visitor_name=t['visitor_name'], visitor_surname=t['visitor_surname'],
                visitor_phone=t['visitor_phone'], museum_name=t['museum_name'],
                museum_code=t['museum_code'], ticket_type=t['ticket_type'],
                price=float(t['price']), quantity=t['quantity'],
                visit_date=str(t['visit_date']) if t['visit_date'] else None,
                visit_time=str(t['visit_time']) if t['visit_time'] else None,
                issued_at=t['issued_at'].isoformat() if hasattr(t['issued_at'], 'isoformat') else str(t['issued_at']),
                check=t['check']))
        return result
    finally:
        cursor.close()
        conn.close()

# ============================================================
# ТЕСТОВЫЕ
# ============================================================
@app.get("/api/test/database")
async def test_database():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        tables = {}
        for tbl in ['museums', 'visitors', 'tickets', 'time_slots']:
            cursor.execute(f"SELECT COUNT(*) as count FROM {tbl}")
            tables[tbl] = cursor.fetchone()['count']
        return {"status": "success", "tables": tables, "database": "connected"}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/test/museums")
async def test_museums():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, code, name, ticket_price FROM museums")
        return {"museums": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()

# ============================================================
# WEB SOCKET ПОДГОТОВКА
# ============================================================
museum_subscribers: dict[str, list[WebSocket]] = {}
ticket_category_subscribers: list[WebSocket] = []
global_museum_subscribers: list[WebSocket] = []

# Модели для админки
class AdminLogin(BaseModel):
    full_name: str
    admin_code: str

class MuseumUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    ticket_price: Optional[float] = None
    address: Optional[str] = None
    working_hours: Optional[str] = None
    images: Optional[List[str]] = None
    is_active: Optional[bool] = None
    admin_full_name: Optional[str] = None
    admin_code: Optional[str] = None
    slot_start_time: Optional[str] = None
    slot_end_time: Optional[str] = None
    slot_duration_minutes: Optional[int] = None
    slot_days_ahead: Optional[int] = None
    slot_tickets_default: Optional[int] = None


class MuseumCreate(BaseModel):
    code: str
    password: str
    name: str
    ticket_price: float
    category: str = 'Искусство'
    address: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    is_active: bool = True
    working_hours: Optional[str] = None
    images: Optional[List[str]] = None
    admin_full_name: Optional[str] = None
    admin_code: Optional[str] = None

class ClosedDateCreate(BaseModel):
    closed_date: str
    reason: Optional[str] = None

class ClosedDateResponse(BaseModel):
    id: int
    museum_id: int
    closed_date: str
    reason: Optional[str] = None

class CashierLogin(BaseModel):
    code: str
    password: str

class CashierTicketItem(BaseModel):
    type: str
    price: float

class CashierSellRequest(BaseModel):
    museum_id: int
    museum_code: str
    date: str
    start_time: str
    quantity: int
    tickets: List[CashierTicketItem]
    visitor: VisitorCreate


class AdminListItem(BaseModel):
    museum_id: int
    museum_name: str
    login: Optional[str]
    admin_full_name: Optional[str]
    admin_code: Optional[str]

class AdminUpdate(BaseModel):
    login: Optional[str] = None
    admin_full_name: Optional[str] = None
    admin_code: Optional[str] = None

# ===================== ВХОДЫ (без сессий) =====================
@app.post("/api/admin/login")
async def admin_login(credentials: AdminLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # В функции admin_login замените строку запроса:
        cursor.execute(
            "SELECT id, code, name, ticket_price FROM museums WHERE login=%s AND admin_code=%s AND is_active=1",
            (credentials.full_name, credentials.admin_code)
        )
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=401, detail="Неверные данные администратора")
        return {
            "museum_id": museum["id"],
            "museum_name": museum["name"],
            "museum_code": museum["code"],
            "ticket_price": float(museum["ticket_price"])
        }
    finally:
        cursor.close()
        conn.close()

@app.post("/api/cashier/login")
async def cashier_login(credentials: CashierLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, code, name, ticket_price FROM museums WHERE code=%s AND password=%s AND is_active=1",
            (credentials.code, credentials.password))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=401, detail="Неверный код или пароль")
        return {
            "museum_id": museum["id"],
            "museum_name": museum["name"],
            "museum_code": museum["code"],
            "ticket_price": float(museum["ticket_price"])
        }
    finally:
        cursor.close()
        conn.close()

# ===================== ПОЛУЧЕНИЕ ДАННЫХ МУЗЕЯ =====================
@app.get("/api/admin/museum")
async def get_admin_museum(museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id, code, name, ticket_price, category, short_description,
               description, working_hours, address, images, is_active,
               slot_start_time, slot_end_time, slot_duration_minutes,
               slot_days_ahead, slot_tickets_default
            FROM museums WHERE id = %s""",
            (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")
        if isinstance(museum.get("images"), str):
            museum["images"] = json.loads(museum["images"])
        elif museum.get("images") is None:
            museum["images"] = []
        museum["ticket_price"] = float(museum["ticket_price"])
        if museum.get("slot_start_time"):
            museum["slot_start_time"] = str(museum["slot_start_time"])
        if museum.get("slot_end_time"):
            museum["slot_end_time"] = str(museum["slot_end_time"])
        return museum
    finally:
        cursor.close()
        conn.close()

# ===================== ОБНОВЛЕНИЕ МУЗЕЯ =====================
@app.put("/api/admin/museum")
async def update_admin_museum(museum_id: int, update_data: MuseumUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields, values = [], []
        for field, value in update_data.dict(exclude_unset=True).items():
            if field == "images":
                value = json.dumps(value)
            fields.append(f"`{field}` = %s")
            values.append(value)
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(museum_id)
        query = f"UPDATE museums SET {', '.join(fields)} WHERE id = %s"
        cursor.execute(query, values)
        conn.commit()

                # Если были изменены настройки слотов – удаляем будущие слоты
        changed_slot_fields = any(f in update_data.dict(exclude_unset=True) for f in [
            'slot_start_time', 'slot_end_time', 'slot_duration_minutes',
            'slot_days_ahead', 'slot_tickets_default'])
        if changed_slot_fields:
            # Удаляем все будущие слоты музея
            cursor.execute(
                "DELETE FROM time_slots WHERE museum_code = (SELECT code FROM museums WHERE id = %s) AND date >= CURDATE()",
                (museum_id,))
            conn.commit()

            # Загружаем актуальные настройки (могли измениться)
            cursor.execute(
                "SELECT code, slot_start_time, slot_end_time, slot_duration_minutes, slot_days_ahead, slot_tickets_default FROM museums WHERE id = %s",
                (museum_id,))
            museum_settings = cursor.fetchone()
            if museum_settings:
                code = museum_settings[0]
                start_time = museum_settings[1] or '10:00:00'
                end_time = museum_settings[2] or '18:00:00'
                duration = museum_settings[3] or 120
                days_ahead = museum_settings[4] or 90
                tickets = museum_settings[5] or 10

                # Генерируем слоты ровно на days_ahead дней (сегодня + days_ahead - 1)
                current_date = datetime.now().date()
                end_date = current_date + timedelta(days=days_ahead - 1)
                while current_date <= end_date:
                    date_str = current_date.isoformat()
                    current = datetime.strptime(str(start_time), '%H:%M:%S')
                    end = datetime.strptime(str(end_time), '%H:%M:%S')
                    while current + timedelta(minutes=int(duration)) <= end:
                        start_str = current.strftime('%H:%M:%S')
                        end_str = (current + timedelta(minutes=int(duration))).strftime('%H:%M:%S')
                        cursor.execute(
                            "INSERT IGNORE INTO time_slots (museum_code, date, start_time, end_time, available_tickets) VALUES (%s, %s, %s, %s, %s)",
                            (code, date_str, start_str, end_str, tickets))
                        current += timedelta(minutes=int(duration))
                    current_date += timedelta(days=1)
                conn.commit()

                # Отправляем уведомление подписчикам
                for ws in museum_subscribers.get(code, []):
                    try:
                        await ws.send_json({
                            "action": "slots_updated",
                            "slot_days_ahead": days_ahead
                        })
                    except:
                        pass
        # WebSocket уведомление
        cursor_dict = conn.cursor(dictionary=True)
        cursor_dict.execute("SELECT * FROM museums WHERE id = %s", (museum_id,))
        updated = cursor_dict.fetchone()
        cursor_dict.close()
        if updated:
            if isinstance(updated.get("images"), str):
                try:
                    updated["images"] = json.loads(updated["images"])
                except:
                    updated["images"] = []
            elif updated.get("images") is None:
                updated["images"] = []
            updated["ticket_price"] = float(updated["ticket_price"])
            museum_data = {
                "code": updated["code"],
                "name": updated["name"],
                "ticket_price": updated["ticket_price"],
                "category": updated["category"],
                "short_description": updated.get("short_description"),
                "description": updated.get("description"),
                "address": updated.get("address"),
                "working_hours": updated.get("working_hours"),
                "images": updated["images"],
                "is_active": updated["is_active"],
                # Добавляем поля слотов, чтобы клиент получал их при любом обновлении
                "slot_start_time": str(updated["slot_start_time"]) if updated.get("slot_start_time") else None,
                "slot_end_time": str(updated["slot_end_time"]) if updated.get("slot_end_time") else None,
                "slot_duration_minutes": updated.get("slot_duration_minutes"),
                "slot_days_ahead": updated.get("slot_days_ahead"),
                "slot_tickets_default": updated.get("slot_tickets_default")
            }
            for ws in museum_subscribers.get(updated["code"], []):
                try:
                    await ws.send_json(museum_data)
                except:
                    pass
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/admin/museum")
async def create_museum(data: MuseumCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверка уникальности кода
        cursor.execute("SELECT id FROM museums WHERE code = %s", (data.code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Музей с таким кодом уже существует")

        images = json.dumps(data.images) if data.images else None
        cursor.execute(
            """INSERT INTO museums (code, password, name, ticket_price, category, address, description,
               short_description, is_active, working_hours, images, admin_full_name, admin_code)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (data.code, data.password, data.name, data.ticket_price, data.category, data.address,
             data.description, data.short_description, data.is_active, data.working_hours,
             images, data.admin_full_name, data.admin_code)
        )
        conn.commit()
        new_id = cursor.lastrowid

        # Стандартный набор категорий для нового музея
        default_categories = [
            ("Стандартный", 1.0),
            ("Льготный", 0.6),
            ("Детский", 0.4),
            ("Студенческий", 0.5),
            ("Пенсионный", 0.4)
        ]
        for name, mult in default_categories:
            cursor.execute(
                "INSERT INTO ticket_categories (museum_id, name, discount_multiplier) VALUES (%s, %s, %s)",
                (new_id, name, mult))
        conn.commit()

                # Генерируем стандартные слоты на 90 дней для нового музея
        code = data.code
        start_time = '10:00:00'
        end_time = '18:00:00'
        duration = 120
        days_ahead = 90
        tickets = 10
        current_date = datetime.now().date()
        end_date = current_date + timedelta(days=days_ahead - 1)
        while current_date <= end_date:
            date_str = current_date.isoformat()
            current = datetime.strptime(start_time, '%H:%M:%S')
            end = datetime.strptime(end_time, '%H:%M:%S')
            while current + timedelta(minutes=duration) <= end:
                start_str = current.strftime('%H:%M:%S')
                end_str = (current + timedelta(minutes=duration)).strftime('%H:%M:%S')
                cursor.execute(
                    "INSERT IGNORE INTO time_slots (museum_code, date, start_time, end_time, available_tickets) VALUES (%s, %s, %s, %s, %s)",
                    (code, date_str, start_str, end_str, tickets))
                current += timedelta(minutes=duration)
            current_date += timedelta(days=1)
        conn.commit()

        # Теперь создаём словарный курсор и получаем полную информацию о музее
        cursor_dict = conn.cursor(dictionary=True)

        # Данные музея
        cursor_dict.execute("""
            SELECT id, code, name, ticket_price, category, short_description,
                   description, working_hours, address, images, is_active
            FROM museums WHERE id = %s
        """, (new_id,))
        new_museum = cursor_dict.fetchone()

        # Категории музея
        cursor_dict.execute("""
            SELECT id, name, discount_multiplier
            FROM ticket_categories
            WHERE museum_id = %s
            ORDER BY id
        """, (new_id,))
        ticket_categories = cursor_dict.fetchall()
        categories_list = [{"id": tc["id"], "name": tc["name"], "discount_multiplier": float(tc["discount_multiplier"])} for tc in ticket_categories]

        cursor_dict.close()

        if new_museum:
            if isinstance(new_museum.get("images"), str):
                try:
                    new_museum["images"] = json.loads(new_museum["images"])
                except:
                    new_museum["images"] = []
            elif new_museum.get("images") is None:
                new_museum["images"] = []
            new_museum["ticket_price"] = float(new_museum["ticket_price"])
            new_museum["ticket_categories"] = categories_list

            # Оповещаем всех глобальных подписчиков
            for ws in global_museum_subscribers:
                try:
                    await ws.send_json({
                        "action": "museum_added",
                        "museum": new_museum
                    })
                except:
                    pass

        return {"success": True, "museum_id": new_id}

    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.delete("/api/admin/museum")
async def delete_museum(museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Получаем код и название музея до удаления
        cursor.execute("SELECT code, name FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")

        museum_code = museum["code"]
        museum_name = museum["name"]

        # Удаляем музей (каскадные удаления сработают)
        cursor.execute("DELETE FROM museums WHERE id = %s", (museum_id,))
        conn.commit()

        # Отправляем WebSocket-уведомление всем подписчикам музея
        for ws in museum_subscribers.get(museum_code, []):
            try:
                await ws.send_json({
                    "action": "museum_deleted",
                    "museum_code": museum_code,
                    "museum_name": museum_name
                })
            except:
                pass

        # Также можно удалить код музея из словаря подписчиков, чтобы не копились мёртвые соединения
        if museum_code in museum_subscribers:
            del museum_subscribers[museum_code]

        return {"success": True, "message": "Музей удалён"}

    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ===================== УПРАВЛЕНИЕ ЗАКРЫТЫМИ ДАТАМИ =====================
@app.get("/api/admin/closed-dates", response_model=List[ClosedDateResponse])
async def get_closed_dates(museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, museum_id, closed_date, reason FROM museum_closed_dates WHERE museum_id = %s ORDER BY closed_date",
            (museum_id,))
        dates = cursor.fetchall()
        for d in dates:
            d['closed_date'] = d['closed_date'].isoformat() if hasattr(d['closed_date'], 'isoformat') else str(d['closed_date'])
        return [ClosedDateResponse(**d) for d in dates]
    finally:
        cursor.close()
        conn.close()

@app.post("/api/admin/closed-dates", response_model=ClosedDateResponse)
async def add_closed_date(museum_id: int, data: ClosedDateCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO museum_closed_dates (museum_id, closed_date, reason) VALUES (%s, %s, %s)",
            (museum_id, data.closed_date, data.reason))
        conn.commit()
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if museum:
            for ws in museum_subscribers.get(museum["code"], []):
                try:
                    await ws.send_json({
                        "action": "closed_date_added",
                        "museum_code": museum["code"],
                        "closed_date": data.closed_date,
                        "reason": data.reason
                    })
                except:
                    pass
        return ClosedDateResponse(
            id=cursor.lastrowid,
            museum_id=museum_id,
            closed_date=data.closed_date,
            reason=data.reason
        )
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/closed-dates/{date_id}")
async def delete_closed_date(date_id: int, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT closed_date FROM museum_closed_dates WHERE id = %s AND museum_id = %s",
            (date_id, museum_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Дата не найдена")
        closed_date_str = str(row[0])
        cursor.execute(
            "DELETE FROM museum_closed_dates WHERE id = %s AND museum_id = %s",
            (date_id, museum_id))
        conn.commit()
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum_row = cursor.fetchone()
        if museum_row:
            for ws in museum_subscribers.get(museum_row[0], []):
                try:
                    await ws.send_json({
                        "action": "closed_date_removed",
                        "museum_code": museum_row[0],
                        "closed_date": closed_date_str
                    })
                except:
                    pass
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ===================== СТАТИСТИКА =====================
@app.get("/api/admin/stats")
async def get_admin_stats(museum_id: int, start_date: str = None, end_date: str = None, group_by: str = "day"):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        where_clause = "WHERE museums_id = %s"
        params = [museum_id]
        if start_date and end_date:
            where_clause += " AND date BETWEEN %s AND %s"
            params.append(start_date)
            params.append(end_date)
        elif start_date:
            where_clause += " AND date >= %s"
            params.append(start_date)
        elif end_date:
            where_clause += " AND date <= %s"
            params.append(end_date)

        cursor.execute(f"""
            SELECT COUNT(*) as total_sales,
                   COALESCE(SUM(quantity_tickets_sold), 0) as total_tickets,
                   COALESCE(SUM(CAST(income AS DECIMAL(10,2))), 0) as total_income
            FROM sales {where_clause}
        """, params)
        summary = cursor.fetchone()

        if group_by == "month":
            group_field = "DATE_FORMAT(date, '%Y-%m')"
        else:
            group_field = "DATE(date)"

        cursor.execute(f"""
            SELECT {group_field} as period,
                   COALESCE(SUM(quantity_tickets_sold), 0) as tickets,
                   COALESCE(SUM(CAST(income AS DECIMAL(10,2))), 0) as income
            FROM sales {where_clause}
            GROUP BY period ORDER BY period
        """, params)
        periods = cursor.fetchall()
        for p in periods:
            p['period'] = p['period'].isoformat() if hasattr(p['period'], 'isoformat') else str(p['period'])

        return {
            "total_sales": summary["total_sales"],
            "total_tickets": summary["total_tickets"],
            "total_income": float(summary["total_income"]),
            "periods": periods
        }
    finally:
        cursor.close()
        conn.close()

# ===================== УПРАВЛЕНИЕ КАТЕГОРИЯМИ БИЛЕТОВ =====================
class TicketCategoryUpdate(BaseModel):
    name: str
    discount_multiplier: float

class TicketCategoryResponse(BaseModel):
    id: int
    name: str
    discount_multiplier: float

@app.get("/api/admin/ticket-categories", response_model=List[TicketCategoryResponse])
async def get_admin_ticket_categories(museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, discount_multiplier FROM ticket_categories WHERE museum_id = %s ORDER BY id",
            (museum_id,))
        return [TicketCategoryResponse(**c) for c in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

@app.post("/api/admin/ticket-categories", response_model=TicketCategoryResponse)
async def create_ticket_category(museum_id: int, data: TicketCategoryUpdate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO ticket_categories (museum_id, name, discount_multiplier) VALUES (%s, %s, %s)",
            (museum_id, data.name, data.discount_multiplier))
        conn.commit()
        new_id = cursor.lastrowid
        # WebSocket уведомление
        for ws in ticket_category_subscribers:
            try:
                await ws.send_json({
                    "action": "created",
                    "category": {"id": new_id, "name": data.name, "discount_multiplier": data.discount_multiplier},
                    "museum_id": museum_id
                })
            except: pass
        return TicketCategoryResponse(id=new_id, name=data.name, discount_multiplier=data.discount_multiplier)
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/ticket-categories/{category_id}", response_model=TicketCategoryResponse)
async def update_ticket_category(category_id: int, museum_id: int, data: TicketCategoryUpdate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT museum_id FROM ticket_categories WHERE id = %s", (category_id,))
        cat = cursor.fetchone()
        if not cat or cat['museum_id'] != museum_id:
            raise HTTPException(status_code=404, detail="Категория не найдена или нет доступа")
        cursor.execute(
            "UPDATE ticket_categories SET name = %s, discount_multiplier = %s WHERE id = %s",
            (data.name, data.discount_multiplier, category_id))
        conn.commit()
        # WebSocket уведомление
        for ws in ticket_category_subscribers:
            try:
                await ws.send_json({
                    "action": "updated",
                    "category": {"id": category_id, "name": data.name, "discount_multiplier": data.discount_multiplier},
                    "museum_id": museum_id
                })
            except: pass
        return TicketCategoryResponse(id=category_id, name=data.name, discount_multiplier=data.discount_multiplier)
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/ticket-categories/{category_id}")
async def delete_ticket_category(category_id: int, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT museum_id, name FROM ticket_categories WHERE id = %s", (category_id,))
        cat = cursor.fetchone()
        if not cat or cat['museum_id'] != museum_id:
            raise HTTPException(status_code=404, detail="Категория не найдена или нет доступа")
        deleted_name = cat['name']
        cursor.execute("DELETE FROM ticket_categories WHERE id = %s", (category_id,))
        conn.commit()
        # WebSocket уведомление
        for ws in ticket_category_subscribers:
            try:
                await ws.send_json({
                    "action": "deleted",
                    "category_id": category_id,
                    "category_name": deleted_name,
                    "museum_id": museum_id
                })
            except: pass
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ==================== АДМИН: ПОИСК БИЛЕТОВ ====================
@app.get("/api/admin/tickets")
async def admin_search_tickets(museum_id: int, search: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT t.*, v.name as visitor_name, v.surname as visitor_surname,
                   v.phone as visitor_phone, m.name as museum_name
            FROM tickets t
            JOIN visitors v ON t.visitor_id = v.id
            JOIN museums m ON t.museum_code = m.code
            WHERE m.id = %s
        """
        params = [museum_id]
        if search:
            query += " AND (v.name LIKE %s OR v.surname LIKE %s OR v.phone LIKE %s OR t.ticket_number LIKE %s)"
            like_search = f"%{search}%"
            params.extend([like_search, like_search, like_search, like_search])
        query += " ORDER BY t.issued_at DESC LIMIT 200"
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        for t in tickets:
            if t.get('visit_date') and hasattr(t['visit_date'], 'isoformat'):
                t['visit_date'] = t['visit_date'].isoformat()
            else:
                t['visit_date'] = str(t['visit_date']) if t['visit_date'] else None
            if t.get('visit_time') and hasattr(t['visit_time'], 'isoformat'):
                t['visit_time'] = t['visit_time'].isoformat()
            else:
                t['visit_time'] = str(t['visit_time']) if t['visit_time'] else None
            if t.get('issued_at') and hasattr(t['issued_at'], 'isoformat'):
                t['issued_at'] = t['issued_at'].isoformat()
            else:
                t['issued_at'] = str(t['issued_at']) if t['issued_at'] else None
        return tickets
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/tickets/{ticket_id}")
async def admin_update_ticket(ticket_id: int, data: AdminTicketUpdate, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.id, m.id as museum_id
            FROM tickets t
            JOIN museums m ON t.museum_code = m.code
            WHERE t.id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket or ticket['museum_id'] != museum_id:
            raise HTTPException(status_code=404, detail="Билет не найден или нет доступа")
        update_data = data.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        fields, values = [], []
        for key, value in update_data.items():
            fields.append(f"`{key}` = %s")
            values.append(value)
        values.append(ticket_id)
        cursor.execute(f"UPDATE tickets SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/tickets/{ticket_id}")
async def admin_delete_ticket(ticket_id: int, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.id, m.id as museum_id
            FROM tickets t
            JOIN museums m ON t.museum_code = m.code
            WHERE t.id = %s
        """, (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket or ticket['museum_id'] != museum_id:
            raise HTTPException(status_code=404, detail="Билет не найден или нет доступа")
        cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
        conn.commit()
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ==================== УПРАВЛЕНИЕ СЛОТАМИ ====================
@app.put("/api/admin/time-slots/{slot_id}/close")
async def admin_close_time_slot(slot_id: int, museum_id: int, reason: str = Body(None, embed=True)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM time_slots WHERE id = %s", (slot_id,))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Слот не найден")
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum_code_row = cursor.fetchone()
        if not museum_code_row or slot["museum_code"] != museum_code_row["code"]:
            raise HTTPException(status_code=403, detail="Нет доступа")
        cursor.execute("UPDATE time_slots SET is_closed = 1, close_reason = %s WHERE id = %s", (reason, slot_id))
        conn.commit()
        code = slot["museum_code"]
        for ws in museum_subscribers.get(code, []):
            try:
                await ws.send_json({
                    "action": "slot_closed",
                    "museum_code": code,
                    "date": str(slot["date"]),
                    "start_time": str(slot["start_time"]),
                    "end_time": str(slot["end_time"]),
                    "reason": reason
                })
            except:
                pass
        return {"success": True, "message": "Слот закрыт"}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/time-slots/{slot_id}/open")
async def admin_open_time_slot(slot_id: int, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM time_slots WHERE id = %s", (slot_id,))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Слот не найден")
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum_code_row = cursor.fetchone()
        if not museum_code_row or slot["museum_code"] != museum_code_row["code"]:
            raise HTTPException(status_code=403, detail="Нет доступа")
        cursor.execute("UPDATE time_slots SET is_closed = 0, close_reason = NULL WHERE id = %s", (slot_id,))
        conn.commit()
        code = slot["museum_code"]
        for ws in museum_subscribers.get(code, []):
            try:
                await ws.send_json({
                    "action": "slot_opened",
                    "museum_code": code,
                    "date": str(slot["date"]),
                    "start_time": str(slot["start_time"]),
                    "end_time": str(slot["end_time"])
                })
            except:
                pass
        return {"success": True, "message": "Слот открыт"}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ==================== КАССИР: ПРОДАЖА ====================
@app.post("/api/cashier/sell")
async def cashier_sell(request: CashierSellRequest):
    """Продажа билетов через кассу (без токена, используется museum_id из запроса)."""
    museum_id = request.museum_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, code, name, ticket_price FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")
        if museum["code"] != request.museum_code:
            raise HTTPException(status_code=403, detail="Неверный код музея")
        cursor.execute(
            "SELECT id, available_tickets, is_closed FROM time_slots WHERE museum_code = %s AND date = %s AND start_time = %s",
            (request.museum_code, request.date, request.start_time))
        slot = cursor.fetchone()
        if not slot:
            raise HTTPException(status_code=404, detail="Временной слот не найден")
        if slot["is_closed"]:
            raise HTTPException(status_code=400, detail="Слот закрыт администратором")
        if slot["available_tickets"] < request.quantity:
            raise HTTPException(status_code=400, detail=f"Недостаточно билетов. Доступно: {slot['available_tickets']}")
        cursor.execute("SELECT name, discount_multiplier FROM ticket_categories")
        categories = {cat["name"]: float(cat["discount_multiplier"]) for cat in cursor.fetchall()}
        base_price = float(museum["ticket_price"])
        visitor_name = request.visitor.name.strip()
        if not visitor_name:
            raise HTTPException(status_code=400, detail="Имя посетителя обязательно")
        cursor.execute(
            "INSERT INTO visitors (name, surname, phone, login, password) VALUES (%s, %s, %s, NULL, NULL)",
            (visitor_name, request.visitor.surname, request.visitor.phone))
        visitor_id = cursor.lastrowid
        ticket_numbers = []
        total_income = 0
        base_ticket_number = f"T{int(datetime.now().timestamp() * 1000)}"
        for i, ticket in enumerate(request.tickets):
            multiplier = categories.get(ticket.type, 1.0)
            price = round(base_price * multiplier, 2)
            ticket_number = f"{base_ticket_number}-{(i+1):02d}"
            cursor.execute(
                """INSERT INTO tickets (ticket_number, visitor_id, ticket_type, price, museum_code,
                   visit_date, visit_time, quantity, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'offline')""",
                (ticket_number, visitor_id, ticket.type, price, request.museum_code,
                 request.date, request.start_time))
            ticket_numbers.append(ticket_number)
            total_income += price
        cursor.execute(
            "UPDATE time_slots SET available_tickets = available_tickets - %s WHERE id = %s",
            (request.quantity, slot["id"]))
        cursor.execute(
            "INSERT INTO sales (museums_id, quantity_tickets_sold, income, date, status) VALUES (%s, %s, %s, %s, 'offline')",
            (museum_id, request.quantity, total_income, request.date))
        conn.commit()
        return {
            "success": True,
            "ticket_numbers": ticket_numbers,
            "total_income": total_income
        }
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# ==================== КАССИР: ПОЛУЧИТЬ БИЛЕТЫ ДЛЯ ПРОВЕРКИ ====================
@app.get("/api/cashier/tickets")
async def cashier_get_tickets(museum_id: int, search: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")
        query = """
            SELECT t.ticket_number, t.ticket_type, t.price, t.visit_date, t.visit_time,
                   t.status, t.check, t.reason,
                   v.name AS visitor_name, v.surname AS visitor_surname, v.phone AS visitor_phone
            FROM tickets t
            JOIN visitors v ON t.visitor_id = v.id
            WHERE t.museum_code = %s AND (t.check IS NULL OR t.check != 'проверено')
        """
        params = [museum["code"]]
        if search:
            query += " AND (t.ticket_number LIKE %s OR v.name LIKE %s OR v.surname LIKE %s OR v.phone LIKE %s)"
            like = f"%{search}%"
            params.extend([like, like, like, like])
        query += " ORDER BY t.issued_at DESC LIMIT 200"
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        for t in tickets:
            if t.get('visit_date') and hasattr(t['visit_date'], 'isoformat'):
                t['visit_date'] = t['visit_date'].isoformat()
            else:
                t['visit_date'] = str(t['visit_date']) if t['visit_date'] else None
            if t.get('visit_time') and hasattr(t['visit_time'], 'isoformat'):
                t['visit_time'] = t['visit_time'].isoformat()
            else:
                t['visit_time'] = str(t['visit_time']) if t['visit_time'] else None
        return tickets
    finally:
        cursor.close()
        conn.close()

# ==================== КАССИР: ПРОВЕРИТЬ/ОТКАЗАТЬ БИЛЕТ ====================
@app.put("/api/cashier/tickets/{ticket_number}/check")
async def cashier_check_ticket(ticket_number: str, museum_id: int, check: str = Body(...), reason: str = Body(None)):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum_row = cursor.fetchone()
        if not museum_row:
            raise HTTPException(status_code=404, detail="Музей не найден")
        museum_code = museum_row["code"]
        cursor.execute(
            "SELECT id FROM tickets WHERE ticket_number = %s AND museum_code = %s",
            (ticket_number, museum_code))
        ticket = cursor.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Билет не найден в вашем музее")
        cursor.execute(
            "UPDATE tickets SET `check` = %s, reason = %s WHERE ticket_number = %s",
            (check, reason, ticket_number))
        conn.commit()
        return {"success": True, "message": "Статус обновлён"}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ==================== КАССИР: ПОЛУЧИТЬ ПРОВЕРЕННЫЕ БИЛЕТЫ ====================
@app.get("/api/cashier/tickets/checked")
async def cashier_checked_tickets(museum_id: int, search: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")
        query = """
            SELECT t.*, v.name as visitor_name, v.surname as visitor_surname, v.phone as visitor_phone
            FROM tickets t
            JOIN visitors v ON t.visitor_id = v.id
            WHERE t.museum_code = %s AND t.`check` = 'проверено'
        """
        params = [museum["code"]]
        if search:
            query += " AND (t.ticket_number LIKE %s OR v.name LIKE %s OR v.surname LIKE %s OR v.phone LIKE %s)"
            like = f"%{search}%"
            params.extend([like, like, like, like])
        query += " ORDER BY t.issued_at DESC LIMIT 200"
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        for t in tickets:
            if t.get('visit_date') and hasattr(t['visit_date'], 'isoformat'):
                t['visit_date'] = t['visit_date'].isoformat()
            else:
                t['visit_date'] = str(t['visit_date']) if t['visit_date'] else None
            if t.get('visit_time') and hasattr(t['visit_time'], 'isoformat'):
                t['visit_time'] = t['visit_time'].isoformat()
            else:
                t['visit_time'] = str(t['visit_time']) if t['visit_time'] else None
        return tickets
    finally:
        cursor.close()
        conn.close()

# ==================== КАССИР: ВЕРНУТЬ БИЛЕТ (СБРОСИТЬ ПРОВЕРКУ) ====================
@app.put("/api/cashier/tickets/{ticket_number}/uncheck")
async def cashier_uncheck_ticket(ticket_number: str, museum_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT code FROM museums WHERE id = %s", (museum_id,))
        museum = cursor.fetchone()
        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")
        cursor.execute(
            "SELECT id FROM tickets WHERE ticket_number = %s AND museum_code = %s",
            (ticket_number, museum["code"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Билет не найден")
        cursor.execute(
            "UPDATE tickets SET `check` = NULL, reason = NULL WHERE ticket_number = %s",
            (ticket_number,))
        conn.commit()
        return {"success": True, "message": "Билет возвращён"}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


class SuperLogin(BaseModel):
    username: str
    password: str

@app.post("/api/super/login")
async def super_login(credentials: SuperLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id FROM museums WHERE super_admin_login = %s AND super_admin_password = %s",
            (credentials.username, credentials.password)
        )
        # Принудительно читаем все строки (даже если нужна только одна)
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        return {"success": True, "message": "Вход выполнен"}
    finally:
        cursor.close()
        conn.close()   # обязательно закрываем соединение              # ← и соединение тоже закрываем

# ==================== WebSocket ====================
@app.websocket("/ws/museum/{museum_code}")
async def websocket_museum_updates(websocket: WebSocket, museum_code: str):
    await websocket.accept()
    museum_subscribers.setdefault(museum_code, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        museum_subscribers.get(museum_code, []).remove(websocket)
        if not museum_subscribers[museum_code]:
            del museum_subscribers[museum_code]

@app.websocket("/ws/ticket-categories")
async def websocket_ticket_categories(websocket: WebSocket):
    await websocket.accept()
    ticket_category_subscribers.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ticket_category_subscribers.remove(websocket)


@app.websocket("/ws/museums")
async def websocket_museums(websocket: WebSocket):
    """Глобальный канал для уведомлений о добавлении/удалении музеев."""
    await websocket.accept()
    global_museum_subscribers.append(websocket)
    try:
        while True:
            await websocket.receive_text()   # держим соединение
    except WebSocketDisconnect:
        pass
    finally:
        global_museum_subscribers.remove(websocket)




from fastapi.staticfiles import StaticFiles
import os

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
# ============================================================
# СТАТИЧЕСКИЕ ФАЙЛЫ (замена твоих старых маршрутов)
# ============================================================

# Основные страницы
@app.get("/")
async def serve_homepage():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/index.html")
async def serve_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/admin.html")
async def serve_admin():
    return FileResponse(os.path.join(frontend_path, "admin.html"))

@app.get("/superadmin.html")
async def serve_superadmin():
    return FileResponse(os.path.join(frontend_path, "superadmin.html"))

@app.get("/kasir.html")
async def serve_kasir():
    return FileResponse(os.path.join(frontend_path, "kasir.html"))

# Корневые библиотеки (если используются в HTML без подпапки)
@app.get("/html2canvas.min.js")
async def serve_html2canvas():
    return FileResponse(os.path.join(frontend_path, "html2canvas.min.js"))

@app.get("/qrcode.min.js")
async def serve_qrcode():
    return FileResponse(os.path.join(frontend_path, "qrcode.min.js"))

@app.get("/script.js")
async def serve_script():
    return FileResponse(os.path.join(frontend_path, "script.js"))

@app.get("/styles.css")
async def serve_css():
    return FileResponse(os.path.join(frontend_path, "styles.css"))

# Папка libs (если библиотеки лежат в /frontend/libs/)
# Например, chart.umd.min.js, jspdf.umd.min.js и т.д.
libs_path = os.path.join(frontend_path, "libs")
if os.path.isdir(libs_path):
    app.mount("/libs", StaticFiles(directory=libs_path), name="libs")

# Папка images (уже была, но на всякий случай оставь)
app.mount("/images", StaticFiles(directory=os.path.join(frontend_path, "images")), name="images")

import socket

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    
def generate_slots_for_all_active_museums():
    """При старте создаём слоты для всех активных музеев на 90 дней вперёд."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Получаем все активные музеи
        cursor.execute("SELECT code, slot_start_time, slot_end_time, slot_duration_minutes, slot_days_ahead, slot_tickets_default FROM museums WHERE is_active = 1")
        museums = cursor.fetchall()
        for museum in museums:
            code = museum[0]
            start_time = museum[1] or '10:00:00'
            end_time = museum[2] or '18:00:00'
            duration = int(museum[3]) if museum[3] else 120
            days_ahead = int(museum[4]) if museum[4] else 90
            tickets = int(museum[5]) if museum[5] else 10

            current_date = datetime.now().date()
            end_date = current_date + timedelta(days=days_ahead - 1)
            while current_date <= end_date:
                date_str = current_date.isoformat()
                # Проверяем, есть ли уже слоты на эту дату
                cursor.execute("SELECT COUNT(*) FROM time_slots WHERE museum_code = %s AND date = %s", (code, date_str))
                cnt = cursor.fetchone()[0]
                if cnt == 0:
                    current = datetime.strptime(str(start_time), '%H:%M:%S')
                    end = datetime.strptime(str(end_time), '%H:%M:%S')
                    while current + timedelta(minutes=duration) <= end:
                        start_str = current.strftime('%H:%M:%S')
                        end_str = (current + timedelta(minutes=duration)).strftime('%H:%M:%S')
                        cursor.execute(
                            "INSERT IGNORE INTO time_slots (museum_code, date, start_time, end_time, available_tickets) VALUES (%s, %s, %s, %s, %s)",
                            (code, date_str, start_str, end_str, tickets))
                        current += timedelta(minutes=duration)
                    conn.commit()  # коммитим после каждого дня, чтобы не блокировать таблицу
                current_date += timedelta(days=1)
    finally:
        cursor.close()
        conn.close()

@app.get("/api/admin/coupons", response_model=List[CouponResponse])
async def get_coupons(museum_id: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if museum_id:
            cursor.execute("SELECT * FROM coupons WHERE museum_id = %s OR museum_id IS NULL", (museum_id,))
        else:
            cursor.execute("SELECT * FROM coupons")
        coupons = cursor.fetchall()
        for c in coupons:
            if c.get('expires_at') and hasattr(c['expires_at'], 'isoformat'):
                c['expires_at'] = c['expires_at'].isoformat()
        return coupons
    finally:
        cursor.close()
        conn.close()

@app.post("/api/admin/coupons", response_model=CouponResponse)
async def create_coupon(coupon: CouponCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO coupons (code, discount_percent, museum_id, max_uses, expires_at) VALUES (%s, %s, %s, %s, %s)",
            (coupon.code, coupon.discount_percent, coupon.museum_id, coupon.max_uses, coupon.expires_at)
        )
        conn.commit()
        return CouponResponse(id=cursor.lastrowid, code=coupon.code, discount_percent=coupon.discount_percent,
                              museum_id=coupon.museum_id, max_uses=coupon.max_uses, current_uses=0,
                              is_active=True, expires_at=coupon.expires_at)
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/admin/coupons/{coupon_id}")
async def delete_coupon(coupon_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM coupons WHERE id = %s", (coupon_id,))
        conn.commit()
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/coupons/validate")
async def validate_coupon(data: CouponValidate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM coupons WHERE code = %s AND is_active = 1", (data.code,)
        )
        coupon = cursor.fetchone()
        if not coupon:
            raise HTTPException(status_code=404, detail="Купон не найден или недействителен")

        # Проверка срока
        if coupon.get('expires_at'):
            expires = coupon['expires_at']
            if isinstance(expires, str):
                expires = datetime.strptime(expires, '%Y-%m-%d').date()
            if expires < datetime.now().date():
                raise HTTPException(status_code=400, detail="Срок действия купона истёк")

        # Проверка лимита использований
        if coupon['max_uses'] > 0 and coupon['current_uses'] >= coupon['max_uses']:
            raise HTTPException(status_code=400, detail="Лимит использований купона исчерпан")

        # Проверка музея (если купон привязан к конкретному)
        if coupon['museum_id'] is not None:
            cursor.execute("SELECT code FROM museums WHERE id = %s", (coupon['museum_id'],))
            museum = cursor.fetchone()
            if not museum or museum['code'] != data.museum_code:
                raise HTTPException(status_code=400, detail="Купон недействителен для данного музея")

        return {
            "valid": True,
            "discount_percent": float(coupon['discount_percent']),
            "code": coupon['code']
        }
    finally:
        cursor.close()
        conn.close()


class CouponApply(BaseModel):
    code: str

@app.post("/api/coupons/apply")
async def apply_coupon_usage(data: CouponApply):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE coupons SET current_uses = current_uses + 1 WHERE code = %s", (data.code,))
        conn.commit()
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/super/admins", response_model=List[AdminListItem])
async def get_admins():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id AS museum_id, name AS museum_name, login, admin_full_name, admin_code
            FROM museums
            ORDER BY name
        """)
        admins = cursor.fetchall()
        return [AdminListItem(**a) for a in admins]
    finally:
        cursor.close()
        conn.close()

@app.put("/api/super/admins/{museum_id}")
async def update_admin(museum_id: int, data: AdminUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields, values = [], []
        for field, value in data.dict(exclude_unset=True).items():
            fields.append(f"`{field}` = %s")
            values.append(value)
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(museum_id)
        query = f"UPDATE museums SET {', '.join(fields)} WHERE id = %s"
        cursor.execute(query, values)
        conn.commit()
        return {"success": True}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ==================== ШЕРИНГ БИЛЕТОВ ====================
@app.post("/api/tickets/{ticket_id}/share", response_model=TicketShareResponse)
async def share_ticket(ticket_id: int, request: Request):
    """Создаёт уникальную ссылку для просмотра билета."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Проверяем существование билета
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Билет не найден")

        # Генерируем криптостойкий токен: 8 символов (буквы + цифры)
        alphabet = string.ascii_letters + string.digits
        token = ''.join(secrets.choice(alphabet) for _ in range(8))

        # Сохраняем
        cursor.execute(
            "INSERT INTO shared_tickets (ticket_id, token) VALUES (%s, %s)",
            (ticket_id, token)
        )
        conn.commit()

        # Формируем полную ссылку
        base_url = str(request.base_url).rstrip('/')
        share_url = f"{base_url}/api/shared/{token}"
        return TicketShareResponse(share_url=share_url, token=token)
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/shared/{token}")
async def view_shared_ticket(token: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.ticket_number, t.ticket_type, t.price, t.visit_date, t.visit_time,
                   t.status, v.name as visitor_name, v.surname as visitor_surname,
                   m.name as museum_name
            FROM shared_tickets st
            JOIN tickets t ON st.ticket_id = t.id
            JOIN visitors v ON t.visitor_id = v.id
            JOIN museums m ON t.museum_code = m.code
            WHERE st.token = %s
        """, (token,))
        ticket = cursor.fetchone()
        if not ticket:
            raise HTTPException(status_code=404, detail="Билет не найден")

        visit_date = str(ticket['visit_date']) if ticket.get('visit_date') else None
        visit_time = str(ticket['visit_time']) if ticket.get('visit_time') else None
        ticket_number = ticket['ticket_number']
        # Очищаем ticket_number для безопасного имени файла
        safe_ticket_number = re.sub(r'[^a-zA-Z0-9]', '_', ticket_number)

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Билет в музей</title>
<style>
    body {{ font-family: 'Inter', Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f1f5f9; margin: 0; }}
    .ticket-wrapper {{ background: white; border-radius: 20px; padding: 24px; max-width: 420px; width: 90%; box-shadow: 0 10px 30px rgba(0,0,0,0.1); text-align: center; }}
    .museum-title {{ color: #0da2e7; font-size: 1.8rem; margin-bottom: 0.2em; }}
    .info {{ margin: 20px 0; text-align: left; }}
    .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed #e0e0e0; }}
    .label {{ color: #64748b; font-weight: 500; }}
    .value {{ font-weight: 600; color: #1e293b; }}
    .ticket-number {{ font-family: monospace; font-weight: bold; background: #f0f9ff; padding: 8px 12px; border-radius: 8px; display: inline-block; margin: 10px 0; font-size: 1.1rem; }}
    .barcode-container {{ margin: 20px 0; }}
    .btn {{ background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 10px; font-size: 1rem; cursor: pointer; font-weight: 600; transition: background 0.2s; }}
    .btn:hover {{ background: #2563eb; }}
    .btn:active {{ transform: scale(0.98); }}
    .actions {{ margin-top: 20px; }}
</style>
</head>
<body>
<div class="ticket-wrapper" id="ticket-card">
    <h2 class="museum-title">🎟️ {ticket['museum_name']}</h2>
    <div class="info">
        <div class="info-row"><span class="label">Посетитель:</span> <span class="value">{ticket['visitor_name']} {ticket['visitor_surname'] or ''}</span></div>
        <div class="info-row"><span class="label">Дата:</span> <span class="value">{visit_date or 'Не указана'}</span></div>
        <div class="info-row"><span class="label">Время:</span> <span class="value">{visit_time or 'Не указано'}</span></div>
        <div class="info-row"><span class="label">Тип билета:</span> <span class="value">{ticket['ticket_type']}</span></div>
        <div class="info-row"><span class="label">Цена:</span> <span class="value">{ticket['price']} ₽</span></div>
        <div class="info-row"><span class="label">Статус:</span> <span class="value">{ticket['status'] or 'online'}</span></div>
    </div>
    <div class="ticket-number">№ {ticket_number}</div>
    <div class="barcode-container" id="barcode-container"></div>
    <div class="actions">
        <button class="btn" id="download-btn">Скачать билет</button>
    </div>
</div>

<script src="/libs/html2canvas.min.js"></script>
<script>
(function() {{
    function generateBarcodeDataURL(text, width, height) {{
        return new Promise(resolve => {{
            const canvas = document.createElement('canvas');
            canvas.width = width || 200;
            canvas.height = height || 80;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#000000';
            const barWidth = 2;
            const totalBars = Math.floor(canvas.width / barWidth);
            for (let i = 0; i < totalBars; i++) {{
                const charIndex = i % text.length;
                if (text.charCodeAt(charIndex) % 2 === 0) {{
                    ctx.fillRect(i * barWidth, 0, barWidth, canvas.height);
                }}
            }}
            ctx.fillStyle = '#000';
            ctx.font = 'bold 10px monospace';
            ctx.textAlign = 'center';
            ctx.fillText(text.length > 25 ? text.substring(0,25)+'...' : text, canvas.width/2, canvas.height-5);
            resolve(canvas.toDataURL('image/png'));
        }});
    }}

    const ticketNumber = "{ticket_number}";
    generateBarcodeDataURL(ticketNumber, 280, 80).then(dataUrl => {{
        const img = document.createElement('img');
        img.src = dataUrl;
        img.alt = "Штрихкод";
        img.style.maxWidth = '100%';
        img.style.border = '1px solid #ddd';
        img.style.borderRadius = '6px';
        document.getElementById('barcode-container').appendChild(img);
    }});

    document.getElementById('download-btn').addEventListener('click', async function() {{
        const element = document.getElementById('ticket-card');
        if (typeof html2canvas === 'undefined') {{
            alert('Функция сохранения недоступна. Обновите страницу.');
            return;
        }}
        const canvas = await html2canvas(element, {{
            scale: 2,
            backgroundColor: '#ffffff',
            useCORS: true
        }});
        const link = document.createElement('a');
        link.download = 'ticket_{safe_ticket_number}.png';
        link.href = canvas.toDataURL('image/png');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }});
}})();
</script>
</body>
</html>"""
        return HTMLResponse(content=html)
    finally:
        cursor.close()
        conn.close()
# ============================================================
# ЗАПУСК СЕРВЕРА
# ============================================================
if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("🚀 Starting Museum Ticket System Server...")
    print(f"🌐 Локально: http://localhost:8002")
    print(f"📱 Для телефона/планшета: http://{local_ip}:8002")
    print("📝 Документация API: http://localhost:8002/docs")
    print("=" * 50)
    generate_slots_for_all_active_museums()
    print("✅ Слоты для всех активных музеев обновлены")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info", access_log=True)