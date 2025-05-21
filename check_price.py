import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import pyppeteer # requests-html puede necesitarlo explícitamente
from datetime import datetime # Para la fecha y hora en el correo

PRODUCT_URL = "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

# --- Funciones para el correo ---
def send_email_notification(subject, body_html, recipient_email, sender_email, sender_app_password, smtp_server, smtp_port):
    """Envía una notificación por correo electrónico."""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email

        # Adjuntar parte HTML
        message.attach(MIMEText(body_html, "html"))

        context = ssl.create_default_context() # Para conexión segura
        
        print(f"Intentando enviar correo a: {recipient_email} desde: {sender_email} vía {smtp_server}:{smtp_port}")

        if smtp_port == 465: # Conexión SSL directa
             with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
                server.login(sender_email, sender_app_password)
                server.sendmail(sender_email, recipient_email, message.as_string())
        elif smtp_port == 587: # Conexión TLS/STARTTLS
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context) # Iniciar conexión segura
                server.login(sender_email, sender_app_password)
                server.sendmail(sender_email, recipient_email, message.as_string())
        else:
            print(f"Puerto SMTP no soportado para envío seguro: {smtp_port}. Usar 465 (SSL) o 587 (TLS).")
            return False
            
        print("Correo de notificación enviado exitosamente.")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Error de autenticación SMTP. Verifica el correo del remitente y la contraseña de aplicación.")
        return False
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False

# --- Funciones de Scraping ---
def get_price_value(price_text):
    if price_text:
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            return float(match.group(1).replace(',', ''))
    return None

def extract_product_details(soup):
    """Extrae nombre del producto, precio regular y promocional."""
    product_name = "Producto Desconocido"
    texto_regular_encontrado = None
    texto_promocional_encontrado = None
    regular_esta_tachado = False

    # Intentar extraer el nombre del producto (esto puede necesitar ajuste específico)
    # Opción 1: Buscar por <meta property="og:title" content="...">
    meta_title = soup.find("meta", property="og:title")
    if meta_title and meta_title.get("content"):
        product_name = meta_title["content"].replace("Inkafarma: Más salud al mejor precio | ", "").replace("Inkafarma | ", "").strip()
        # Quitar coletillas comunes si es necesario
        if " - Inkafarma" in product_name: # Ejemplo
            product_name = product_name.split(" - Inkafarma")[0]
    else:
        # Opción 2: Buscar un h1 (común para el título principal)
        h1_tag = soup.find("h1")
        if h1_tag:
            product_name = h1_tag.get_text(strip=True)
    
    # Si el nombre es muy genérico por el meta, podemos refinar más
    if "Inkafarma" in product_name or "Más salud al mejor precio" in product_name:
        # Intentar un selector más específico si el meta title es muy genérico
        # Este selector es una suposición y probablemente necesite ajuste para la página de Inkafarma.
        # Por ejemplo, un div con una clase específica que envuelva el nombre del producto.
        # Ejemplo: title_element = soup.select_one(".product-name-class") # Necesitaríamos la clase real
        # if title_element: product_name = title_element.get_text(strip=True)
        pass # Dejar el nombre extraído del meta o h1 por ahora

    span_regular_element = soup.find("span", string=lambda text: text and "precio regular" in text.strip().lower())
    span_promo_element = soup.find("span", string=lambda text: text and "precio promocional" in text.strip().lower())

    if span_regular_element:
        parent_col_div_regular = span_regular_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div_regular:
            price_sibling_div_regular = parent_col_div_regular.find_next_sibling("div", class_="price-amount")
            if price_sibling_div_regular:
                texto_regular_encontrado = price_sibling_div_regular.get_text(strip=True)
                if "text-strike" in price_sibling_div_regular.get("class", []):
                    regular_esta_tachado = True
    
    if span_promo_element:
        parent_col_div_promo = span_promo_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div_promo:
            price_sibling_div_promo = parent_col_div_promo.find_next_sibling("div", class_="price-amount")
            if price_sibling_div_promo:
                if "text-strike" not in price_sibling_div_promo.get("class", []):
                    texto_promocional_encontrado = price_sibling_div_promo.get_text(strip=True)
    
    return product_name, texto_regular_encontrado, texto_promocional_encontrado, regular_esta_tachado

