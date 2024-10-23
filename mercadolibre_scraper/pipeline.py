import psycopg2
import json
from scrapy.exceptions import DropItem
from scrapy.utils.project import get_project_settings
import logging

class PostgresPipeline:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.create_connection()

    def create_connection(self):
        try:
            settings = get_project_settings()
            params = settings['DATABASE']
            self.conn = psycopg2.connect(**params)
            self.cur = self.conn.cursor()
            self.logger.info("Conexión a la base de datos establecida")
        except Exception as e:
            self.logger.error(f"Error al conectar a la base de datos: {e}")
            raise

    def process_item(self, item, spider):
        try:
            self.logger.info(f"Procesando item en pipeline: {item['titulo']}")
            self.cur.execute("""
                INSERT INTO locales_arriendo (titulo, precio, ubicacion, link, metros_cuadrados, cantidad_banos, observaciones, fuente, latitud, longitud, puntos_interes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING
            """, (
                item['titulo'],
                item['precio'],
                item['ubicacion'],
                item['link'],
                item['metros_cuadrados'],
                item['cantidad_banos'],
                item['observaciones'],
                'MercadoLibre',
                item['latitud'],
                item['longitud'],
                json.dumps(item['puntos_interes'])
            ))
            self.conn.commit()
            self.logger.info(f"Item insertado en la base de datos: {item['titulo']}")
        except Exception as e:
            self.logger.error(f"Error al insertar item en la base de datos: {e}")
            self.conn.rollback()
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
        self.logger.info("Conexión a la base de datos cerrada")
