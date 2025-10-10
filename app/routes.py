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

    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Invalid email format"}), 400

    # Check waitlist status
    waitlisted = check_waitlist_status(email)

    # Set price (in GHS)
    price = 130 if waitlisted else 150
    amount_pesewas = int(price * 100)  # convert to pesewas for Paystack

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
        ticket_info = insert_ticket(email, price, reference)

        return jsonify(
            {
                "success": True,
                "data": {
                    "checkout_url": paystack_data["data"]["authorization_url"],
                    "price": price,
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


@bp.route("/verify-payment", methods=["GET"])
def verify_payment():
    reference = request.args.get("reference")

    if not reference:
        return (
            jsonify({"success": False, "error": "Payment reference is required"}),
            400,
        )

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}", headers=headers
        )
        result = response.json()

        if result["data"]["status"] == "success":
            # Update ticket status
            if update_ticket_payment_status(reference):
                # Get ticket details
                ticket = get_ticket_by_reference(reference)
                if ticket:
                    # Prepare email data
                    email_data = {
                        "email": ticket["user_email"],
                        "ticket_code": ticket["ticket_code"],
                        "price": ticket["price"],
                        "event_title": "MIDNIGHT MADNESS III",
                        "event_date": "October 31, 2025",
                        "event_venue": "[Redacted], Accra",
                    }

                    # Send confirmation email
                    email_sent = send_ticket_confirmation_email(email_data)

                    return jsonify(
                        {
                            "success": True,
                            "message": (
                                "Payment verified and confirmation email sent"
                                if email_sent
                                else "Payment verified but email failed to send"
                            ),
                            "status": "success",
                            "ticket_code": ticket["ticket_code"],
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "message": "Payment verified but ticket not found",
                            "status": "success",
                        }
                    )
            else:
                return (
                    jsonify(
                        {"success": False, "error": "Failed to update ticket status"}
                    ),
                    500,
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
