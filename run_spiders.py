import asyncio

import aiohttp
import logging
import psycopg2
from bs4 import BeautifulSoup

from mercadolibre_scraper.settings import DATABASE
from concurrent.futures import ThreadPoolExecutor
import random
from datetime import datetime, timezone

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
]

async def fetch(session, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            headers = {'User-Agent': random.choice(USER_AGENTS)}
            async with session.get(url, headers=headers) as response:
                return await response.text()
        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                logging.warning(f"No se pudo obtener {url} después de {max_retries} intentos")
                return None
        await asyncio.sleep(random.uniform(1, 3))

async def extract_data(item, ciudad):
    data = {}
    data['titulo'] = item.select_one('.poly-component__title a').text.strip() if item.select_one('.poly-component__title a') else None
    data['precio'] = item.select_one('.andes-money-amount__fraction').text.strip().replace('.', '') if item.select_one('.andes-money-amount__fraction') else None
    data['ubicacion'] = item.select_one('.poly-component__location').text.strip() if item.select_one('.poly-component__location') else None
    data['link'] = item.select_one('.poly-component__title a')['href'] if item.select_one('.poly-component__title a') else None
    image_element = item.select_one('.poly-component__picture')
    data['imagen_url'] = image_element['data-src'] if image_element and 'data-src' in image_element.attrs else image_element['src'] if image_element else None
    
    attributes = item.select('.poly-attributes-list__item')
    for attr in attributes:
        text = attr.text.strip()
        if 'm²' in text:
            data['metros_cuadrados'] = float(text.split()[0])
        elif 'baño' in text.lower():
            data['cantidad_banos'] = int(text.split()[0])
    
    if data['ubicacion']:
        ubicacion_parts = data['ubicacion'].split(',')
        data['ciudad'] = ciudad
        data['localidad'] = ubicacion_parts[-1].strip() if len(ubicacion_parts) > 0 else None
        data['barrio'] = ubicacion_parts[0].strip() if len(ubicacion_parts) > 1 else None
    else:
        data['ciudad'] = ciudad
        data['localidad'] = data['barrio'] = None
    
    data['ultima_actualizacion'] = datetime.now(timezone.utc)
    
    return data

async def scrape_page(session, url, ciudad):
    html = await fetch(session, url)
    if not html:
        return [], None
    soup = BeautifulSoup(html, 'html.parser')
    
    items = soup.select('.ui-search-layout__item')
    data = [await extract_data(item, ciudad) for item in items]
    
    next_page = soup.select_one('.andes-pagination__button--next a')
    next_url = next_page['href'] if next_page else None
    
    return data, next_url

def save_to_db(items):
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    
    for item in items:
        try:
            cur.execute("""
                INSERT INTO locales_arriendo (titulo, precio, ubicacion, ciudad, localidad, barrio, link, imagen_url, metros_cuadrados, cantidad_banos, fuente, ultima_actualizacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (imagen_url) DO UPDATE
                SET titulo = EXCLUDED.titulo,
                    precio = EXCLUDED.precio,
                    ubicacion = EXCLUDED.ubicacion,
                    ciudad = EXCLUDED.ciudad,
                    localidad = EXCLUDED.localidad,
                    barrio = EXCLUDED.barrio,
                    link = EXCLUDED.link,
                    metros_cuadrados = EXCLUDED.metros_cuadrados,
                    cantidad_banos = EXCLUDED.cantidad_banos,
                    fuente = EXCLUDED.fuente,
                    ultima_actualizacion = EXCLUDED.ultima_actualizacion
            """, (
                item.get('titulo'),
                item.get('precio'),
                item.get('ubicacion'),
                item.get('ciudad'),
                item.get('localidad'),
                item.get('barrio'),
                item.get('link'),
                item.get('imagen_url'),
                item.get('metros_cuadrados'),
                item.get('cantidad_banos'),
                'MercadoLibre',
                item.get('ultima_actualizacion')
            ))
            conn.commit()
        except Exception as e:
            logging.warning(f"Error al insertar/actualizar item en la base de datos: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()

async def main():
    start_urls = [
        ('https://listado.mercadolibre.com.co/locales-arriendo-bogota', 'Bogotá'),
        #('https://listado.mercadolibre.com.co/locales-arriendo-medellin', 'Medellín')
    ]
    all_data = []
    batch_size = 200
    max_pages = 100
    
    async with aiohttp.ClientSession() as session:
        for start_url, ciudad in start_urls:
            page_count = 0
            url = start_url
            while url and page_count < max_pages:
                logging.warning(f"Scraping página {page_count + 1} de {ciudad}: {url}")
                data, url = await scrape_page(session, url, ciudad)
                all_data.extend(data)
                page_count += 1
                
                if len(all_data) >= batch_size:
                    with ThreadPoolExecutor() as executor:
                        executor.submit(save_to_db, all_data[:batch_size])
                    all_data = all_data[batch_size:]
                
                await asyncio.sleep(random.uniform(2, 5))
    
    if all_data:
        save_to_db(all_data)
    
    logging.warning(f"Scraping finalizado. Total de páginas scrapeadas: {page_count}")

if __name__ == '__main__':
    asyncio.run(main())
