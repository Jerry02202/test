# scraper.py

from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import pyppeteer # Import implícito necesario para requests-html.render()

def get_price_value(price_text):
    if price_text:
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            return float(match.group(1).replace(',', ''))
    return None

def extract_product_details_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    product_name = "Producto Desconocido"
    texto_regular_encontrado = None
    texto_promocional_encontrado = None
    texto_oh_encontrado = None # NUEVO
    regular_esta_tachado = False

    name_tag = soup.select_one("h1.product-detail-information__name")
    if name_tag:
        product_name = name_tag.get_text(strip=True)
    else:
        meta_title = soup.find("meta", property="og:title")
        if meta_title and meta_title.get("content"):
            product_name = meta_title["content"].replace("Inkafarma: Más salud al mejor precio | ", "").replace("Inkafarma | ", "").strip()
            if " - Inkafarma" in product_name:
                product_name = product_name.split(" - Inkafarma")[0]
        elif soup.find("h1"):
            product_name = soup.find("h1").get_text(strip=True)

    # Buscar Precio Regular
    span_regular_element = soup.find("span", string=lambda text: text and "precio regular" in text.strip().lower())
    if span_regular_element:
        parent_col_div = span_regular_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div:
            price_sibling_div = parent_col_div.find_next_sibling("div", class_="price-amount")
            if price_sibling_div:
                texto_regular_encontrado = price_sibling_div.get_text(strip=True)
                if "text-strike" in price_sibling_div.get("class", []):
                    regular_esta_tachado = True
    
    # Buscar Precio Promocional
    span_promo_element = soup.find("span", string=lambda text: text and "precio promocional" in text.strip().lower())
    if span_promo_element:
        parent_col_div = span_promo_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div:
            price_sibling_div = parent_col_div.find_next_sibling("div", class_="price-amount")
            if price_sibling_div:
                if "text-strike" not in price_sibling_div.get("class", []): # Asegurar que no sea el regular tachado
                    texto_promocional_encontrado = price_sibling_div.get_text(strip=True)

    # Buscar Precio Exclusivo oh! y oh! pay (NUEVO)
    span_oh_element = soup.find("span", string=lambda text: text and "exclusivo oh! y oh! pay" in text.strip().lower())
    if span_oh_element:
        parent_col_div = span_oh_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div:
            # El precio está en un div con clase 'price-amount' que es un hijo del siguiente div hermano
            price_container_sibling_div = parent_col_div.find_next_sibling("div") 
            if price_container_sibling_div:
                price_oh_div = price_container_sibling_div.find("div", class_="price-amount")
                if price_oh_div:
                    # Extraer solo el texto del precio, ignorando los elementos hijos como las imágenes
                    price_text_parts = [str(content) for content in price_oh_div.contents if isinstance(content, str)]
                    texto_oh_encontrado = "".join(price_text_parts).strip()


    return {
        "name": product_name,
        "regular_price_text": texto_regular_encontrado,
        "promo_price_text": texto_promocional_encontrado,
        "oh_price_text": texto_oh_encontrado, # NUEVO
        "is_regular_price_striked": regular_esta_tachado,
        "regular_price_value": get_price_value(texto_regular_encontrado) if texto_regular_encontrado else None,
        "promo_price_value": get_price_value(texto_promocional_encontrado) if texto_promocional_encontrado else None,
        "oh_price_value": get_price_value(texto_oh_encontrado) if texto_oh_encontrado else None, # NUEVO
    }

def fetch_product_data(product_url, headers):
    session = HTMLSession()
    product_data = None
    try:
        print(f"Scraper: Intentando acceder a: {product_url}")
        response = session.get(product_url, headers=headers, timeout=35)
        response.raise_for_status()

        print("Scraper: Página obtenida. Renderizando JavaScript...")
        response.html.render(timeout=45, scrolldown=2, sleep=5)
        
        print("Scraper: JavaScript renderizado. Extrayendo detalles del producto...")
        rendered_html = response.html.html 
        product_data = extract_product_details_from_html(rendered_html)
        product_data["url"] = product_url

    except pyppeteer.errors.TimeoutError as e:
        print(f"Scraper: Error de Timeout durante el renderizado de JavaScript para {product_url}: {e}")
    except Exception as e:
        print(f"Scraper: Error al procesar {product_url}: {e}")
    finally:
        session.close()
    
    return product_data
