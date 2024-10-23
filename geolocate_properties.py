import psycopg2
import json
from mercadolibre_scraper.settings import DATABASE
import logging
import overpy
from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_coordinates(address, max_retries=3):
    geolocator_nominatim = Nominatim(user_agent="localfindsmart", timeout=10)
    geolocator_google = GoogleV3(api_key="TU_API_KEY_DE_GOOGLE")  # Reemplaza con tu API key de Google
    
    for attempt in range(max_retries):
        try:
            logging.info(f"Intento {attempt + 1} de geocodificación para: {address}")
            
            # Intenta con Nominatim primero
            location = geolocator_nominatim.geocode(address)
            if location:
                logging.info(f"Coordenadas encontradas con Nominatim: {location.latitude}, {location.longitude}")
                return location.latitude, location.longitude
            
            # Si Nominatim falla, intenta con Google
            location = geolocator_google.geocode(address)
            if location:
                logging.info(f"Coordenadas encontradas con Google: {location.latitude}, {location.longitude}")
                return location.latitude, location.longitude
            
            logging.warning(f"No se encontraron coordenadas para: {address}")
            return None, None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logging.error(f"Error en el intento {attempt + 1} para {address}: {str(e)}")
            if attempt == max_retries - 1:
                logging.error(f"Todos los intentos fallaron para: {address}")
                return None, None
            time.sleep(2 ** attempt)  # Espera exponencial entre intentos

def get_points_of_interest(lat, lon, radius=500):
    api = overpy.Overpass()
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
        result = api.query(query)
        poi = {
            'restaurantes': set(),
            'bancos': set(),
            'transporte_publico': set()
        }
        for element in result.nodes + result.ways + result.relations:
            if 'amenity' in element.tags:
                name = element.tags.get('name', 'Sin nombre')
                if name != 'Sin nombre':
                    if element.tags['amenity'] in ['restaurant', 'cafe', 'fast_food']:
                        poi['restaurantes'].add(name)
                    elif element.tags['amenity'] in ['bank', 'atm']:
                        poi['bancos'].add(name)
                    elif element.tags['amenity'] in ['bus_station', 'subway_entrance']:
                        poi['transporte_publico'].add(name)
        
        for key in poi:
            poi[key] = list(poi[key])
        
        logging.info(f"Puntos de interés encontrados para ({lat}, {lon}): {poi}")
        return poi
    except Exception as e:
        logging.error(f"Error querying Overpass API for ({lat}, {lon}): {e}")
        return {}

def process_property(property_data):
    id, ubicacion, lat, lon = property_data
    if lat is None or lon is None:
        lat, lon = get_coordinates(ubicacion)
    if lat is not None and lon is not None:
        poi = get_points_of_interest(lat, lon)
    else:
        poi = {}
    return (id, ubicacion, lat, lon, json.dumps(poi))

def update_database(results):
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    for result in results:
        id, ubicacion, lat, lon, poi = result
        try:
            cur.execute("""
                INSERT INTO geolocalizaciones (direccion, latitud, longitud, puntos_interes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (direccion) DO UPDATE
                SET latitud = EXCLUDED.latitud,
                    longitud = EXCLUDED.longitud,
                    puntos_interes = EXCLUDED.puntos_interes
                RETURNING id
            """, (ubicacion, lat, lon, poi))
            geolocalizacion_id = cur.fetchone()[0]
            
            cur.execute("""
                UPDATE locales_arriendo
                SET geolocalizacion_id = %s
                WHERE id = %s
            """, (geolocalizacion_id, id))
            
            conn.commit()
            logging.info(f"Actualizado registro para ID: {id}")
        except Exception as e:
            logging.error(f"Error al actualizar la base de datos para ID {id}: {str(e)}")
            conn.rollback()
    cur.close()
    conn.close()

def main():
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    cur.execute("""
        SELECT la.id, la.ubicacion, g.latitud, g.longitud
        FROM locales_arriendo la
        LEFT JOIN geolocalizaciones g ON la.geolocalizacion_id = g.id
        WHERE g.id IS NULL OR g.puntos_interes IS NULL OR g.puntos_interes = '{}'
    """)
    properties = cur.fetchall()
    cur.close()
    conn.close()

    logging.info(f"Procesando {len(properties)} propiedades")

    results = [process_property(prop) for prop in properties]

    update_database(results)
    logging.info("Proceso completado")

if __name__ == "__main__":
    main()
