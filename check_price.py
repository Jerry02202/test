import time
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
import pyppeteer # requests-html puede necesitarlo explícitamente

PRODUCT_URL = "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
}

def get_price_value(price_text):
    if price_text:
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            return float(match.group(1).replace(',', ''))
    return None

def find_price_elements(soup):
    texto_regular_encontrado = None
    texto_promocional_encontrado = None
    regular_esta_tachado = False

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
    
    return texto_regular_encontrado, texto_promocional_encontrado, regular_esta_tachado

def check_product_price():
    session = HTMLSession()
    try:
        print(f"Iniciando revisión de precio para: {PRODUCT_URL}") # Mensaje inicial útil
        response = session.get(PRODUCT_URL, headers=HEADERS, timeout=35) # Timeout un poco más largo para GET
        response.raise_for_status()

        # print("Página obtenida. Renderizando JavaScript (esto puede tardar)...") # Eliminado
        response.html.render(timeout=45, scrolldown=2, sleep=5) # Aumentar ligeramente timeouts/sleeps
        
        # print("JavaScript renderizado. Parseando HTML con BeautifulSoup...") # Eliminado
        rendered_html = response.html.html 
        soup = BeautifulSoup(rendered_html, "html.parser")
        
        # La línea de print(soup.prettify()) ya debería estar comentada o eliminada.

        texto_regular, texto_promo, regular_tachado = find_price_elements(soup)

        # print(f"\n--- Resultados de la Extracción ---") # Eliminado
        # print(f"Texto Regular Encontrado: '{texto_regular}'") # Eliminado
        # print(f"Precio Regular está Tachado: {regular_tachado}") # Eliminado
        # print(f"Texto Promocional Encontrado: '{texto_promo}'") # Eliminado
        # print(f"-----------------------------------\n") # Eliminado

        if texto_promo and texto_regular and regular_tachado:
            valor_regular_num = get_price_value(texto_regular)
            valor_promo_num = get_price_value(texto_promo)
            if valor_regular_num is not None and valor_promo_num is not None:
                print(f"  Precio Regular: {texto_regular} (Valor: {valor_regular_num})")
                print(f"  Precio Promocional: {texto_promo} (Valor: {valor_promo_num})")
                if valor_promo_num < valor_regular_num:
                    print("¡PROMOCIÓN DETECTADA!")
                else:
                    print("Promoción encontrada (regular tachado y promocional visible), pero el precio promocional no es menor que el regular.")
            else:
                print("Se encontraron los textos de promoción, pero no se pudieron extraer los valores numéricos.")
                if not valor_regular_num: print(f"  No se pudo parsear el valor de: '{texto_regular}'")
                if not valor_promo_num: print(f"  No se pudo parsear el valor de: '{texto_promo}'")
        
        elif texto_regular and not texto_promo:
            print(f"Solo se encontró el Precio Regular: '{texto_regular}'.")
            if regular_tachado: # Aunque no debería pasar si solo hay regular y está tachado sin promo
                 print("  Este precio regular aparece tachado, pero no se encontró un 'Precio Promocional' acompañándolo.")
            else:
                 print("  No se encontró un 'Precio Promocional'. Asumiendo que no hay promoción activa.")
        
        elif not texto_regular and texto_promo:
            print(f"Se encontró un 'Precio Promocional' ('{texto_promo}') pero no se pudo identificar un 'Precio regular' claro.")
        
        else:
            print("No se pudo identificar claramente ni 'Precio regular' ni 'Precio Promocional' con la estructura esperada.")
            # print("Verificar la lógica de búsqueda si se esperaba encontrar precios (o descomentar la impresión del HTML renderizado).")

    except pyppeteer.errors.TimeoutError as e:
        print(f"Error de Timeout durante el renderizado de JavaScript: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error al intentar acceder a la página: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        print(f"Tipo de error: {type(e)}")
    finally:
        session.close()
    print("Revisión de precio finalizada.") # Mensaje final útil

if __name__ == "__main__":
    # El mensaje "Iniciando revisión de precio para..." ya está en check_product_price()
    check_product_price()
    # El mensaje "Revisión de precio finalizada." ya está en check_product_price()
