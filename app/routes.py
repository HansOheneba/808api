from flask import Blueprint, request, jsonify, current_app
from .models import (
    insert_waitlist,
    get_all_waitlist,
    check_waitlist_status,
    insert_ticket,
    update_ticket_payment_status,
    get_ticket_by_reference,
    get_promo_code,
    get_ticket_by_code,
    check_in_ticket,
    create_promo_code,
    get_all_promo_codes,
    get_all_tickets,
)
from .email import send_ticket_confirmation_email
import re
import requests
import os
import datetime

bp = Blueprint("routes", __name__)

# Add CORS headers to all responses
# CORS is handled at the application level in __init__.py


def is_valid_email(email: str) -> bool:
    # simple regex for basic validation
    if not email:
        return False
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


@bp.route("/", methods=["GET"])
def index():
    return jsonify({"success": True, "message": "API is running"})


@bp.route("/waitlist", methods=["GET", "POST", "OPTIONS"])
def waitlist():
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return jsonify({}), 200

    # Handle GET request to retrieve all entries
    if request.method == "GET":
        try:
            entries = get_all_waitlist()
            return jsonify({"success": True, "data": entries}), 200
        except Exception as e:
            current_app.logger.exception("Error retrieving waitlist entries")
            return jsonify({"success": False, "error": "Server error"}), 500

    if not request.is_json:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    data = request.get_json()
    email = data.get("email")
    name = data.get("name")
    phone = data.get("phone")
    referral = data.get("referral")

    if not email:
        return jsonify({"success": False, "error": "'email' is required"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Invalid email format"}), 400

    # optional: basic phone validation
    if phone:
        # allow digits, spaces, + and -
        if not re.match(r"^[0-9 +\-()]+$", phone):
            return jsonify({"success": False, "error": "Invalid phone format"}), 400

    try:
        inserted_id = insert_waitlist(
            email=email, name=name, phone=phone, referral=referral
        )
        return jsonify({"success": True, "id": inserted_id}), 201
    except Exception as e:
        current_app.logger.exception("Error inserting into waitlist")
        # handle duplicate email specifically if possible
        msg = str(e)
        if "Duplicate" in msg or "unique" in msg.lower():
            return jsonify({"success": False, "error": "Email already registered"}), 409
        return jsonify({"success": False, "error": "Server error"}), 500


PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL")


@bp.route("/buy-ticket", methods=["POST"])
def buy_ticket():
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    data = request.get_json()
    email = data.get("email")
    name = data.get("name")
    phone = data.get("phone")
    ticket_type = data.get("ticket_type", "regular").lower()
    quantity = data.get("quantity", 1)
    promo_code = data.get("promo_code")

    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Invalid email format"}), 400

    # Validate required fields
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400

    if not phone:
        return jsonify({"success": False, "error": "Phone is required"}), 400

    # Validate phone format
    if phone and not re.match(r"^[0-9 +\-()]+$", phone):
        return jsonify({"success": False, "error": "Invalid phone format"}), 400

    # Validate ticket_type
    prices = {"early_bird": 100, "regular": 150, "late": 200}
    if ticket_type not in prices:
        return jsonify({"success": False, "error": "Invalid ticket type"}), 400

    # Validate quantity
    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except (TypeError, ValueError):
        quantity = 1

    # Get base price
    price = prices[ticket_type]

    # Calculate total price
    total_price = price * quantity

    # Validate and apply promo code
    discount_amount = 0
    final_price = total_price

    if promo_code:
        promo = get_promo_code(promo_code)
        if not promo:
            return (
                jsonify({"success": False, "error": "Invalid or expired promo code"}),
                400,
            )

        # Check if promo code has reached max uses
        if promo["max_uses"] and promo["used_count"] >= promo["max_uses"]:
            return (
                jsonify(
                    {"success": False, "error": "Promo code has reached maximum uses"}
                ),
                400,
            )

        # Calculate discount
        if promo["discount_type"] == "percentage":
            discount_amount = total_price * (promo["discount_value"] / 100)
        else:  # fixed amount
            discount_amount = promo["discount_value"]

        final_price = max(0, total_price - discount_amount)

    amount_pesewas = int(final_price * 100)  # convert to pesewas for Paystack

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": amount_pesewas,
        "currency": "GHS",
        "callback_url": f"{FRONTEND_URL}/verify",
    }

    try:
        response = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers=headers,
            json=payload,
        )
        paystack_data = response.json()

        if not paystack_data.get("status"):
            return (
                jsonify({"success": False, "error": "Failed to initialize payment"}),
                400,
            )

        reference = paystack_data["data"]["reference"]

        # Insert ticket record and get ticket info
        ticket_info = insert_ticket(
            email=email,
            name=name,
            phone=phone,
            price=price,
            total_price=total_price,
            quantity=quantity,
            ticket_type=ticket_type,
            reference=reference,
            promo_code=promo_code,
        )

        # Check waitlist status
        waitlisted = check_waitlist_status(email)

        return jsonify(
            {
                "success": True,
                "data": {
                    "checkout_url": paystack_data["data"]["authorization_url"],
                    "price": price,
                    "total_price": total_price,
                    "final_price": final_price,
                    "discount_amount": discount_amount,
                    "quantity": quantity,
                    "ticket_type": ticket_type,
                    "waitlisted": waitlisted,
                    "ticket_code": ticket_info["ticket_code"],
                    "promo_code": promo_code,
                },
            }
        )

    except Exception as e:
        current_app.logger.exception("Error processing ticket purchase")
        return (
            jsonify(
                {"success": False, "error": "Server error processing ticket purchase"}
            ),
            500,
        )


