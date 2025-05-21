# main.py

import os
from datetime import datetime
import config  # Importa nuestro archivo de configuración
import scraper # Importa nuestro módulo scraper
import notifier # Importa nuestro módulo notifier

def process_product(product_url):
    """
    Procesa un solo producto: obtiene datos, verifica promoción y notifica si es necesario.
    """
    print(f"Main: Procesando URL: {product_url}")
    product_data = scraper.fetch_product_data(product_url, config.DEFAULT_HEADERS)

    if not product_data:
        print(f"Main: No se pudieron obtener datos para {product_url}. Revisar logs del scraper.")
        return

    print(f"Main: Producto detectado: {product_data.get('name', 'Desconocido')}")
    
    promo_price_val = product_data.get("promo_price_value")
    regular_price_val = product_data.get("regular_price_value")
    is_striked = product_data.get("is_regular_price_striked")
    
    promo_price_text = product_data.get("promo_price_text")
    regular_price_text = product_data.get("regular_price_text")

    if promo_price_val is not None and regular_price_val is not None and is_striked:
        print(f"  Precio Regular: {regular_price_text} (Valor: {regular_price_val})")
        print(f"  Precio Promocional: {promo_price_text} (Valor: {promo_price_val})")

        if promo_price_val < regular_price_val:
            print("Main: ¡PROMOCIÓN DETECTADA!")
            
            # Recuperar credenciales y configuración de correo desde variables de entorno
            sender_email = os.environ.get('SENDER_EMAIL')
            sender_app_password = os.environ.get('SENDER_APP_PASSWORD')
            recipient_email = os.environ.get('RECIPIENT_EMAIL')
            smtp_server = os.environ.get('SMTP_SERVER')
            smtp_port = os.environ.get('SMTP_PORT') # Se pasa como string, notifier lo convierte

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            product_name_for_email = product_data.get('name', 'Producto') # Fallback si el nombre es None
            
            email_subject = f"¡Alerta de Promoción: {product_name_for_email}!"
            email_body_html = f"""
            <html>
                <body>
                    <p>¡Se ha detectado una promoción para el producto <strong>{product_name_for_email}</strong>!</p>
                    <p><strong>URL del Producto:</strong> <a href="{product_data.get('url', '#')}">{product_data.get('url', 'No disponible')}</a></p>
                    <p><strong>Precio Regular:</strong> {regular_price_text}</p>
                    <p><strong>Precio Promocional:</strong> <font color="green">{promo_price_text}</font></p>
                    <p><em>Revisado el: {current_time} (UTC)</em></p>
                </body>
            </html>
            """
            
            notifier.send_email_notification(
                email_subject, email_body_html, recipient_email,
                sender_email, sender_app_password, smtp_server, smtp_port
            )
        else:
            print("Main: Promoción encontrada, pero el precio promocional no es menor que el regular.")
    elif regular_price_val is not None:
        print(f"Main: Solo se encontró el Precio Regular: '{regular_price_text}'. No hay promoción activa.")
    else:
        print("Main: No se pudo identificar claramente la estructura de precios esperada.")

def run_checker():
    print("Main: Iniciando el comprobador de precios...")
    if not config.PRODUCT_URLS:
        print("Main: No hay URLs de productos configuradas en config.py. Saliendo.")
        return

    for url in config.PRODUCT_URLS:
        process_product(url)
        print("-" * 30) # Separador entre productos

    print("Main: Comprobador de precios finalizado.")

if __name__ == "__main__":
    run_checker()
