import scrapy
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import overpy
from mercadolibre_scraper.items import MercadoLibreItem
import logging

class MercadoLibreSpider(scrapy.Spider):
    name = 'mercadolibre'
    start_urls = ['https://listado.mercadolibre.com.co/locales-arriendo-bogota']
    geolocator = Nominatim(user_agent="mercadolibre_spider", domain="nominatim.openstreetmap.org")
    overpass_api = overpy.Overpass()

    def __init__(self, start_url=None, stop_event=None, *args, **kwargs):
        super(MercadoLibreSpider, self).__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        self.stop_event = stop_event
        self.items_collected = []

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, errback=self.errback_httpbin)

    def errback_httpbin(self, failure):
        self.logger.error(f'Error en la solicitud: {repr(failure)}')

    def parse(self, response):
        self.logger.info(f"Procesando página: {response.url}")
        if self.stop_event and self.stop_event.is_set():
            raise scrapy.exceptions.CloseSpider('Stopped by user')
        
        locales = response.css('li.ui-search-layout__item')
        self.logger.info(f"Encontrados {len(locales)} locales en la página")
        
        for local in locales:
            self.logger.debug(f"Procesando item: {local.css('h2.ui-search-item__title::text').get()}")
            item = MercadoLibreItem()
            
            precio_text = local.css('span.price-tag-amount span.price-tag-fraction::text').get()
            item['precio'] = float(precio_text.replace('.', '').replace(',', '.')) if precio_text else None

            # Extraer características adicionales
            caracteristicas = local.css('ul.ui-search-card-attributes li::text').getall()
            item['metros_cuadrados'] = None
            item['cantidad_banos'] = None
            observaciones = []

            for caracteristica in caracteristicas:
                if 'm²' in caracteristica:
                    item['metros_cuadrados'] = float(re.search(r'\d+(\.\d+)?', caracteristica).group())
                elif 'baño' in caracteristica.lower():
                    item['cantidad_banos'] = int(re.search(r'\d+', caracteristica).group())
                else:
                    observaciones.append(caracteristica.strip())

            item['ubicacion'] = local.css('span.ui-search-item__location::text').get()
            item['latitud'], item['longitud'] = self.get_coordinates(item['ubicacion'])
            
            item['puntos_interes'] = self.get_points_of_interest(item['latitud'], item['longitud']) if item['latitud'] and item['longitud'] else {}

            item['titulo'] = local.css('h2.ui-search-item__title::text').get()
            item['link'] = local.css('a.ui-search-link::attr(href)').get()
            item['observaciones'] = ', '.join(observaciones) if observaciones else None
            item['fuente'] = 'MercadoLibre'

            self.logger.info(f"Item creado: {item['titulo']}")
            self.items_collected.append(item)
            yield item

        siguiente_pagina = response.css('a.andes-pagination__link.shops__pagination-link.ui-search-link[title="Siguiente"]::attr(href)').get()
        if siguiente_pagina:
            self.logger.info(f"Siguiente página encontrada: {siguiente_pagina}")
            yield scrapy.Request(siguiente_pagina, callback=self.parse)
        else:
            self.logger.info("No se encontró siguiente página")

    def closed(self, reason):
        self.logger.info(f"Spider cerrado. Razón: {reason}")
        self.logger.info(f"Total de items recolectados: {len(self.items_collected)}")
        for item in self.items_collected:
            self.logger.debug(f"Item: {item['titulo']}")

    def get_coordinates(self, address):
        try:
            location = self.geolocator.geocode(address + ", Bogotá, Colombia")
            if location:
                return location.latitude, location.longitude
        except (GeocoderTimedOut, GeocoderServiceError):
            self.logger.error(f"Geocoding error for address: {address}")
        return None, None

    def get_points_of_interest(self, lat, lon, radius=500):
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
            result = self.overpass_api.query(query)
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
            self.logger.error(f"Error querying Overpass API: {e}")
            return {}

    def parse_item(self, response):
        item = MercadoLibreItem()
        # Llena el item con los datos extraídos
        item['titulo'] = response.css('h1.ui-pdp-title::text').get()
        item['precio'] = response.css('span.andes-money-amount__fraction::text').get()
        # ... (resto de la extracción de datos)
        return item
