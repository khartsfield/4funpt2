# Part of the code's Source: https://www.geeksforgeeks.org/send-mail-attachment-gmail-account-using-python/

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(sender, receiver, email_password):

    # instance of MIMEMultipart
    msg = MIMEMultipart()

    # storing the senders email address
    msg['From'] = sender

    # storing the receivers email address
    msg['To'] = receiver

    # storing the subject
    msg['Subject'] = "Solubility Measurement Experiment Failure"

    # string to store the body of the mail
    body = "Experiment failure due to the reason of beaker is full before the saturation point is reached."

    # attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

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

