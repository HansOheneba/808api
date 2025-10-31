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
            name VARCHAR(255),
            phone VARCHAR(50),
            price DECIMAL(10,2) NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            quantity INT NOT NULL,
            ticket_type VARCHAR(20) NOT NULL,
            reference VARCHAR(255) NOT NULL UNIQUE,
            payment_status VARCHAR(50) NOT NULL,
            ticket_code VARCHAR(20) NOT NULL UNIQUE,
            promo_code VARCHAR(50) DEFAULT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            final_price DECIMAL(10,2) DEFAULT 0,
            checked_in BOOLEAN DEFAULT FALSE,
            checked_in_at DATETIME DEFAULT NULL,
            checked_in_by VARCHAR(255) DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # Create promo_codes table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            discount_type ENUM('percentage', 'fixed') NOT NULL,
            discount_value DECIMAL(10,2) NOT NULL,
            max_uses INT DEFAULT NULL,
            used_count INT DEFAULT 0,
            valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_until DATETIME DEFAULT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )

    # Create index for better performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_promo_code ON tickets(promo_code)"
    )
    cursor.close()


def get_promo_code(code):
    """Get promo code details and validate it."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM promo_codes 
            WHERE code = %s AND is_active = TRUE 
            AND (valid_until IS NULL OR valid_until >= UTC_TIMESTAMP())
            AND (valid_from IS NULL OR valid_from <= UTC_TIMESTAMP())
            """,
            (code,),
        )
        promo = cursor.fetchone()
        cursor.close()
        return promo
    finally:
        conn.close()


def use_promo_code(code):
    """Increment the used_count for a promo code."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = %s",
            (code,),
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def calculate_discounted_price(base_price, promo_code):
    """Calculate discounted price based on promo code."""
    if not promo_code:
        return base_price, 0

    promo = get_promo_code(promo_code)
    if not promo:
        return base_price, 0

    # Check if promo code has reached max uses
    if promo["max_uses"] and promo["used_count"] >= promo["max_uses"]:
        return base_price, 0

    discount_amount = 0
    if promo["discount_type"] == "percentage":
        discount_amount = base_price * (promo["discount_value"] / 100)
    else:  # fixed amount
        discount_amount = promo["discount_value"]

    # Ensure discount doesn't make price negative
    final_price = max(0, base_price - discount_amount)
    return final_price, discount_amount


def insert_ticket(
    email,
    name,
    phone,
    price,
    reference,
    ticket_type="regular",
    quantity=1,
    total_price=None,
    promo_code=None,
):
    """Insert a new ticket record."""
    conn = get_conn()
    try:
        create_tickets_table(conn)
        cursor = conn.cursor(dictionary=True)
        ticket_code = generate_ticket_code()

        # If total_price is not provided, calculate it
        if total_price is None:
            total_price = price * quantity

        # Calculate discount if promo code provided
        discount_amount = 0
        final_price = total_price

        if promo_code:
            final_price, discount_amount = calculate_discounted_price(
                total_price, promo_code
            )
            # Mark promo code as used
            use_promo_code(promo_code)

        cursor.execute(
            """
            INSERT INTO tickets 
                (user_email, name, phone, price, total_price, quantity, ticket_type, 
                 reference, payment_status, ticket_code, promo_code, discount_amount, final_price) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                email,
                name,
                phone,
                price,
                total_price,
                quantity,
                ticket_type,
                reference,
                "pending",
                ticket_code,
                promo_code,
                discount_amount,
                final_price,
            ),
        )
        conn.commit()

        # Fetch the inserted record
        cursor.execute(
            "SELECT id, ticket_code, ticket_type, quantity, price, total_price, discount_amount, final_price, promo_code FROM tickets WHERE reference = %s",
            (reference,),
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


def get_ticket_by_reference(reference):
    """Get ticket details by reference."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_email, name, phone, price, total_price, quantity, ticket_type, 
                   ticket_code, payment_status, promo_code, discount_amount, final_price,
                   checked_in, checked_in_at, checked_in_by
            FROM tickets WHERE reference = %s
            """,
            (reference,),
        )
        result = cursor.fetchone()
        cursor.close()
        return result
    finally:
        conn.close()


