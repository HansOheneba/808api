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
        ticket_code = ticket_data["ticket_code"]
        price = ticket_data["price"]
        event_title = ticket_data.get("event_title", "MIDNIGHT MADNESS III")
        event_date = ticket_data.get("event_date", "October 31, 2025")
        event_venue = ticket_data.get("event_venue", "[REDACTED], Accra")

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="color-scheme" content="dark light" />
  <meta name="supported-color-schemes" content="dark light" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Access Confirmed: {event_title}</title>
  <style>
    body {{
      background-color: #000000;
      color: #c0c0c0;
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      padding: 40px 20px;
    }}
    .card {{
      background-color: #111111;
      border-radius: 8px;
      padding: 30px;
    }}
    .accent {{
      color: #00ff00;
    }}
    .divider {{
      border: none;
      border-top: 1px solid #333;
      margin: 24px 0;
    }}
    code {{
      color: #00ff00;
      font-size: 20px;
      font-weight: bold;
    }}

    /* LIGHT MODE VARIANT */
    @media (prefers-color-scheme: light) {{
      body {{
        background-color: #f9f9f9 !important;
        color: #111 !important;
      }}
      .card {{
        background-color: #ffffff !important;
        border: 1px solid #e5e5e5;
      }}
      .accent {{
        color: #00c800 !important;
      }}
      .divider {{
        border-top: 1px solid #ddd;
      }}
      code {{
        background-color: #f3f3f3;
        border: 1px solid #ccc;
        color: #009900;
      }}
    }}
  </style>
</head>
<body>
  <table align="center" width="100%" cellpadding="0" cellspacing="0" role="presentation">
    <tr>
      <td>
        <div class="container" style="text-align: center;">
          <h1 style="font-size: 24px; font-weight: 900; letter-spacing: 2px;" class="accent">ACCESS GRANTED</h1>
          <p style="font-size: 14px; letter-spacing: 1px; color: #888;">TRANSMISSION: FILE 003</p>
        </div>

        <div class="container">
          <div class="card">
            <h2 class="accent" style="font-size: 18px; text-transform: uppercase; letter-spacing: 1px;">{event_title}</h2>
            <p style="font-size: 14px; margin-top: 10px;">{event_date} — {event_venue}</p>
            <hr class="divider" />

            <h3 style="font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">Ticket Code</h3>
            <div style="margin: 16px 0; border: 1px solid #00ff00; background-color: #000000; padding: 12px; border-radius: 6px; text-align: center;">
              <code>{ticket_code}</code>
            </div>

            <p style="font-size: 14px;">Amount Paid: <span class="accent">GHS {price}</span></p>

            <p style="margin-top: 24px; font-size: 13px; color: #888;">
              Keep this code safe. It will be required for entry verification at the gate.
            </p>
          </div>
        </div>

        <div class="container" style="text-align: center; padding-top: 30px;">
          <p style="font-size: 12px; color: #666;">
            This transmission was issued by <span class="accent">808 DTP</span>.<br>
            For operational inquiries, contact <a href="mailto:ops@808dtp.com" class="accent" style="text-decoration: none;">ops@808dtp.com</a>
          </p>
          <p style="font-size: 11px; color: #333; margin-top: 10px;">© 2025 808 DTP. All Rights Reserved.</p>
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

        return True

    except Exception as e:
        current_app.logger.error(f"Error sending ticket confirmation email: {str(e)}")
        return False
