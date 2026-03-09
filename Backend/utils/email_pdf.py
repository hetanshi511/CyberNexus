import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import logging

logger = logging.getLogger("api")

def send_raw_pdf_email(pdf_bytes: bytes, to_email: str, subject: str = "Your Generated Report"):
    """Sends an externally generated PDF blob as an email attachment."""
    logger.info(f"Sending raw PDF email to {to_email}...")
    
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    
    if not smtp_server:
        logger.info(f"SMTP variables not configured. Skipping raw email to {to_email}.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user or "noreply@invinsense.local"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        body = "Hello!\n\nPlease find the attached report generated from the Invinsense AI Agent dashboard.\n\nBest,\nInvinsense AI Agent"
        msg.attach(MIMEText(body, 'plain'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_bytes)
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename=Dashboard_Report.pdf'
        )
        msg.attach(part)
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)
        
        server.send_message(msg)
        server.quit()
        logger.info("Raw PDF Email sent successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send raw PDF email to {to_email}: {e}")
        return False
