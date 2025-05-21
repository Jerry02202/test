# scraper.py

from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import pyppeteer # Import implícito necesario para requests-html.render()

# No necesitamos config aquí directamente si la URL y headers se pasan como argumentos

def get_price_value(price_text):
    """Extrae el valor numérico del texto del precio (ej: 'S/ 28.90' -> 28.90)"""
    if price_text:
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            # Reemplazamos coma por punto para el formato decimal si es necesario y convertimos a float
            return float(match.group(1).replace(',', ''))
    return None

def extract_product_details_from_html(html_content):
    """
    Extrae nombre del producto, precio regular y promocional del HTML parseado.
    Utiliza BeautifulSoup para analizar el contenido HTML.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    product_name = "Producto Desconocido"
    texto_regular_encontrado = None
    texto_promocional_encontrado = None
    regular_esta_tachado = False

    # Extraer el nombre del producto usando la clase identificada
    name_tag = soup.select_one("h1.product-detail-information__name")
    if name_tag:
        product_name = name_tag.get_text(strip=True)
    else:
        # Fallback si no se encuentra la clase específica, intentar con og:title o h1 genérico
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            product_name = meta_title["content"].replace("Inkafarma: Más salud al mejor precio | ", "").replace("Inkafarma | ", "").strip()
            if " - Inkafarma" in product_name:
                product_name = product_name.split(" - Inkafarma")[0]
        elif soup.find("h1"):
            product_name = soup.find("h1").get_text(strip=True)


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
    
    return {
        "name": product_name,
        "regular_price_text": texto_regular_encontrado,
        "promo_price_text": texto_promocional_encontrado,
        "is_regular_price_striked": regular_esta_tachado,
        "regular_price_value": get_price_value(texto_regular_encontrado) if texto_regular_encontrado else None,
        "promo_price_value": get_price_value(texto_promocional_encontrado) if texto_promocional_encontrado else None,
    }

def fetch_product_data(product_url, headers):
    """
    Obtiene la página del producto, renderiza JavaScript y extrae los detalles.
    Devuelve un diccionario con los datos del producto o None si falla.
    """
    session = HTMLSession()
    product_data = None
    try:
        print(f"Scraper: Intentando acceder a: {product_url}")
        response = session.get(product_url, headers=headers, timeout=35)
        response.raise_for_status()

        print("Scraper: Página obtenida. Renderizando JavaScript...")
        response.html.render(timeout=45, scrolldown=2, sleep=5) # Ajustar según sea necesario
        
        print("Scraper: JavaScript renderizado. Extrayendo detalles del producto...")
        rendered_html = response.html.html 
        product_data = extract_product_details_from_html(rendered_html)
        product_data["url"] = product_url # Añadir la URL a los datos devueltos

    except pyppeteer.errors.TimeoutError as e:
        print(f"Scraper: Error de Timeout durante el renderizado de JavaScript para {product_url}: {e}")
    except Exception as e: # Captura más general para errores de requests, etc.
        print(f"Scraper: Error al procesar {product_url}: {e}")
    finally:
        session.close()
    
    return product_data
