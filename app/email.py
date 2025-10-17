import resend
from flask import current_app


def send_ticket_confirmation_email(ticket_data):
    """
    Send confirmation email after successful ticket payment
    Supports both light and dark mode with Gmail fallback
    """
    try:
        resend.api_key = current_app.config["RESEND_API_KEY"]
        verified_domain = current_app.config["RESEND_VERIFIED_DOMAIN"]

        user_email = ticket_data["email"]
        user_name = ticket_data.get("name", "Guest")
        ticket_code = ticket_data["ticket_code"]
        price = ticket_data["price"]
        total_price = ticket_data.get("total_price", price)
        quantity = ticket_data.get("quantity", 1)
        ticket_type = (
            ticket_data.get("ticket_type", "regular").replace("_", " ").title()
        )
        event_title = ticket_data.get("event_title", "MIDNIGHT MADNESS III")
        event_date = ticket_data.get("event_date", "October 31, 2025")
        event_venue = ticket_data.get("event_venue", "[REDACTED], Accra")

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Access Confirmed: {event_title}</title>
</head>
<body style="margin:0; padding:0; background-color:#0a0a0a; color:#e0e0e0; font-family:'Segoe UI',Arial,sans-serif;">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" role="presentation">
    <tr>
      <td>
        <div style="max-width:600px;margin:0 auto;padding:40px 20px;text-align:center;">
          <h1 style="color:#00ff66;font-size:24px;font-weight:900;letter-spacing:2px;">ACCESS GRANTED</h1>
          <p style="font-size:13px;letter-spacing:1px;color:#8a8a8a;">TRANSMISSION: FILE 003</p>
        </div>

        <div style="max-width:600px;margin:0 auto;padding:0 20px;">
          <div style="background-color:#121212;border-radius:8px;padding:30px;border:1px solid #1a1a1a;">
            <h2 style="color:#00ff66;font-size:18px;text-transform:uppercase;letter-spacing:1px;margin-top:0;">{event_title}</h2>
            <p style="font-size:14px;margin-top:10px;color:#bbb;">{event_date} — {event_venue}</p>
            <hr style="border:none;border-top:1px solid #2b2b2b;margin:20px 0;" />

            <h3 style="color:#00ff66;font-size:15px;text-transform:uppercase;letter-spacing:1px;">Ticket Details</h3>
            <p style="font-size:14px;color:#e0e0e0;">Name: <span style="color:#00ff66;">{user_name}</span></p>
            <p style="font-size:14px;color:#e0e0e0;">Ticket Type: <span style="color:#00ff66;">{ticket_type}</span></p>
            <p style="font-size:14px;color:#e0e0e0;">Quantity: <span style="color:#00ff66;">{quantity}</span></p>

            <h3 style="color:#00ff66;font-size:15px;text-transform:uppercase;letter-spacing:1px;margin-top:20px;">Ticket Code</h3>
            <div style="margin:16px 0;border:1px solid #00ff66;background-color:#000;padding:12px;border-radius:6px;text-align:center;">
              <code style="color:#00ff66;font-size:20px;font-weight:bold;font-family:'Consolas',monospace;">{ticket_code}</code>
            </div>

            <p style="font-size:14px;color:#e0e0e0;">Amount Paid: <span style="color:#00ff66;">GHS {total_price}</span></p>

            <p style="margin-top:24px;font-size:12px;color:#888;">
              Keep this code safe. It will be required for entry verification at the gate.
            </p>
          </div>
        </div>

        <div style="max-width:600px;margin:0 auto;text-align:center;padding:30px 20px;">
          <p style="font-size:12px;color:#777;">
            This transmission was issued by <span style="color:#00ff66;">808 DTP</span>.<br>
            For operational inquiries, contact <a href="mailto:ops@808dtp.com" style="color:#00ff66;text-decoration:none;">ops@808dtp.com</a>
          </p>
          <p style="font-size:11px;color:#555;margin-top:10px;">© 2025 808 DTP. All Rights Reserved.</p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        resend.Emails.send(
            {
                "from": f"808 DTP <noreply@{verified_domain}>",
                "to": [user_email],
                "subject": f"ACCESS GRANTED // {ticket_code}",
                "html": html_content,
            }
        )

        current_app.logger.info(
            f"Confirmation email sent to {user_email} for ticket {ticket_code}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Error sending ticket confirmation email: {str(e)}")
        return False
