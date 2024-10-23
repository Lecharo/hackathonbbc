import psycopg2
import json
from mercadolibre_scraper.settings import DATABASE
from mercadolibre_scraper.geocoding import get_coordinates, get_points_of_interest

def geolocate_and_update(item_id, ubicacion):
    lat, lon = get_coordinates(ubicacion)
    if lat and lon:
        poi = get_points_of_interest(lat, lon)
    else:
        poi = {}
    
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    
    try:
        # Insertar o actualizar en geolocalizaciones
        cur.execute("""
            INSERT INTO geolocalizaciones (direccion, latitud, longitud, puntos_interes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (direccion) DO UPDATE
            SET latitud = EXCLUDED.latitud, longitud = EXCLUDED.longitud, 
                puntos_interes = EXCLUDED.puntos_interes, ultima_actualizacion = CURRENT_TIMESTAMP
            RETURNING id
        """, (ubicacion, lat, lon, json.dumps(poi)))
        geolocalizacion_id = cur.fetchone()[0]
        
        # Actualizar locales_arriendo con el id de geolocalización
        cur.execute("""
            UPDATE locales_arriendo
            SET geolocalizacion_id = %s
            WHERE id = %s
        """, (geolocalizacion_id, item_id))
        
        conn.commit()
        print(f"Geolocalización actualizada para item_id: {item_id}")
    except Exception as e:
        print(f"Error al actualizar geolocalización: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
