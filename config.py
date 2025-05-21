# config.py

# Por ahora, una sola URL. Más adelante podría ser una lista de diccionarios.
# Ejemplo de expansión futura:
# PRODUCTS_TO_CHECK = [
#     {
#         "name_hint": "Magnesol Naranja", # Para referencia o si el scraping del nombre falla
#         "url": "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570"
#     },
#     {
#         "name_hint": "Aceite de Coco Peruvian Health",
#         "url": "URL_DEL_ACEITE_DE_COCO"
#     }
# ]

PRODUCT_URLS = [
    "https://inkafarma.pe/producto/magnesol-polvo-efervescente-sabor-naranja/009570",
    "https://inkafarma.pe/producto/desodorante-barra-invisible-secret-powder-cotton/071306"
    # Puedes añadir más URLs aquí en el futuro, una por línea, separadas por comas:
    # "https://inkafarma.pe/OTRO_PRODUCTO_URL",
    # "https://inkafarma.pe/UN_TERCER_PRODUCTO_URL"
]

# Configuración común de Headers para el scraper
# (Aunque requests-html puede manejar su propio User-Agent, tenerlo aquí es una opción)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}
