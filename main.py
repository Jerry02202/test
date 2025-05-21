# main.py

import os
import json # Para manejar el archivo de estado JSON
from datetime import datetime
import config
import scraper
import notifier

STATE_FILE_PATH = "product_states.json" # Nombre del archivo de estado

# Constantes para los tipos de oferta (para consistencia)
OFFER_TYPE_OH = "Exclusivo oh! y oh! pay"
OFFER_TYPE_PROMO = "Precio Promocional"
OFFER_TYPE_REGULAR = "Precio regular" # O "Sin Oferta"

def load_product_states():
    """Carga los estados de los productos desde el archivo JSON."""
    if os.path.exists(STATE_FILE_PATH):
        try:
            with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Main: Error al decodificar {STATE_FILE_PATH}. Se creará uno nuevo si es necesario.")
            return {} # Devuelve vacío si el archivo está corrupto
    return {}

def save_product_states(states):
    """Guarda los estados de los productos en el archivo JSON."""
    try:
        with open(STATE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(states, f, indent=4, ensure_ascii=False)
        print(f"Main: Estados de los productos guardados en {STATE_FILE_PATH}")
    except IOError as e:
        print(f"Main: Error al guardar estados en {STATE_FILE_PATH}: {e}")


def determine_best_offer(product_data):
    """Determina la mejor oferta actual y su tipo basado en la jerarquía."""
    oh_price = product_data.get("oh_price_value")
    promo_price = product_data.get("promo_price_value")
    regular_price = product_data.get("regular_price_value") # Lo usamos para saber si hay algún precio

    if oh_price is not None:
        return OFFER_TYPE_OH, oh_price, product_data.get("oh_price_text")
    elif promo_price is not None and product_data.get("is_regular_price_striked"): # Asegurar que el regular esté tachado para promo
        return OFFER_TYPE_PROMO, promo_price, product_data.get("promo_price_text")
    elif regular_price is not None: # Si solo hay regular (o los otros no son válidos)
        return OFFER_TYPE_REGULAR, regular_price, product_data.get("regular_price_text")
    else:
        return None, None, None # No se encontraron precios válidos


def process_product(product_url, product_states):
    print(f"Main: Procesando URL: {product_url}")
    product_data = scraper.fetch_product_data(product_url, config.DEFAULT_HEADERS)

    if not product_data:
        print(f"Main: No se pudieron obtener datos para {product_url}.")
        return False # Indica que no se pudo procesar para no intentar guardar estado inválido

    product_name_scraped = product_data.get('name', 'Producto Desconocido')
    print(f"Main: Producto detectado: {product_name_scraped}")
    
    current_best_offer_type, current_best_price, current_best_price_text = determine_best_offer(product_data)
    
    # Obtener precios de referencia para el cuerpo del correo
    regular_price_text_for_email = product_data.get("regular_price_text", "N/A")
    promo_price_text_for_email = product_data.get("promo_price_text", "N/A")
    oh_price_text_for_email = product_data.get("oh_price_text", "N/A")


    # Cargar estado anterior para esta URL
    last_state = product_states.get(product_url, {})
    last_notified_type = last_state.get("last_notified_type")
    last_notified_price = last_state.get("last_notified_price")

    send_notification = False
    notification_reason = ""

    if current_best_offer_type == OFFER_TYPE_REGULAR or current_best_offer_type is None:
        print(f"Main: Solo se encontró el precio regular ({current_best_price_text}) o ningún precio válido. No se enviará notificación.")
        # Actualizar estado si la última vez fue una oferta mejor y ahora es solo regular
        if last_notified_type and last_notified_type != OFFER_TYPE_REGULAR:
            product_states[product_url] = {
                "last_notified_type": OFFER_TYPE_REGULAR, # O None si current_best_offer_type es None
                "last_notified_price": current_best_price, # O None
                "last_checked_timestamp": datetime.now().isoformat()
            }
            print(f"Main: Estado actualizado para {product_url} a 'Solo Regular' o 'Sin Precio'.")
            return True # Indica que el estado cambió y debe guardarse
    else: # Tenemos una oferta (OH o Promocional)
        if not last_notified_type or last_notified_type == OFFER_TYPE_REGULAR:
            send_notification = True
            notification_reason = f"Nueva oferta '{current_best_offer_type}' detectada."
        elif current_best_offer_type != last_notified_type:
            send_notification = True
            notification_reason = f"Tipo de oferta cambió de '{last_notified_type}' a '{current_best_offer_type}'."
        elif current_best_offer_type == last_notified_type and current_best_price != last_notified_price:
            send_notification = True
            notification_reason = f"Precio de '{current_best_offer_type}' cambió de S/ {last_notified_price} a S/ {current_best_price}."
        else:
            print(f"Main: La oferta '{current_best_offer_type}' a S/ {current_best_price} es la misma que la última vez. No se notifica.")

    if send_notification:
        print(f"Main: {notification_reason} ¡Notificando!")
        
        sender_email = os.environ.get('SENDER_EMAIL')
        sender_app_password = os.environ.get('SENDER_APP_PASSWORD')
        recipient_email = os.environ.get('RECIPIENT_EMAIL')
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = os.environ.get('SMTP_PORT')

        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        email_subject = f"¡Alerta de Promoción: {product_name_scraped}!"
        
        # Cuerpo del correo dinámico según la mejor oferta
        body_intro = f"<p>¡Se ha detectado una promoción para el producto <strong>{product_name_scraped}</strong>!</p>"
        body_url = f"<p><strong>URL del Producto:</strong> <a href=\"{product_data.get('url', '#')}\">{product_data.get('url', 'No disponible')}</a></p>"
        
        if current_best_offer_type == OFFER_TYPE_OH:
            body_price_details = f"""
                <p><strong>Precio Exclusivo oh! y oh! pay:</strong> <font color="red">{oh_price_text_for_email}</font></p>
                <p><em>(Precio Promocional de referencia: {promo_price_text_for_email})</em></p>
                <p><em>(Precio Regular de referencia: {regular_price_text_for_email})</em></p>
            """
        elif current_best_offer_type == OFFER_TYPE_PROMO:
            body_price_details = f"""
                <p><strong>Precio Promocional:</strong> <font color="green">{promo_price_text_for_email}</font></p>
                <p><em>(Precio Regular de referencia: {regular_price_text_for_email})</em></p>
            """
        else: # Debería ser improbable llegar aquí si send_notification es True
            body_price_details = "<p>Error al determinar detalles del precio para el correo.</p>"

        body_footer = f"<p><em>Razón de la notificación: {notification_reason}</em></p>"
        body_footer += f"<p><em>Revisado el: {current_time_str} (UTC)</em></p>"

        email_body_html = f"""
        <html>
            <body>
                {body_intro}
                {body_url}
                {body_price_details}
                {body_footer}
            </body>
        </html>
        """
        
        if notifier.send_email_notification(
            email_subject, email_body_html, recipient_email,
            sender_email, sender_app_password, smtp_server, smtp_port
        ):
            # Solo actualiza el estado guardado si la notificación fue exitosa (o si decidimos guardarlo siempre)
            product_states[product_url] = {
                "last_notified_type": current_best_offer_type,
                "last_notified_price": current_best_price,
                "last_checked_timestamp": datetime.now().isoformat()
            }
            return True # Indica que el estado cambió y debe guardarse
    
    return False # No se envió notificación o no cambió el estado de forma relevante


def run_checker():
    print("Main: Iniciando el comprobador de precios...")
    if not config.PRODUCT_URLS:
        print("Main: No hay URLs de productos configuradas en config.py. Saliendo.")
        return

    product_states = load_product_states()
    initial_states_copy = product_states.copy() # Para comparar si hubo cambios

    for url in config.PRODUCT_URLS:
        process_product(url, product_states) # Pasa el dict de estados para que pueda ser modificado
        print("-" * 30)

    # Guardar estados solo si han cambiado
    if product_states != initial_states_copy:
        save_product_states(product_states)
    else:
        print("Main: No hubo cambios en los estados de los productos, no se reescribe el archivo de estado.")

    print("Main: Comprobador de precios finalizado.")

if __name__ == "__main__":
    run_checker()
