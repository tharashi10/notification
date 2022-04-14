# coding: utf-8
import requests
import sys,codecs
import json
import csv
import base64
import sys
import os
import hashlib
import ConfigParser
import logging
import time
import datetime
import smtplib 
import email.utils
from email.message import EmailMessage
import ssl

SUBJECT = 'Email Delivery Test (Python smtplib)'
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Email Delivery SMTP Email Test</h1>
  <p>This email was sent with Email Delivery using the
    <a href='https://www.python.org/'>Python</a>
    <a href='https://docs.python.org/3/library/smtplib.html'>
    smtplib</a> library.</p>
</body>
</html>"""

def usage():
    print("Usage: notify.py <config file>")

class MessageService():
    def send_msg(self, SUBJECT, SENDERNAME, SENDER, RECIPIENT, BODY_HTML,
        HOST, PORT, USERNAME_SMTP, password_smtp):
        msg = EmailMessage()
        msg['Subject'] = SUBJECT
        msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
        msg['To'] = RECIPIENT
        msg.add_alternative(BODY_HTML, subtype='html')

        try: 
            server = smtplib.SMTP(HOST, PORT)
            server.ehlo()

            # most python runtimes default to a set of trusted public CAs that will include the CA used by OCI Email Delivery.
            # However, on platforms lacking that default (or with an outdated set of CAs), customers may need to provide a capath that includes our public CA.
            server.starttls(context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=None, capath=None))
            
            # smtplib docs recommend calling ehlo() before & after starttls()
            server.ehlo()
            server.login(USERNAME_SMTP, password_smtp)
            
            # our requirement is that SENDER is the same as From address set previously
            server.sendmail(SENDER, RECIPIENT, msg.as_string())
            server.close()
        
        # Display an error message if something goes wrong.
        except Exception as e:
            print(f"Error: {e}")
        else:
            print("Email successfully sent!")

if __name__ == "__main__":

    # Read Config
    config_ini = ConfigParser.ConfigParser()
    config_ini.read(sys.argv[1])

    # get the password from a named config file ociemail.config
    with open(PASSWORD_SMTP_FILE) as f:
        password_smtp = f.readline().strip()

    SENDERNAME = config_ini['DEFAULT']['SENDERNAME']
    SENDER = config_ini['DEFAULT']['SENDER']
    RECIPIENT = config_ini['DEFAULT']['RECIPIENT']
    HOST = config_ini['DEFAULT']['HOST']
    PORT = config_ini['DEFAULT']['PORT']
    USERNAME_SMTP = config_ini['DEFAULT']['USERNAME_SMTP']

    MessageService = MessageService()
    MessageService.send_msg(SUBJECT, SENDERNAME, SENDER, RECIPIENT, BODY_HTML,
        HOST, PORT, USERNAME_SMTP, password_smtp)