@bp.route("/verify-payment", methods=["GET", "OPTIONS"])
def verify_payment():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    reference = request.args.get("reference")
    if not reference:
        return (
            jsonify({"success": False, "error": "Payment reference is required"}),
            400,
        )

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    try:
        # ✅ Verify payment with Paystack API
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}", headers=headers
        )
        result = response.json()

        if result.get("data", {}).get("status") == "success":
            # ✅ Get ticket first to check current status
            ticket = get_ticket_by_reference(reference)

            if not ticket:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Ticket not found for this reference",
                        }
                    ),
                    404,
                )

            # ✅ Update ticket status only if it's still pending
            email_sent = False
            if ticket.get("payment_status") == "pending":
                if update_ticket_payment_status(reference):
                    # Refresh ticket data after update
                    ticket = get_ticket_by_reference(reference)

                    # ✅ Send confirmation email only for newly verified payments
                    email_data = {
                        "email": ticket["user_email"],
                        "name": ticket.get("name", ""),
                        "ticket_code": ticket["ticket_code"],
                        "price": ticket["price"],
                        "total_price": ticket["total_price"],
                        "final_price": ticket.get("final_price", ticket["total_price"]),
                        "discount_amount": ticket.get("discount_amount", 0),
                        "quantity": ticket["quantity"],
                        "ticket_type": ticket["ticket_type"],
                        "promo_code": ticket.get("promo_code"),
                        "event_title": "MIDNIGHT MADNESS III",
                        "event_date": "October 31, 2025",
                        "event_venue": "[Redacted], Accra",
                    }

                    email_sent = send_ticket_confirmation_email(email_data)
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Failed to update ticket status",
                            }
                        ),
                        500,
                    )
            else:
                # Ticket is already paid/verified - log this but don't resend email
                current_app.logger.info(
                    f"Ticket already in status: {ticket.get('payment_status')}"
                )
                email_sent = True  # Assume email was already sent

            # ✅ Always return success if Paystack verification passed
            return jsonify(
                {
                    "success": True,
                    "message": (
                        "Payment verified and confirmation email sent"
                        if email_sent
                        else "Payment verified but email sending failed"
                    ),
                    "status": "verified",
                    "ticket_code": ticket["ticket_code"],
                    "payment_status": ticket.get("payment_status", "unknown"),
                    "email_sent": email_sent,
                }
            )

        else:
            return (
                jsonify({"success": False, "error": "Payment verification failed"}),
                400,
            )

    except Exception as e:
        current_app.logger.exception("Error verifying payment")
        return (
            jsonify({"success": False, "error": "Server error verifying payment"}),
            500,
        )


@bp.route("/check-ticket/<ticket_code>", methods=["GET"])
def check_ticket(ticket_code):
    """Check ticket details and validity."""
    try:
        ticket = get_ticket_by_code(ticket_code)
        if not ticket:
            return jsonify({"success": False, "error": "Ticket not found"}), 404

        return jsonify(
            {
                "success": True,
                "data": {
                    "id": ticket["id"],
                    "ticket_code": ticket["ticket_code"],
                    "name": ticket["name"],
                    "email": ticket["user_email"],
                    "phone": ticket["phone"],
                    "ticket_type": ticket["ticket_type"],
                    "quantity": ticket["quantity"],
                    "price": ticket["price"],
                    "total_price": ticket["total_price"],
                    "payment_status": ticket["payment_status"],
                    "reference": ticket["reference"],
                    "created_at": ticket["created_at"],
                    "promo_code": ticket.get("promo_code"),
                    "discount_amount": ticket.get("discount_amount", 0),
                    "final_price": ticket.get("final_price", ticket["total_price"]),
                    "checked_in": ticket["checked_in"],
                    "checked_in_at": ticket["checked_in_at"],
                    "checked_in_by": ticket["checked_in_by"],
                },
            }
        )
    except Exception as e:
        current_app.logger.exception("Error checking ticket")
        return jsonify({"success": False, "error": "Server error"}), 500


