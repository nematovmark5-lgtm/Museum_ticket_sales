from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import mysql.connector
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Museum Ticket System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
async def serve_homepage():
    """Отдаем HTML-страницу"""
    try:
        if os.path.exists("index.html"):
            return FileResponse("index.html", media_type="text/html")
        else:
            return {"message": "Museum Ticket System API is running", "status": "healthy"}
    except Exception as e:
        logger.error(f"Error serving homepage: {e}")
        return {"message": "Museum Ticket System API is running", "status": "healthy"}


@app.get("/api/time-slots/{museum_code}/{date}", response_model=List[TimeSlotResponse])
async def get_time_slots(museum_code: str, date: str):
    """Получить доступные временные слоты для музея на указанную дату"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT code FROM museums WHERE code = %s", (museum_code,))
        museum = cursor.fetchone()

        if not museum:
            raise HTTPException(status_code=404, detail="Музей не найден")

        cursor.execute("""
            SELECT 
                id, museum_code, date, start_time, end_time, 
                available_tickets
            FROM time_slots 
            WHERE museum_code = %s AND date = %s
            ORDER BY start_time
        """, (museum_code, date))

        slots = cursor.fetchall()

        formatted_slots = []
        for slot in slots:
            formatted_slot = {
                'id': slot['id'],
                'museum_code': slot['museum_code'],
                'date': str(slot['date']),
                'start_time': str(slot['start_time']),
                'end_time': str(slot['end_time']),
                'available_tickets': slot['available_tickets']
            }
            formatted_slots.append(formatted_slot)

        return [TimeSlotResponse(**slot) for slot in formatted_slots]

    except mysql.connector.Error as e:
        logger.error(f"Database error in get_time_slots: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_time_slots: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/time-slots/reserve")
async def reserve_time_slot(reservation: TimeSlotReserve):
    """Временное резервирование билетов (проверка доступности)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, available_tickets 
            FROM time_slots 
            WHERE museum_code = %s AND date = %s AND start_time = %s
        """, (reservation.museum_code, reservation.date, reservation.start_time))

        slot = cursor.fetchone()

        if not slot:
            raise HTTPException(status_code=404, detail="Временной слот не найден")

        available_tickets = slot['available_tickets']

        if available_tickets < reservation.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно билетов. Доступно: {available_tickets}, запрошено: {reservation.quantity}"
            )

        return {
            "available": True,
            "available_tickets": available_tickets,
            "requested_quantity": reservation.quantity,
            "message": "Билеты доступны для бронирования"
        }

    except mysql.connector.Error as e:
        logger.error(f"Database error in reserve_time_slot: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in reserve_time_slot: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/time-slots/confirm-payment")
async def confirm_payment_and_reserve(confirmation: TimeSlotConfirm):
    """Подтверждение оплаты и окончательное резервирование билетов"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute("""
            SELECT id, available_tickets 
            FROM time_slots 
            WHERE museum_code = %s AND date = %s AND start_time = %s
            FOR UPDATE
        """, (confirmation.museum_code, confirmation.date, confirmation.start_time))

        slot = cursor.fetchone()

        if not slot:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Временной слот не найден")

        available_tickets = slot['available_tickets']

        if available_tickets < confirmation.quantity:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно билетов. Доступно: {available_tickets}, запрошено: {confirmation.quantity}"
            )

        cursor.execute("""
            UPDATE time_slots 
            SET available_tickets = available_tickets - %s 
            WHERE id = %s
        """, (confirmation.quantity, slot['id']))

        cursor.execute("SELECT id FROM visitors WHERE id = %s", (confirmation.visitor_id,))
        visitor = cursor.fetchone()

        if not visitor:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        conn.commit()

        return {
            "success": True,
            "reserved_quantity": confirmation.quantity,
            "remaining_tickets": available_tickets - confirmation.quantity,
            "message": "Билеты успешно забронированы"
        }

    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Database error in confirm_payment_and_reserve: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in confirm_payment_and_reserve: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/time-slots/cancel-reservation")
async def cancel_reservation(reservation: TimeSlotReserve):
    """Отмена резервирования билетов"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute("""
            SELECT id, available_tickets 
            FROM time_slots 
            WHERE museum_code = %s AND date = %s AND start_time = %s
            FOR UPDATE
        """, (reservation.museum_code, reservation.date, reservation.start_time))

        slot = cursor.fetchone()

        if not slot:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Временной слот не найден")

        cursor.execute("""
            UPDATE time_slots 
            SET available_tickets = available_tickets + %s 
            WHERE id = %s
        """, (reservation.quantity, slot['id']))

        conn.commit()

        return {
            "success": True,
            "cancelled_quantity": reservation.quantity,
            "message": "Бронирование успешно отменено"
        }

    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Database error in cancel_reservation: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in cancel_reservation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.get("/api/health")
async def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/api/museums/mapping")
async def get_museums_mapping():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, code FROM museums")
        museums = cursor.fetchall()

        mapping = {museum['code']: museum['id'] for museum in museums}
        return mapping

    except mysql.connector.Error as e:
        logger.error(f"Database error in get_museums_mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_museums_mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/sales/", response_model=SaleResponse)
async def create_sale(sale: SaleCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        logger.info(f"Получены данные для sales: {sale.dict()}")

        cursor.execute("SELECT id FROM museums WHERE id = %s", (sale.museums_id,))
        museum = cursor.fetchone()

        if not museum:
            logger.error(f"Музей с ID {sale.museums_id} не найден")
            raise HTTPException(status_code=404, detail="Музей не найден")

        query = """
        INSERT INTO sales (museums_id, quantity_tickets_sold, income, date, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            sale.museums_id,
            sale.quantity_tickets_sold,
            sale.income,
            sale.date,
            sale.status
        ))
        conn.commit()

        sale_id = cursor.lastrowid

        cursor.execute("SELECT * FROM sales WHERE id = %s", (sale_id,))
        new_sale = cursor.fetchone()

        if new_sale['date'] and hasattr(new_sale['date'], 'isoformat'):
            new_sale['date'] = new_sale['date'].isoformat()
        elif new_sale['date']:
            new_sale['date'] = str(new_sale['date'])

        logger.info(f"Продажа успешно записана с ID: {sale_id}")
        return SaleResponse(**new_sale)

    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Ошибка базы данных при создании продажи: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Неожиданная ошибка при создании продажи: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/visitors/", response_model=VisitorResponse)
