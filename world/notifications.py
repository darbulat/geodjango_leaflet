import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


def send_email(subject, body, sender_email, receiver_email, password, fp=None):
    if receiver_email:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        filename = str(datetime.datetime.now()) + '.jpg'
        msgText = MIMEText('<b>%s</b>' % (body), 'html')
        msg.attach(msgText)
        if fp:
            img = MIMEImage(fp.read())
            img.add_header('Content-Disposition', 'attachment',
                           filename=filename)
            msg.attach(img)

        try:
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=5) as smtpObj:
                smtpObj.ehlo()
                smtpObj.starttls()
                smtpObj.login(sender_email, password)
                smtpObj.sendmail(sender_email, receiver_email, msg.as_string())
        except Exception as e:
            print(e)
