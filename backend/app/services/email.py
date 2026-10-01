import smtplib
from email.message import EmailMessage
from app.core.config import settings
from app.core.errors import DomainError

def send_email(to_email: str, subject: str, text_body: str):
    """Send an email using SMTP. If SMTP_HOST is empty, print to console (mock)."""
    if not settings().smtp_host:
        if settings().environment != 'production':
            print('--- EMAIL MOCK ---')
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"Body: {text_body}")
            print('------------------')
            return
        else:
            print(f"WARNING: Email not sent to {to_email} (SMTP_HOST is not configured).")
            return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings().smtp_from
    msg['To'] = to_email
    msg.set_content(text_body)

    try:
        if settings().smtp_port in [465]:
            # SSL
            server = smtplib.SMTP_SSL(settings().smtp_host, settings().smtp_port, timeout=10)
        else:
            # TLS
            server = smtplib.SMTP(settings().smtp_host, settings().smtp_port, timeout=10)
            server.starttls()
            
        if settings().smtp_user and settings().smtp_password:
            server.login(settings().smtp_user, settings().smtp_password)
            
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        # In a real app we might not want to throw a 500 here if it's async, but 
        # raising it prevents the user from thinking the email was successfully sent.
        raise DomainError('email_failed', 'Could not dispatch email. Please try again later.')