def get_ticket_by_code(ticket_code):
    """Get ticket details by ticket code."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT 
                id,
                user_email,
                name,
                phone,
                ticket_type,
                quantity,
                price,
                payment_status,
                reference,
                ticket_code,
                created_at,
                total_price,
                promo_code,
                discount_amount,
                final_price,
                checked_in,
                checked_in_at,
                checked_in_by
            FROM tickets WHERE ticket_code = %s
            """,
            (ticket_code,),
        )
        result = cursor.fetchone()

        # Convert datetime objects to ISO format for JSON serialization
        if result:
            if result.get("created_at"):
                result["created_at"] = result["created_at"].isoformat()
            if result.get("checked_in_at"):
                result["checked_in_at"] = result["checked_in_at"].isoformat()
            # Convert tinyint(1) to boolean for checked_in
            if "checked_in" in result:
                result["checked_in"] = bool(result["checked_in"])

        cursor.close()
        return result
    finally:
        conn.close()


def check_in_ticket(ticket_code, checked_in_by="admin"):
    """Check in a ticket (mark as used)."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tickets 
            SET checked_in = TRUE, checked_in_at = UTC_TIMESTAMP(), checked_in_by = %s 
            WHERE ticket_code = %s AND checked_in = FALSE
            """,
            (checked_in_by, ticket_code),
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        return affected_rows > 0
    finally:
        conn.close()


def create_promo_code(
    code, discount_type, discount_value, max_uses=None, valid_until=None
):
    """Create a new promo code."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO promo_codes (code, discount_type, discount_value, max_uses, valid_until)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (code, discount_type, discount_value, max_uses, valid_until),
        )
        conn.commit()
        cursor.close()
        return True
    except mysql.connector.Error as e:
        if e.errno == 1062:  # Duplicate entry
            raise ValueError("Promo code already exists")
        raise e
    finally:
        conn.close()


def get_all_promo_codes():
    """Get all promo codes for admin."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
        promos = cursor.fetchall()

        # Convert datetime objects to string for JSON serialization
        for promo in promos:
            if promo.get("created_at"):
                promo["created_at"] = promo["created_at"].isoformat()
            if promo.get("valid_from"):
                promo["valid_from"] = (
                    promo["valid_from"].isoformat() if promo["valid_from"] else None
                )
            if promo.get("valid_until"):
                promo["valid_until"] = (
                    promo["valid_until"].isoformat() if promo["valid_until"] else None
                )

        cursor.close()
        return promos
    finally:
        conn.close()


def get_all_tickets():
    """Get all tickets for admin."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, user_email, name, phone, price, total_price, final_price, discount_amount,
                   quantity, ticket_type, ticket_code, payment_status, promo_code,
                   checked_in, checked_in_at, checked_in_by, created_at
            FROM tickets 
            ORDER BY created_at DESC
        """
        )
        tickets = cursor.fetchall()

        # Convert datetime objects to string for JSON serialization
        for ticket in tickets:
            if ticket.get("created_at"):
                ticket["created_at"] = ticket["created_at"].isoformat()
            if ticket.get("checked_in_at"):
                ticket["checked_in_at"] = ticket["checked_in_at"].isoformat()

        cursor.close()
        return tickets
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


# Add this function to models.py after the existing functions


def create_manual_payments_table(conn):
    """Create manual_payments table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            phone VARCHAR(50) NOT NULL,
            ticket_type VARCHAR(20) NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            final_price DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            promo_code VARCHAR(50) DEFAULT NULL,
            reference_code VARCHAR(10) NOT NULL UNIQUE,
            payment_status ENUM('pending', 'confirmed', 'rejected') DEFAULT 'pending',
            momo_number VARCHAR(20) NOT NULL,
            admin_notes TEXT DEFAULT NULL,
            confirmed_by VARCHAR(255) DEFAULT NULL,
            confirmed_at DATETIME DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cursor.close()


def insert_manual_payment(
    email,
    name,
    phone,
    ticket_type,
    quantity,
    price,
    total_price,
    final_price,
    discount_amount,
    promo_code,
    momo_number,
):
    """Insert a new manual payment record."""
    conn = get_conn()
    try:
        create_manual_payments_table(conn)
        cursor = conn.cursor(dictionary=True)

        # Generate unique short reference code (6 characters)
        reference_code = generate_short_reference_code()

        cursor.execute(
            """
            INSERT INTO manual_payments 
                (user_email, name, phone, ticket_type, quantity, price, total_price, 
                 final_price, discount_amount, promo_code, reference_code, momo_number) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                email,
                name,
                phone,
                ticket_type,
                quantity,
                price,
                total_price,
                final_price,
                discount_amount,
                promo_code,
                reference_code,
                momo_number,
            ),
        )
        conn.commit()

        # Return the reference code
        return reference_code
    finally:
        conn.close()


