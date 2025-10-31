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
        event_venue = ticket_data.get("event_venue", "13 Mankata Ave, Accra")

        # Static map image (no iframe, works in all email clients)
        # You can replace the `key=` part with your actual Google Maps Static API key
        map_image_url = (
            "https://maps.googleapis.com/maps/api/staticmap?"
            "center=13+Mankata+Ave,Accra,Ghana"
            "&zoom=15"
            "&size=600x300"
            "&maptype=roadmap"
            "&markers=color:green%7C13+Mankata+Ave,Accra,Ghana"
            "&key=YOUR_GOOGLE_MAPS_API_KEY"
        )

        # Clickable link to open in Google Maps
        maps_link = (
            "https://goo.gl/maps/2JkB5W7bi7hP99GQ9"  # (short link for 13 Mankata Ave)
        )

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

            <hr style="border:none;border-top:1px solid #2b2b2b;margin:30px 0;" />

            <h3 style="color:#00ff66;font-size:15px;text-transform:uppercase;letter-spacing:1px;">Location</h3>
            <p style="font-size:14px;color:#bbb;">13 Mankata Ave, Accra</p>
            <a href="{maps_link}" target="_blank" style="display:inline-block;text-decoration:none;">
              <img src="{map_image_url}" alt="Event Location Map" width="100%" style="border-radius:8px;border:2px solid #00ff66;display:block;margin-top:10px;" />
            </a>

            <p style="margin-top:10px;font-size:12px;color:#888;">
              Click the map to open directions in Google Maps.
            </p>

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


def send_manual_payment_notification(payment_data):
    """
    Send notification to admins when someone attempts a manual ticket purchase
    """
    try:
        resend.api_key = current_app.config["RESEND_API_KEY"]
        verified_domain = current_app.config["RESEND_VERIFIED_DOMAIN"]

        # Send to both admins
        admin_emails = ["beecham.business@gmail.com", "hansopoku360@gmail.com"]

        user_email = payment_data["email"]
        user_name = payment_data["name"]
        user_phone = payment_data["phone"]
        reference_code = payment_data["reference_code"]
        amount = payment_data["amount"]
        ticket_type = payment_data["ticket_type"].replace("_", " ").title()
        quantity = payment_data["quantity"]
        momo_number = payment_data["momo_number"]
        created_at = payment_data["created_at"]

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Manual Payment Request - {reference_code}</title>
</head>
<body style="margin:0; padding:0; background-color:#f8fafc; color:#334155; font-family:'Segoe UI',Arial,sans-serif;">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" role="presentation">
    <tr>
      <td>
        <div style="max-width:600px;margin:0 auto;padding:30px 20px;">
          <div style="background-color:#ffffff;border-radius:12px;padding:40px;border:1px solid#e2e8f0;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="text-align:center;margin-bottom:30px;">
              <h1 style="color:#dc2626;font-size:24px;font-weight:700;margin:0 0 8px 0;">⚠️ MANUAL PAYMENT REQUEST</h1>
              <p style="color:#64748b;font-size:14px;margin:0;">Action Required: Verify MoMo Payment</p>
            </div>

            <!-- Alert Box -->
            <div style="background-color:#fef2f2;border:1px solid#fecaca;border-radius:8px;padding:16px;margin-bottom:24px;">
              <p style="color:#dc2626;font-size:14px;font-weight:600;margin:0;">
                Please check your MoMo transactions and confirm receipt of payment
              </p>
            </div>

            <!-- Payment Details -->
            <div style="margin-bottom:24px;">
              <h2 style="color:#1e293b;font-size:18px;font-weight:600;margin-bottom:16px;">Payment Details</h2>
              
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Reference Code</p>
                  <p style="color:#1e293b;font-size:16px;font-weight:600;margin:0;font-family:'Courier New',monospace;">{reference_code}</p>
                </div>
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Amount Expected</p>
                  <p style="color:#dc2626;font-size:16px;font-weight:700;margin:0;">GHS {amount}</p>
                </div>
              </div>

              <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">MoMo Number</p>
                  <p style="color:#1e293b;font-size:16px;font-weight:600;margin:0;">{momo_number}</p>
                </div>
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Request Time</p>
                  <p style="color:#1e293b;font-size:14px;font-weight:500;margin:0;">{created_at}</p>
                </div>
              </div>
            </div>

            <!-- Customer Information -->
            <div style="margin-bottom:24px;">
              <h2 style="color:#1e293b;font-size:18px;font-weight:600;margin-bottom:16px;">Customer Information</h2>
              
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:12px;">
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Full Name</p>
                  <p style="color:#1e293b;font-size:15px;font-weight:500;margin:0;">{user_name}</p>
                </div>
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Phone</p>
                  <p style="color:#1e293b;font-size:15px;font-weight:500;margin:0;">{user_phone}</p>
                </div>
              </div>

              <div>
                <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Email</p>
                <p style="color:#1e293b;font-size:15px;font-weight:500;margin:0;">{user_email}</p>
              </div>
            </div>

            <!-- Ticket Information -->
            <div style="margin-bottom:32px;">
              <h2 style="color:#1e293b;font-size:18px;font-weight:600;margin-bottom:16px;">Ticket Information</h2>
              
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Ticket Type</p>
                  <p style="color:#1e293b;font-size:15px;font-weight:500;margin:0;">{ticket_type}</p>
                </div>
                <div>
                  <p style="color:#64748b;font-size:13px;margin:0 0 4px 0;">Quantity</p>
                  <p style="color:#1e293b;font-size:15px;font-weight:500;margin:0;">{quantity}</p>
                </div>
              </div>
            </div>

            <!-- Action Required -->
            <div style="background-color:#f0f9ff;border:1px solid#bae6fd;border-radius:8px;padding:20px;">
              <h3 style="color:#0369a1;font-size:16px;font-weight:600;margin:0 0 12px 0;">📋 Action Required</h3>
              <ol style="color:#1e293b;font-size:14px;margin:0;padding-left:20px;">
                <li style="margin-bottom:8px;">Check your MoMo transactions for <strong>GHS {amount}</strong></li>
                <li style="margin-bottom:8px;">Look for reference code: <strong>{reference_code}</strong></li>
                <li style="margin-bottom:8px;">Go to Admin Panel → Manual tab</li>
                <li style="margin-bottom:8px;">Click "Confirm" if payment received, or "Reject" if not</li>
              </ol>
            </div>

          </div>

          <!-- Footer -->
          <div style="text-align:center;padding:24px 20px 0 20px;">
            <p style="color:#94a3b8;font-size:12px;margin:0;">
              This is an automated notification from the 808 DTP ticketing system.<br>
              Please do not reply to this email.
            </p>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        resend.Emails.send(
            {
                "from": f"808 DTP Notifications <noreply@{verified_domain}>",
                "to": admin_emails,
                "subject": f"Manual Payment Request - {reference_code} - GHS {amount}",
                "html": html_content,
            }
        )

        current_app.logger.info(
            f"Manual payment notification sent to admins for reference {reference_code}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Error sending manual payment notification: {str(e)}")
        return False
