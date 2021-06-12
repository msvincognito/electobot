import smtplib
import ssl
from email.mime.text import MIMEText



def send_message(address, subject, message):
    # Create a secure SSL context
    context = ssl.create_default_context()

    # Define the message

    receivers = [address]

    with open('mail_credentials') as file_:
        server_address, port, username, password, sender_email = file_.read().splitlines()
    
    msg = MIMEText(message)

    msg['Subject'] = subject
    msg['From'] = "Electobot"
    msg['To'] = address

    
    port = int(port)
    with smtplib.SMTP_SSL(server_address, port, context=context) as server:
        server.login(username, password)
        server.sendmail(sender_email, address,
                        msg.as_string())