async def create_visitor(visitor: VisitorCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM visitors WHERE login = %s", (visitor.login,))
        existing_visitor = cursor.fetchone()

        if existing_visitor:
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

        query = """
        INSERT INTO visitors (login, password, name, surname, phone) 
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            visitor.login,
            visitor.password,
            visitor.name,
            visitor.surname,
            visitor.phone
        ))
        conn.commit()

        visitor_id = cursor.lastrowid

        cursor.execute("SELECT * FROM visitors WHERE id = %s", (visitor_id,))
        new_visitor = cursor.fetchone()

        return VisitorResponse(**new_visitor)

    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Database error in create_visitor: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in create_visitor: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/visitors/login/", response_model=VisitorResponse)
async def login_visitor(credentials: VisitorLogin):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM visitors WHERE login = %s AND password = %s",
                       (credentials.login, credentials.password))
        visitor = cursor.fetchone()

        if not visitor:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")

        return VisitorResponse(**visitor)

    except mysql.connector.Error as e:
        logger.error(f"Database error in login_visitor: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in login_visitor: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.post("/api/tickets/", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, name, surname, phone FROM visitors WHERE id = %s", (ticket.visitor_id,))
        visitor = cursor.fetchone()

        if not visitor:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        cursor.execute("SELECT code, name FROM museums WHERE code = %s", (ticket.museum_code,))
        museum = cursor.fetchone()

        museum_name = museum['name'] if museum else "Неизвестный музей"

        query = """
        INSERT INTO tickets (
            ticket_number, visitor_id, ticket_type, price, museum_code, 
            quantity, visit_date, visit_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            ticket.ticket_number,
            ticket.visitor_id,
            ticket.ticket_type,
            ticket.price,
            ticket.museum_code,
            ticket.quantity,
            ticket.visit_date,
            ticket.visit_time
        ))
        conn.commit()

        ticket_id = cursor.lastrowid

        new_ticket = {
            "id": ticket_id,
            "ticket_number": ticket.ticket_number,
            "visitor_id": ticket.visitor_id,
            "visitor_name": visitor['name'],
            "visitor_surname": visitor['surname'],
            "visitor_phone": visitor['phone'],
            "museum_name": museum_name,
            "museum_code": ticket.museum_code,
            "ticket_type": ticket.ticket_type,
            "price": ticket.price,
            "quantity": ticket.quantity,
            "visit_date": ticket.visit_date,
            "visit_time": ticket.visit_time,
            "issued_at": datetime.now()
        }

        return TicketResponse(**new_ticket)

    except mysql.connector.Error as e:
        conn.rollback()
        logger.error(f"Database error in create_ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error in create_ticket: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.get("/api/tickets/{visitor_id}", response_model=List[TicketResponse])
async def get_visitor_tickets(visitor_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM visitors WHERE id = %s", (visitor_id,))
        visitor = cursor.fetchone()

        if not visitor:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        cursor.execute("""
            SELECT 
                t.id,
                t.ticket_number,
                t.visitor_id,
                t.ticket_type,
                t.price,
                t.museum_code,
                t.quantity,
                DATE(t.visit_date) as visit_date,
                TIME(t.visit_time) as visit_time,
                t.issued_at,
                t.check,  -- ← ДОБАВЬТЕ ЭТУ СТРОКУ
                v.name as visitor_name, 
                v.surname as visitor_surname, 
                v.phone as visitor_phone, 
                COALESCE(m.name, 'Неизвестный музей') as museum_name
            FROM tickets t 
            JOIN visitors v ON t.visitor_id = v.id 
            LEFT JOIN museums m ON t.museum_code = m.code
            WHERE t.visitor_id = %s 
            ORDER BY t.issued_at DESC
        """, (visitor_id,))

        tickets = cursor.fetchall()

        formatted_tickets = []
        for ticket in tickets:
            formatted_ticket = {
                "id": ticket["id"],
                "ticket_number": ticket["ticket_number"],
                "visitor_id": ticket["visitor_id"],
                "visitor_name": ticket["visitor_name"],
                "visitor_surname": ticket["visitor_surname"],
                "visitor_phone": ticket["visitor_phone"],
                "museum_name": ticket["museum_name"],
                "museum_code": ticket["museum_code"],
                "ticket_type": ticket["ticket_type"],
                "price": float(ticket["price"]),
                "quantity": ticket["quantity"],
                "visit_date": str(ticket["visit_date"]) if ticket["visit_date"] else None,
                "visit_time": str(ticket["visit_time"]) if ticket["visit_time"] else None,
                "issued_at": ticket["issued_at"].isoformat() if hasattr(ticket["issued_at"], 'isoformat') else str(ticket["issued_at"]),
                "check": ticket["check"]
            }
            formatted_tickets.append(formatted_ticket)

        return [TicketResponse(**ticket) for ticket in formatted_tickets]

    except mysql.connector.Error as e:
        logger.error(f"Database error in get_visitor_tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_visitor_tickets: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    finally:
        cursor.close()
        conn.close()


@app.get("/api/test/database")
async def test_database():
    """Тестовый эндпоинт для проверки подключения к БД"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) as count FROM museums")
        museums_count = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as count FROM visitors")
        visitors_count = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as count FROM tickets")
        tickets_count = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as count FROM time_slots")
        time_slots_count = cursor.fetchone()

        return {
            "status": "success",
            "tables": {
                "museums": museums_count['count'],
                "visitors": visitors_count['count'],
                "tickets": tickets_count['count'],
                "time_slots": time_slots_count['count']
            },
            "database": "connected"
        }

    except Exception as e:
        logger.error(f"Test database error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/test/museums")
async def test_museums():
    """Тестовый эндпоинт для проверки музеев"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, code, name, ticket_price FROM museums")
        museums = cursor.fetchall()
        return {"museums": museums}
    except Exception as e:
        logger.error(f"Test museums error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn

    try:
        print("🚀 Starting Museum Ticket System Server...")
        print("📊 Database: museum_system")
        print("🌐 Server will run on: http://localhost:8002")
        print("📝 API Documentation: http://localhost:8002/docs")
        print("🏠 HTML Interface: http://localhost:8002")
        print("=" * 50)

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8002,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Possible solutions:")
        print("   1. Check if MySQL is running")
        print("   2. Check if port 8002 is available (netstat -an | grep 8002)")
        print("   3. Verify database credentials in get_db_connection()")
        print("   4. Check if database 'museum_system' exists")