def check_product_price():
    session = HTMLSession()
    try:
        print(f"Iniciando revisión de precio para: {PRODUCT_URL}")
        response = session.get(PRODUCT_URL, headers=HEADERS, timeout=35)
        response.raise_for_status()

        response.html.render(timeout=45, scrolldown=2, sleep=5)
        
        rendered_html = response.html.html 
        soup = BeautifulSoup(rendered_html, "html.parser")
        
        product_name, texto_regular, texto_promo, regular_tachado = extract_product_details(soup)
        print(f"Producto detectado: {product_name}")

        if texto_promo and texto_regular and regular_tachado:
            valor_regular_num = get_price_value(texto_regular)
            valor_promo_num = get_price_value(texto_promo)

            if valor_regular_num is not None and valor_promo_num is not None:
                print(f"  Precio Regular: {texto_regular} (Valor: {valor_regular_num})")
                print(f"  Precio Promocional: {texto_promo} (Valor: {valor_promo_num})")
                
                if valor_promo_num < valor_regular_num:
                    print("¡PROMOCIÓN DETECTADA!")
                    
                    # Enviar correo
                    sender_email = os.environ.get('SENDER_EMAIL')
                    sender_app_password = os.environ.get('SENDER_APP_PASSWORD')
                    recipient_email = os.environ.get('RECIPIENT_EMAIL')
                    smtp_server = os.environ.get('SMTP_SERVER')
                    smtp_port_str = os.environ.get('SMTP_PORT')

                    if not all([sender_email, sender_app_password, recipient_email, smtp_server, smtp_port_str]):
                        print("Error: Faltan una o más variables de entorno para la configuración del correo.")
                    else:
                        try:
                            smtp_port = int(smtp_port_str) # Convertir puerto a entero
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            email_subject = f"¡Alerta de Promoción: {product_name}!"
                            email_body_html = f"""
                            <html>
                                <body>
                                    <p>¡Se ha detectado una promoción para el producto <strong>{product_name}</strong>!</p>
                                    <p><strong>URL del Producto:</strong> <a href="{PRODUCT_URL}">{PRODUCT_URL}</a></p>
                                    <p><strong>Precio Regular:</strong> {texto_regular}</p>
                                    <p><strong>Precio Promocional:</strong> <font color="green">{texto_promo}</font></p>
                                    <p><em>Revisado el: {current_time} (UTC)</em></p>
                                </body>
                            </html>
                            """
                            send_email_notification(
                                email_subject, email_body_html, recipient_email,
                                sender_email, sender_app_password, smtp_server, smtp_port
                            )
                        except ValueError:
                            print(f"Error: El puerto SMTP ('{smtp_port_str}') no es un número válido.")
                else:
                    print("Promoción encontrada (regular tachado y promocional visible), pero el precio promocional no es menor que el regular.")
            else:
                print("Se encontraron los textos de promoción, pero no se pudieron extraer los valores numéricos.")
        
        elif texto_regular and not texto_promo:
            print(f"Solo se encontró el Precio Regular: '{texto_regular}'. No hay promoción activa.")
        
        else:
            print("No se pudo identificar claramente ni 'Precio regular' ni 'Precio Promocional' con la estructura esperada.")

    except pyppeteer.errors.TimeoutError as e:
        print(f"Error de Timeout durante el renderizado de JavaScript: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error al intentar acceder a la página: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        print(f"Tipo de error: {type(e)}")
    finally:
        session.close()
    print("Revisión de precio finalizada.")

if __name__ == "__main__":
    check_product_price()
