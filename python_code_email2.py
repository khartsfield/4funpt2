# Part of the code's Source: https://www.geeksforgeeks.org/send-mail-attachment-gmail-account-using-python/

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def email_info_check(email_info):
    while True:
        print(email_info)
        print("Are all the input information correct? ")
        ans = str(input("Enter Y, y, Yes, YES, or yes for yes; N, n, No, NO, or no for no: "))
        if ans == "Y" or ans == "Yes" or ans == "yes" or ans == "YES" or ans == "y":
            break
        elif ans == "N" or ans == "No" or ans == "NO" or ans == "no" or ans == "n":
            while True:
                print("0 is for sender, 1 is for receiver, 2 is for email password")
                position = int(input("position number in the email info list: "))
                if position < 0:
                    print("Error: position number cannot be negative ")
                elif position > 2:
                    print("Error: position number is too large, does not exist in the data list ")
                else:
                    break
            info = input("correct information: ")
            email_info[position] = info
        else:
            print("Please only enter Y, y, Yes, YES, or yes for yes; N, n, No, NO, or no ")


def send_email_attachment(filename, sender, receiver, email_password):
    # sender = input("Email address of the sender:")
    # receiver = input("Email address of the receiver:")

    # instance of MIMEMultipart
    msg = MIMEMultipart()

    # storing the senders email address
    msg['From'] = sender

    # storing the receivers email address
    msg['To'] = receiver

    # storing the subject
    msg['Subject'] = "Solubility Measurement Experiment Data"

    # string to store the body of the mail
    body = "Solubility measurement experiment data recorded from the automated measurement system."

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

