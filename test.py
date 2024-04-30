import smtplib
from src.settings import PORT, HOST, HOST_USER, HOST_PASSWORD

from email.message import EmailMessage


def send_email_verify():	
	email = EmailMessage()
	email['Subject'] = 'ПРИВЕТ!!!!!!!!!!!'
	email['From'] = HOST_USER
	email['To'] = "tomchuk_marina@mail.ru"
		
	email.set_content("<h1>Привет киса!!!! Как дела?</h1>" , subtype='html')
    
	with smtplib.SMTP_SSL(HOST, PORT) as server:
		server.login(HOST_USER, HOST_PASSWORD)
		server.send_message(email)


send_email_verify()