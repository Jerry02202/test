import requests
from bs4 import BeautifulSoup
import re

PRODUCT_URL = "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_price_value(price_text):
    """Extrae el valor numérico del texto del precio (ej: 'S/ 28.90' -> 28.90)"""
    if price_text:
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            return float(match.group(1).replace(',', '')) # Reemplaza comas si las usa para miles antes de convertir
    return None

def find_price_elements(soup):
    """
    Intenta encontrar los elementos de precio regular y promocional.
    Devuelve: (texto_regular_encontrado, texto_promocional_encontrado, regular_esta_tachado)
    """
    texto_regular_encontrado = None
    texto_promocional_encontrado = None
    regular_esta_tachado = False

    # Intenta encontrar el span que contiene "Precio regular"
    span_regular_element = soup.find("span", string=lambda text: text and "Precio regular" in text.strip())
    # Intenta encontrar el span que contiene "Precio Promocional"
    span_promo_element = soup.find("span", string=lambda text: text and "Precio Promocional" in text.strip())

    # Procesar Precio Regular si se encontró el span
    if span_regular_element:
        # Navegar al div padre que es una columna (ej. class="col-xs-7...")
        parent_col_div_regular = span_regular_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div_regular:
            # El div del precio es el siguiente hermano con la clase 'price-amount'
            price_sibling_div_regular = parent_col_div_regular.find_next_sibling("div", class_="price-amount")
            if price_sibling_div_regular:
                texto_regular_encontrado = price_sibling_div_regular.get_text(strip=True)
                if "text-strike" in price_sibling_div_regular.get("class", []):
                    regular_esta_tachado = True
    
    # Procesar Precio Promocional si se encontró el span
    if span_promo_element:
        parent_col_div_promo = span_promo_element.find_parent(
            lambda tag: tag.name == 'div' and tag.get('class') and any(cls.startswith('col-') for cls in tag.get('class'))
        )
        if parent_col_div_promo:
            price_sibling_div_promo = parent_col_div_promo.find_next_sibling("div", class_="price-amount")
            if price_sibling_div_promo:
                 # Asegurar que el promocional no esté tachado (a veces las clases se heredan o aplican mal)
                if "text-strike" not in price_sibling_div_promo.get("class", []):
                    texto_promocional_encontrado = price_sibling_div_promo.get_text(strip=True)
    
    return texto_regular_encontrado, texto_promocional_encontrado, regular_esta_tachado


def check_product_price():
    """
    Verifica el precio del producto en la URL y busca una promoción.
    Imprime el resultado.
    """
    try:
        response = requests.get(PRODUCT_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()  # Generará un error si la petición HTTP falló
        
        soup = BeautifulSoup(response.content, "html.parser")

        # Extraer la información de los precios
        texto_regular, texto_promo, regular_tachado = find_price_elements(soup)

        # Imprimir información de depuración
        print(f"--- Información de Depuración ---")
        print(f"Texto Regular Encontrado: '{texto_regular}'")
        print(f"Precio Regular está Tachado: {regular_tachado}")
        print(f"Texto Promocional Encontrado: '{texto_promo}'")
        print(f"-------------------------------")

        if texto_promo and texto_regular and regular_tachado:
            # Caso de promoción clara detectada
            valor_regular_num = get_price_value(texto_regular)
            valor_promo_num = get_price_value(texto_promo)

            if valor_regular_num is not None and valor_promo_num is not None:
                print(f"Precio Regular: {texto_regular} (Valor numérico: {valor_regular_num})")
                print(f"Precio Promocional: {texto_promo} (Valor numérico: {valor_promo_num})")
                
                if valor_promo_num < valor_regular_num:
                    print("¡PROMOCIÓN DETECTADA!")
                    print(f"El precio promocional (S/ {valor_promo_num}) es menor que el precio regular (S/ {valor_regular_num}).")
                else:
                    print("Promoción encontrada (regular tachado y promocional visible), pero el precio promocional no es menor que el regular.")
            else:
                print("Se encontraron los textos de promoción, pero no se pudieron extraer los valores numéricos.")
                if not valor_regular_num: print(f"  No se pudo parsear el valor de: '{texto_regular}'")
                if not valor_promo_num: print(f"  No se pudo parsear el valor de: '{texto_promo}'")
        
        elif texto_regular and not texto_promo:
            # Solo se encontró el precio regular (y no está tachado, o si lo estuviera pero no hay promo, esto lo cubre)
            print(f"Se encontró un Precio Regular: '{texto_regular}'")
            if regular_tachado:
                 print("Este precio regular aparece tachado, pero no se encontró un 'Precio Promocional' acompañándolo.")
                 print("Esto podría ser una estructura de página inusual o una promo que no sigue el patrón esperado.")
            else:
                 print("No se encontró un 'Precio Promocional'. Asumiendo que no hay promoción activa en este momento.")
        
        elif not texto_regular and texto_promo:
            print(f"Se encontró un 'Precio Promocional' ('{texto_promo}') pero no se pudo identificar un 'Precio regular' claro.")
            print("Esto es una estructura de página inusual.")

        else: # Ni texto_regular ni texto_promo fueron claramente identificados
            print("No se pudo identificar claramente ni 'Precio regular' ni 'Precio Promocional' con la estructura esperada.")
            print("Es posible que la página haya cambiado significativamente, el producto no esté disponible, o haya un error en la lógica de scraping.")

    except requests.exceptions.RequestException as e:
        print(f"Error al intentar acceder a la página: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante el scraping: {e}")

if __name__ == "__main__":
    print(f"Iniciando revisión de precio para: {PRODUCT_URL}")
    check_product_price()
    print("Revisión de precio finalizada.")
