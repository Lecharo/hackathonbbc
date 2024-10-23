BOT_NAME = 'mercadolibre_scraper'

SPIDER_MODULES = ['mercadolibre_scraper.spiders']
NEWSPIDER_MODULE = 'mercadolibre_scraper.spiders'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 32

DOWNLOAD_DELAY = 1

COOKIES_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language': 'es',
}

# Configuración de la base de datos
DATABASE = {
    'host': 'localhost',
    'port': '5432',
    'user': 'postgres',  # Cambiado de 'username' a 'user'
    'password': 'admin',
    'database': 'hackatonccb'
}

ITEM_PIPELINES = {
   'mercadolibre_scraper.pipeline.PostgresPipeline': 300,
}

# Desactiva el log para evitar conflictos entre procesos
LOG_ENABLED = True
LOG_LEVEL = 'DEBUG'
LOG_FILE = 'spider_log.txt'
LOG_STDOUT = True

SPIDER_MIDDLEWARES = {
   'mercadolibre_scraper.middlewares.MercadolibreScraperSpiderMiddleware': 543,
}

DOWNLOADER_MIDDLEWARES = {
   'mercadolibre_scraper.middlewares.MercadolibreScraperDownloaderMiddleware': 543,
}