@bp.route("/check-in/<ticket_code>", methods=["POST"])
def check_in_ticket_route(ticket_code):
    """Check in a ticket (mark as used)."""
    try:
        # Get admin/staff identifier from request
        data = request.get_json() or {}
        checked_in_by = data.get("checked_in_by", "admin")

        ticket = get_ticket_by_code(ticket_code)
        if not ticket:
            return jsonify({"success": False, "error": "Ticket not found"}), 404

        if ticket["payment_status"] != "paid":
            return jsonify({"success": False, "error": "Ticket not paid"}), 400

        if ticket["checked_in"]:
            return (
                jsonify({"success": False, "error": "Ticket already checked in"}),
                400,
            )

        success = check_in_ticket(ticket_code, checked_in_by)
        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "Ticket checked in successfully",
                    "data": {
                        "ticket_code": ticket_code,
                        "checked_in_at": datetime.datetime.utcnow().isoformat(),
                        "checked_in_by": checked_in_by,
                    },
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to check in ticket"}),
                500,
            )

    except Exception as e:
        current_app.logger.exception("Error checking in ticket")
        return jsonify({"success": False, "error": "Server error"}), 500


@bp.route("/admin/promo-codes", methods=["GET", "POST"])
def promo_codes_route():
    """Admin endpoints for promo codes."""
    if request.method == "GET":
        try:
            promos = get_all_promo_codes()
            return jsonify({"success": True, "data": promos}), 200
        except Exception as e:
            current_app.logger.exception("Error retrieving promo codes")
            return jsonify({"success": False, "error": "Server error"}), 500

    elif request.method == "POST":
        if not request.is_json:
            return jsonify({"success": False, "error": "JSON body required"}), 400

        data = request.get_json()
        code = data.get("code")
        discount_type = data.get("discount_type")
        discount_value = data.get("discount_value")
        max_uses = data.get("max_uses")
        valid_until = data.get("valid_until")

        # Validate required fields
        if not code or not discount_type or discount_value is None:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Code, discount_type, and discount_value are required",
                    }
                ),
                400,
            )

        if discount_type not in ["percentage", "fixed"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Discount type must be 'percentage' or 'fixed'",
                    }
                ),
                400,
            )

        try:
            discount_value = float(discount_value)
            if discount_value <= 0:
                raise ValueError
            if discount_type == "percentage" and discount_value > 100:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Percentage discount cannot exceed 100%",
                        }
                    ),
                    400,
                )
        except (TypeError, ValueError):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Discount value must be a positive number",
                    }
                ),
                400,
            )

        try:
            create_promo_code(
                code, discount_type, discount_value, max_uses, valid_until
            )
            return jsonify(
                {"success": True, "message": "Promo code created successfully"}
            )
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            current_app.logger.exception("Error creating promo code")
            return jsonify({"success": False, "error": "Server error"}), 500


@bp.route("/admin/tickets", methods=["GET"])
def admin_tickets_route():
    """Admin endpoint to get all tickets."""
    try:
        tickets = get_all_tickets()
        return jsonify({"success": True, "data": tickets}), 200
    except Exception as e:
        current_app.logger.exception("Error retrieving tickets")
        return jsonify({"success": False, "error": "Server error"}), 500


@bp.route("/validate-promo", methods=["POST"])
def validate_promo():
    """Validate a promo code and return discount details."""
    if not request.is_json:
        return jsonify({"success": False, "error": "JSON body required"}), 400

    data = request.get_json()
    promo_code = data.get("promo_code")
    total_amount = data.get("total_amount", 0)

    if not promo_code:
        return jsonify({"success": False, "error": "Promo code is required"}), 400

    try:
        promo = get_promo_code(promo_code)
        if not promo:
            return (
                jsonify({"success": False, "error": "Invalid or expired promo code"}),
                400,
            )

        # Check if promo code has reached max uses
        if promo["max_uses"] and promo["used_count"] >= promo["max_uses"]:
            return (
                jsonify(
                    {"success": False, "error": "Promo code has reached maximum uses"}
                ),
                400,
            )

        # Calculate discount
        discount_amount = 0
        if promo["discount_type"] == "percentage":
            discount_amount = total_amount * (promo["discount_value"] / 100)
        else:  # fixed amount
            discount_amount = promo["discount_value"]

        final_price = max(0, total_amount - discount_amount)

        return jsonify(
            {
                "success": True,
                "data": {
                    "code": promo["code"],
                    "discount_type": promo["discount_type"],
                    "discount_value": promo["discount_value"],
                    "discount_amount": discount_amount,
                    "final_price": final_price,
                    "max_uses": promo["max_uses"],
                    "used_count": promo["used_count"],
                },
            }
        )

    except Exception as e:
        current_app.logger.exception("Error validating promo code")
        return jsonify({"success": False, "error": "Server error"}), 500
