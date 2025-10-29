import resend
import os
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")
VERIFIED_DOMAIN = os.getenv("RESEND_VERIFIED_DOMAIN", "808dtp.com")

recipients = [
    "aaronosebre@gmail.com",
    "abdulwahid2003@icloud.com",
    "pokuaserwaa14@gmail.com",
    "tettehafadi@gmail.com",
    "afinude@gmail.com",
    "amandaxloves7@gmail.com",
    "amyaboa4@gmail.com",
    "andrewsjnr777@gmail.com",
    "gyamfimichelle13@gmail.com",
    "Vdzata@gmail.com",
    "chantellejohnson222@gmail.com",
    "danielleadzanku@gmail.com",
    "delsonbismarck33@gmail.com",
    "edwardofori810@gmail.com",
    "edwardofori1977@gmail.com",
    "e.nyarko4498@gmail.com",
    "maamearabaae7617@gmail.com",
    "ernest.ucheeze07@gmail.com",
    "addoetienne116@gmail.com",
    "faithconteh556@gmail.com",
    "faridazakariya02@gmail.com",
    "feronmi.oseiza@gmail.com",
    "Floizbae@gmail.com",
    "itzztheod@gmail.com",
    "gsafynn@gmail.com",
    "Ghadiagha2001@gmail.com",
    "fattalhassan9@gmail.com",
    "hazelmustapha@gmail.com",
    "Ikennachinelo08@gmail.com",
    "maafok830@gmail.com",
    "jesszmillz@gmail.com",
    "jonathanahuche6@gmail.com",
    "joybandanya@gmail.com",
    "kekeliasamoah898@gmail.com",
    "11424767@wiuc-ghana.edu.gh",
    "krystlekgyau@gmail.com",
    "queenmaguette@gmail.com",
    "laurelnev@icloud.com",
    "AsanteFranklina@gmail.com",
    "medericdalen@gmail.com",
    "michaelkhalipha@gmail.com",
    "michellebonsu7@gmail.com",
    "michelleekong1320@gmail.com",
    "naaodk@gmail.com",
    "mynarkos@gmail.com",
    "princenarh911@icloud.com",
    "nat2002aggo@gmail.com",
    "niciaisimbi18@gmail.com",
    "jujufatimehin@gmail.com",
    "ikennaobiolanna@gmail.com",
    "kofigyamfiboateng1@gmail.com",
    "pearlserwaafrimpong25@gmail.com",
    "PhrinceCharles@gmail.com",
    "ricchmandem@gmail.com",
    "princeyisiwu@gmail.com",
    "priscillaatewen100@gmail.com",
    "Priscillamortey2021@gmail.com",
    "samodaymat@gmail.com",
    "samirasadousamsam@icloud.com",
    "samuelosei2219@icloud.com",
    "nsakeysamuel@gmail.com",
    "steveluguj@gmail.com",
    "shaniquaakafia03@gmail.com",
    "beecham.business@gmail.com",
    "tiamaria1122005@icloud.com",
    "agotracyablo@gmail.com",
    "vanessaboahene8@gmail.com",
    "lifeofzosha@gmail.com",
    "wrighteyram6@gmail.com",
]

subject = "The Meltdown Begins — Accra’s Biggest Halloween Party Awaits"

html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<title>The Meltdown Begins</title>
</head>
<body style="margin:0;padding:0;background-color:#f7f7f7;color:#222;font-family:Arial,sans-serif;">

  <div style="max-width:600px;margin:auto;background:#ffffff;border-radius:8px;padding:30px;line-height:1.6;">
    <h1 style="color:#0e7f2d;text-align:center;letter-spacing:1px;margin-top:0;">
      THE MELTDOWN BEGINS
    </h1>


    <p>Accra’s biggest Halloween party is back and better this year!</p>

    <p>
      This Friday, <strong>31st October 2025</strong>, The Meltdown begins — we’re turning up the heat with our
      <strong>Radioactive theme</strong>, insane energy, and DJs guaranteed to keep the party alive all night long.
    </p>

    <p>
      Expect an explosive DJ lineup headlined by <strong>DJ OJ</strong>, with performances from
      <strong>Khxn DJ</strong>, <strong>Berlin Zac</strong>, and many more. It’s all going down at
      <strong>13 Mankata Avenue, Airport Residential</strong> — right in the centre of Accra.
    </p>

    <p>Costumes are a must, and the best dressed walks away with a mystery prize 🕵🏽‍♀️💀</p>

    <div style="text-align:center;margin:32px 0;">
      <a href="https://midnight-madness.808dtp.com/tickets"
         style="display:inline-block;background-color:#0e7f2d;color:#fff;text-decoration:none;
                padding:12px 20px;border-radius:4px;font-weight:bold;font-size:15px;
                max-width:90%;word-break:break-word;">
        🎟️ Grab Your Early Bird Tickets
      </a>
      <p style="font-size:12px;color:#777;margin-top:6px;">₵50 OFF — Limited time only</p>
    </div>

    <p>
      Let’s make this Halloween one to remember.<br>
      See you in the meltdown zone 💚
    </p>

    <p style="margin-top:25px;color:#555;">
      – Michelle from <strong>808DTP</strong>
    </p>
  </div>

  <p style="text-align:center;font-size:11px;color:#777;margin-top:15px;">
    © 2025 808 DTP. All Rights Reserved. | 
    <a href="mailto:ops@808dtp.com" style="color:#0e7f2d;">ops@808dtp.com</a>
  </p>

</body>
</html>
"""


def send_broadcast():
    for email in recipients:
        try:
            resend.Emails.send(
                {
                    "from": f"Michelle from 808DTP <customerservice@{VERIFIED_DOMAIN}>",
                    "to": [email],
                    "subject": subject,
                    "html": html_content,
                }
            )
            print(f"✅ Email sent to {email}")
        except Exception as e:
            print(f"❌ Failed to send to {email}: {e}")


if __name__ == "__main__":
    print("🚀 Sending broadcast emails...")
    send_broadcast()
    print("🎉 Broadcast complete.")
