import resend
from flask import current_app
from datetime import datetime


def send_ticket_confirmation_email(ticket_data):
    """
    Send confirmation email after successful ticket payment
    """
    try:
        resend.api_key = current_app.config["RESEND_API_KEY"]
        verified_domain = current_app.config["RESEND_VERIFIED_DOMAIN"]

        user_email = ticket_data["email"]
        ticket_code = ticket_data["ticket_code"]
        price = ticket_data["price"]
        event_title = ticket_data.get("event_title", "MIDNIGHT MADNESS")
        event_date = ticket_data.get("event_date", "October 31, 2025")
        event_venue = ticket_data.get("event_venue", "Location Classified")

        html_content = f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Access Confirmed: {event_title}</title>
  </head>
  <body style="background-color: #000000; color: #c0c0c0; font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0;">
    <table align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto;">
      <tr>
        <td style="padding: 40px 20px; text-align: center;">
          <h1 style="font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #00ff00; margin-bottom: 10px;">ACCESS GRANTED</h1>
          <p style="font-size: 14px; letter-spacing: 1px; color: #888;">TRANSMISSION: FILE 003</p>
        </td>
      </tr>

      <tr>
        <td style="background-color: #111111; border-radius: 8px; padding: 30px;">
          <h2 style="color: #00ff00; font-size: 18px; text-transform: uppercase; letter-spacing: 1px;">{event_title}</h2>
          <p style="font-size: 14px; margin-top: 10px;">{event_date} — {event_venue}</p>
          <hr style="border: none; border-top: 1px solid #333; margin: 24px 0;">

          <h3 style="color: #c0c0c0; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">Ticket Code</h3>
          <div style="margin: 16px 0; background-color: #000000; border: 1px solid #00ff00; padding: 12px; border-radius: 6px; text-align: center;">
            <code style="color: #00ff00; font-size: 20px; font-weight: bold;">{ticket_code}</code>
          </div>

          <p style="font-size: 14px; color: #c0c0c0;">Amount Paid: <span style="color: #00ff00;">GHS {price}</span></p>

          <p style="margin-top: 24px; color: #888; font-size: 13px;">
            Keep this code safe. It will be required for entry verification at the gate.
          </p>
        </td>
      </tr>

      <tr>
        <td style="padding: 30px 20px; text-align: center;">
          <p style="font-size: 12px; color: #666;">
            This transmission was issued by <span style="color: #00ff00;">Midnight Madness III</span>.<br>
            For operational inquiries, contact <a href="mailto:ops@midnightmadness.com" style="color: #00ff00; text-decoration: none;">ops@midnightmadness.com</a>
          </p>
          <p style="font-size: 11px; color: #333; margin-top: 10px;">© 2025 Midnight Madness III. All Rights Reserved.</p>
        </td>
      </tr>
    </table>
  </body>
</html>
        """

        resend.Emails.send(
            {
                "from": f"Midnight Madness III <noreply@{verified_domain}>",
                "to": [user_email],
                "subject": f"ACCESS GRANTED // {ticket_code}",
                "html": html_content,
            }
        )

        return True

    except Exception as e:
        current_app.logger.error(f"Error sending ticket confirmation email: {str(e)}")
        return False