def generate_short_reference_code():
    """Generate a unique short reference code (4 characters)."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        while True:
            # Generate even shorter code (4 characters)
            chars = string.ascii_uppercase + string.digits
            # Remove similar-looking characters: 0, O, 1, I
            chars = (
                chars.replace("0", "")
                .replace("O", "")
                .replace("1", "")
                .replace("I", "")
            )
            reference_code = "".join(random.choices(chars, k=4)) 

            # Check if code exists in manual_payments
            cursor.execute(
                "SELECT 1 FROM manual_payments WHERE reference_code = %s",
                (reference_code,),
            )
            if not cursor.fetchone():
                cursor.close()
                return reference_code
    finally:
        conn.close()


def get_manual_payment_by_reference(reference_code):
    """Get manual payment details by reference code."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM manual_payments WHERE reference_code = %s
            """,
            (reference_code,),
        )
        result = cursor.fetchone()

        # Convert datetime objects to ISO format
        if result:
            if result.get("created_at"):
                result["created_at"] = result["created_at"].isoformat()
            if result.get("confirmed_at"):
                result["confirmed_at"] = result["confirmed_at"].isoformat()

        cursor.close()
        return result
    finally:
        conn.close()


def get_all_manual_payments():
    """Get all manual payments for admin."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM manual_payments ORDER BY created_at DESC
            """
        )
        payments = cursor.fetchall()

        # Convert datetime objects
        for payment in payments:
            if payment.get("created_at"):
                payment["created_at"] = payment["created_at"].isoformat()
            if payment.get("confirmed_at"):
                payment["confirmed_at"] = payment["confirmed_at"].isoformat()

        cursor.close()
        return payments
    finally:
        conn.close()


def confirm_manual_payment(reference_code, confirmed_by, admin_notes=None):
    """Confirm a manual payment and create ticket."""
    conn = get_conn()
    try:
        cursor = conn.cursor(dictionary=True)

        # Get the manual payment
        cursor.execute(
            "SELECT * FROM manual_payments WHERE reference_code = %s AND payment_status = 'pending'",
            (reference_code,),
        )
        payment = cursor.fetchone()

        if not payment:
            return False, "Payment not found or already processed"

        # Update manual payment status
        cursor.execute(
            """
            UPDATE manual_payments 
            SET payment_status = 'confirmed', confirmed_by = %s, confirmed_at = UTC_TIMESTAMP(),
                admin_notes = %s
            WHERE reference_code = %s
            """,
            (confirmed_by, admin_notes, reference_code),
        )

        # Generate ticket code
        ticket_code = generate_ticket_code()

        # Insert into tickets table
        cursor.execute(
            """
            INSERT INTO tickets 
                (user_email, name, phone, price, total_price, quantity, ticket_type, 
                 reference, payment_status, ticket_code, promo_code, discount_amount, final_price) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                payment["user_email"],
                payment["name"],
                payment["phone"],
                payment["price"],
                payment["total_price"],
                payment["quantity"],
                payment["ticket_type"],
                f"MANUAL-{reference_code}",  # Use manual reference format
                "paid",
                ticket_code,
                payment["promo_code"],
                payment["discount_amount"],
                payment["final_price"],
            ),
        )

        conn.commit()
        cursor.close()
        return True, ticket_code

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def reject_manual_payment(reference_code, confirmed_by, admin_notes=None):
    """Reject a manual payment."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE manual_payments 
            SET payment_status = 'rejected', confirmed_by = %s, confirmed_at = UTC_TIMESTAMP(),
                admin_notes = %s
            WHERE reference_code = %s
            """,
            (confirmed_by, admin_notes, reference_code),
        )
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        return affected_rows > 0
    finally:
        conn.close()
