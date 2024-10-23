import scrapy

class MercadoLibreItem(scrapy.Item):
    titulo = scrapy.Field()
    precio = scrapy.Field()
    ubicacion = scrapy.Field()
    link = scrapy.Field()
    metros_cuadrados = scrapy.Field()
    cantidad_banos = scrapy.Field()
    observaciones = scrapy.Field()
    imagen_url = scrapy.Field()
    geolocalizacion_id = scrapy.Field()

class GeolocalizacionItem(scrapy.Item):
    direccion = scrapy.Field()
    latitud = scrapy.Field()
    longitud = scrapy.Field()
    puntos_interes = scrapy.Field()
