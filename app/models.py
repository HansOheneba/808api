import mysql.connector
from mysql.connector import pooling
from flask import current_app
import datetime


def init_db(app):
    # Create a connection pool and store on app.extensions
    dbconfig = {
        "host": app.config.get("MYSQL_HOST"),
        "user": app.config.get("MYSQL_USER"),
        "password": app.config.get("MYSQL_PASSWORD"),
        "database": app.config.get("MYSQL_DB"),
        "charset": "utf8mb4",
    }

    # Use a small pool by default
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
