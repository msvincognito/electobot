import smtplib
import ssl
from email.mime.text import MIMEText


port = 465  # For SSL

def send_message(address, subject, message):
# Create a secure SSL context
    context = ssl.create_default_context()

# Define the message

    sender = "electobot@msvincognito.nl"
    receivers = [address]

    port = 465

    msg = MIMEText(message)

    msg['Subject'] = subject
    msg['From'] = 'electobot@msvincognito.nl'
    msg['To'] = address

    with open('mail_credentials') as file_:
        username, password = file_.read().splitlines()

    with smtplib.SMTP_SSL("mail.msvincognito.nl", port, context=context) as server:
        server.login(username, password)
        server.sendmail("electobot@msvincognito.nl", address,
                        msg.as_string())

