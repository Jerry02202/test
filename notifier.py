# notifier.py

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_notification(subject, body_html, recipient_email, 
                            sender_email, sender_app_password, 
                            smtp_server, smtp_port):
    """Envía una notificación por correo electrónico."""
    if not all([sender_email, sender_app_password, recipient_email, smtp_server, smtp_port]):
        print("Error: Faltan una o más variables de entorno para la configuración del correo al intentar enviar.")
        return False
        
    try:
        # Convertir puerto a entero, ya que desde las variables de entorno viene como string
        smtp_port_int = int(smtp_port)
    except ValueError:
        print(f"Error: El puerto SMTP ('{smtp_port}') no es un número válido.")
        return False

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email

        message.attach(MIMEText(body_html, "html"))
        context = ssl.create_default_context()
        
        print(f"Notifier: Intentando enviar correo a: {recipient_email} desde: {sender_email} vía {smtp_server}:{smtp_port_int}")

        if smtp_port_int == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port_int, context=context) as server:
                server.login(sender_email, sender_app_password)
                server.sendmail(sender_email, recipient_email, message.as_string())
        elif smtp_port_int == 587:
            with smtplib.SMTP(smtp_server, smtp_port_int) as server:
                server.starttls(context=context)
                server.login(sender_email, sender_app_password)
                server.sendmail(sender_email, recipient_email, message.as_string())
        else:
            print(f"Notifier: Puerto SMTP no soportado para envío seguro: {smtp_port_int}. Usar 465 (SSL) o 587 (TLS).")
            return False
            
        print("Notifier: Correo de notificación enviado exitosamente.")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Notifier: Error de autenticación SMTP. Verifica el correo del remitente y la contraseña de aplicación.")
        return False
    except Exception as e:
        print(f"Notifier: Error al enviar el correo: {e}")
        return False
