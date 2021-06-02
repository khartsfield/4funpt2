# Source: https://www.geeksforgeeks.org/send-mail-attachment-gmail-account-using-python/

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def send_email(filename, sender, receiver, email_password):
    # sender = input("Email address of the sender:")
    # receiver = input("Email address of the receiver:")

    # instance of MIMEMultipart
    msg = MIMEMultipart()

    # storing the senders email address
    msg['From'] = sender

    # storing the receivers email address
    msg['To'] = receiver

    # storing the subject
    msg['Subject'] = "Solubility Measurement Experiment Failure Alert, Data attached"

    # string to store the body of the mail
    body = "Experiment failure due to the reason of beaker is full before the saturation point is reached."

    # attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    # open the file to be sent
    attachment = open(filename, "rb")

    # instance of MIMEBase and named as p
    p = MIMEBase('application', 'octet-stream')

    # To change the payload into encoded form
    p.set_payload((attachment).read())

    # encode into base64
    encoders.encode_base64(p)

    p.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    # attach the instance 'p' to instance 'msg'
    msg.attach(p)

    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    s.starttls()

    # Authentication
    # email_password = input("Enter the sender's email password:")
    s.login(sender, email_password)

    # Converts the Multipart msg into a string
    text = msg.as_string()

    # sending the mail
    s.sendmail(sender, receiver, text)

    # terminating the session
    s.quit()
    print("Successfully sent the email")

