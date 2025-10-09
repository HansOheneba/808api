import mysql.connector
from mysql.connector import pooling
from flask import current_app
import datetime
import random
import string


def init_db(app):
    # Create a connection pool and store on app.extensions
    dbconfig = {
        "host": app.config.get("MYSQL_HOST"),
        "user": app.config.get("MYSQL_USER"),
        "password": app.config.get("MYSQL_PASSWORD"),
        "database": app.config.get("MYSQL_DB"),
        "charset": "utf8mb4",
    }

    pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)
    app.extensions = getattr(app, "extensions", {})
    app.extensions["db_pool"] = pool


def get_conn():
    pool = current_app.extensions.get("db_pool")
    if pool is None:
        raise RuntimeError("DB pool is not initialized")
    return pool.get_connection()


def insert_waitlist(email, name=None, phone=None, referral=None):
    """Insert into waitlist table. Returns inserted id."""
    conn = get_conn()
    try:
        cursor = conn.cursor()

        # Ensure table exists (simple idempotent create)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS waitlist (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255),
                phone VARCHAR(50),
                referral VARCHAR(255),
                created_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        now = datetime.datetime.utcnow()
        cursor.execute(
            "INSERT INTO waitlist (email, name, phone, referral, created_at) VALUES (%s, %s, %s, %s, %s)",
            (email, name, phone, referral, now),
        )
        conn.commit()
        inserted_id = cursor.lastrowid
        cursor.close()
        return inserted_id
    finally:
        conn.close()


def get_all_waitlist():
    """Retrieve all entries from the waitlist table."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
        cursor.execute("SELECT * FROM waitlist ORDER BY created_at DESC")
        entries = cursor.fetchall()

        # Convert datetime objects to string for JSON serialization
        for entry in entries:
            if entry.get("created_at"):
                entry["created_at"] = entry["created_at"].isoformat()

        cursor.close()
        return entries
    finally:
        conn.close()


def create_tickets_table(conn):
    """Create tickets table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            reference VARCHAR(255) NOT NULL UNIQUE,
            payment_status VARCHAR(50) NOT NULL,
            ticket_code VARCHAR(20) NOT NULL UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cursor.close()


def insert_ticket(email, price, reference):
    """Insert a new ticket record."""
    conn = get_conn()
    try:
        create_tickets_table(conn)
        cursor = conn.cursor(dictionary=True)
        ticket_code = generate_ticket_code()
        cursor.execute(
            """
            INSERT INTO tickets 
                (user_email, price, reference, payment_status, ticket_code) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (email, price, reference, "pending", ticket_code),
        )
        conn.commit()

        # Fetch the inserted record
        cursor.execute(
            "SELECT id, ticket_code FROM tickets WHERE reference = %s", (reference,)
        )
        result = cursor.fetchone()
        cursor.close()
        return result
    finally:
        conn.close()


def update_ticket_payment_status(reference, status="paid"):
    """Update ticket payment status."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tickets SET payment_status = %s WHERE reference = %s",
            (status, reference),
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        return affected_rows > 0
    finally:
        conn.close()


def check_waitlist_status(email):
    """Check if an email exists in waitlist."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM waitlist WHERE email = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        return bool(result)
    finally:
        conn.close()


def generate_ticket_code():
    """Generate a unique ticket code in the format MM-XXXXXX."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        while True:
            # Generate random code
            random_chars = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            ticket_code = f"MM-{random_chars}"

            # Check if code exists
            cursor.execute(
                "SELECT 1 FROM tickets WHERE ticket_code = %s", (ticket_code,)
            )
            if not cursor.fetchone():
                cursor.close()
                return ticket_code
    finally:
        conn.close()
