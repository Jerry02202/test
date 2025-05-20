import requests
from bs4 import BeautifulSoup
import re # Importamos el módulo de expresiones regulares

# URL del producto a monitorear
PRODUCT_URL = "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570"

# User-Agent para simular un navegador
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_price_value(price_text):
    """Extrae el valor numérico del texto del precio (ej: 'S/ 28.90' -> 28.90)"""
    if price_text:
        # Usamos una expresión regular para encontrar el número (puede ser entero o decimal)
        match = re.search(r"S/\s*([\d,]+\.?\d*)", price_text)
        if match:
            # Reemplazamos coma por punto para el formato decimal si es necesario y convertimos a float
            return float(match.group(1).replace(',', ''))
    return None

def check_product_price():
    """
    Verifica el precio del producto en la URL y busca una promoción.
    Imprime el resultado.
    """
    try:
        response = requests.get(PRODUCT_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()  # Generará un error si la petición HTTP falló (ej: 404, 500)
        
        soup = BeautifulSoup(response.content, "html.parser")

        precio_regular_texto = None
        precio_promocional_texto = None
        
        # --- Lógica para encontrar los precios basada en el HTML proporcionado ---
        
        # Encontrar el contenedor principal de precios si es útil (opcional, pero puede ayudar a acotar la búsqueda)
        # price_container = soup.find("div", class_="price-container") # Asumiendo que esta clase sigue siendo relevante
        
        # Si no usamos price_container, buscamos directamente los spans
        # Buscamos todos los spans que podrían contener los textos de los precios
        spans = soup.find_all("span")
        
        regular_price_div = None
        promo_price_div = None

        for span in spans:
            span_text = span.get_text(strip=True)
            
            if span_text == "Precio regular":
                # El div del precio regular es el hermano del div que contiene el span
                # El span está en un div (ej: class="col-xs-7...")
                # El precio está en el siguiente div hermano (ej: class="col-xs-5...")
                parent_col_div = span.find_parent(lambda tag: tag.name == 'div' and 'col-xs-7' in tag.get('class', []))
                if parent_col_div:
                    price_sibling_div = parent_col_div.find_next_sibling("div")
                    if price_sibling_div and "price-amount" in price_sibling_div.get("class", []) and "text-strike" in price_sibling_div.get("class", []):
                        precio_regular_texto = price_sibling_div.get_text(strip=True)
                        
            elif span_text == "Precio Promocional":
                parent_col_div = span.find_parent(lambda tag: tag.name == 'div' and 'col-xs-7' in tag.get('class', [])) # Asumiendo misma estructura de columna para el label
                if parent_col_div:
                    price_sibling_div = parent_col_div.find_next_sibling("div")
                    if price_sibling_div and "price-amount" in price_sibling_div.get("class", []):
                        # Aseguramos que no tenga text-strike para no confundirlo con un regular tachado si la lógica anterior falla
                        if "text-strike" not in price_sibling_div.get("class", []):
                             precio_promocional_texto = price_sibling_div.get_text(strip=True)

        if precio_regular_texto and precio_promocional_texto:
            valor_regular = get_price_value(precio_regular_texto)
            valor_promocional = get_price_value(precio_promocional_texto)

            if valor_regular is not None and valor_promocional is not None:
                print(f"Información de precios encontrada:")
                print(f"  Precio Regular: {precio_regular_texto} (Valor: {valor_regular})")
                print(f"  Precio Promocional: {precio_promocional_texto} (Valor: {valor_promocional})")
                
                if valor_promocional < valor_regular:
                    print("¡PROMOCIÓN DETECTADA!")
                    print(f"El precio promocional (S/ {valor_promocional}) es menor que el precio regular (S/ {valor_regular}).")
                else:
                    print("Promoción encontrada, pero el precio promocional no es menor que el regular.")
            else:
                print("No se pudo extraer el valor numérico de uno o ambos precios.")
                if precio_regular_texto: print(f"  Texto Precio Regular: {precio_regular_texto}")
                if precio_promocional_texto: print(f"  Texto Precio Promocional: {precio_promocional_texto}")


        elif precio_regular_texto and not precio_promocional_texto:
            print(f"Solo se encontró el Precio Regular: {precio_regular_texto}.")
            print("No parece haber una promoción activa con 'Precio Promocional' visible en este momento.")
        else:
            print("No se encontró la estructura esperada para 'Precio regular' y/o 'Precio Promocional'.")
            print("Es posible que la página haya cambiado o no haya promoción activa con esa estructura.")

    except requests.exceptions.RequestException as e:
        print(f"Error al intentar acceder a la página: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante el scraping: {e}")

if __name__ == "__main__":
    print(f"Iniciando revisión de precio para: {PRODUCT_URL}")
    check_product_price()
    print("Revisión de precio finalizada.")
