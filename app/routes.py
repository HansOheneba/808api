from flask import Blueprint, request, jsonify, current_app
from .models import insert_waitlist
import re

bp = Blueprint("routes", __name__)


def is_valid_email(email: str) -> bool:
    # simple regex for basic validation
    if not email:
        return False
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


@bp.route("/", methods=["GET"])
def index():
    return jsonify({"success": True, "message": "API is running"})


@bp.route("/waitlist", methods=["POST"])
def waitlist():
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
