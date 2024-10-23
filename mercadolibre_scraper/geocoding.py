import time
from functools import lru_cache
from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging
import overpy

# Configura tus API keys aquí
GOOGLE_API_KEY = 'TU_API_KEY_DE_GOOGLE'

geolocator_nominatim = Nominatim(user_agent="mercadolibre_spider", domain="nominatim.openstreetmap.org", timeout=5)  # Aumentado el timeout
geolocator_google = GoogleV3(api_key=GOOGLE_API_KEY, timeout=5)  # Aumentado el timeout
overpass_api = overpy.Overpass()

@lru_cache(maxsize=1000)
def geocode_address(address):
    max_retries = 5  # Aumentado el número de reintentos
    for attempt in range(max_retries):
        try:
            # Intenta primero con Nominatim
            location = geolocator_nominatim.geocode(address)
            if location:
                return location.latitude, location.longitude
            
            # Si Nominatim falla, intenta con Google
            location = geolocator_google.geocode(address)
            if location:
                return location.latitude, location.longitude
            
            logging.warning(f"No se encontraron coordenadas para: {address}")
            return None, None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt < max_retries - 1:
                logging.warning(f"Intento {attempt + 1} fallido para geocodificar {address}: {e}")
                time.sleep(2 ** attempt)  # Espera exponencial entre intentos
            else:
                logging.error(f"Geocoding error for address after {max_retries} intentos: {address}")
                return None, None

def get_coordinates(address):
    full_address = f"{address}, Bogotá, Colombia"
    return geocode_address(full_address)

def get_points_of_interest(lat, lon, radius=500):
    query = f"""
    [out:json];
    (
      node["amenity"](around:{radius},{lat},{lon});
      way["amenity"](around:{radius},{lat},{lon});
      relation["amenity"](around:{radius},{lat},{lon});
    );
    out center;
    """
    try:
        result = overpass_api.query(query)
        poi = {
            'restaurantes': [],
            'bancos': [],
            'transporte_publico': []
        }
        for element in result.nodes + result.ways + result.relations:
            if 'amenity' in element.tags:
                if element.tags['amenity'] in ['restaurant', 'cafe', 'fast_food']:
                    poi['restaurantes'].append(element.tags.get('name', 'Sin nombre'))
                elif element.tags['amenity'] in ['bank', 'atm']:
                    poi['bancos'].append(element.tags.get('name', 'Sin nombre'))
                elif element.tags['amenity'] in ['bus_station', 'subway_entrance']:
                    poi['transporte_publico'].append(element.tags.get('name', 'Sin nombre'))
        return poi
    except Exception as e:
        logging.error(f"Error querying Overpass API: {e}")
        return {}
