from flask import Blueprint, request, jsonify, current_app
from .models import (
    insert_waitlist,
    get_all_waitlist,
    check_waitlist_status,
    insert_ticket,
    update_ticket_payment_status,
    get_ticket_by_reference,
)
from .email import send_ticket_confirmation_email
import re
import requests
import os

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


@bp.route("/waitlist", methods=["GET", "POST", "OPTIONS"])  # Add GET method
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
    amount_pesewas = int(total_price * 100)  # convert to pesewas for Paystack

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
                    "quantity": quantity,
                    "ticket_type": ticket_type,
                    "waitlisted": waitlisted,
                    "ticket_code": ticket_info["ticket_code"],
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
            # ✅ Update ticket status if still pending
            ticket = get_ticket_by_reference(reference)

            if ticket and ticket.get("payment_status") == "pending":
                update_ticket_payment_status(reference)
                # Refresh ticket data
                ticket = get_ticket_by_reference(reference)

            # ✅ Always return success if Paystack verification passed
            return jsonify(
                {
                    "success": True,
                    "message": "Payment verified successfully",
                    "status": "verified",
                    "ticket_code": ticket["ticket_code"] if ticket else None,
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
