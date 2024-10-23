import requests
from bs4 import BeautifulSoup
import psycopg2
import time
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la base de datos
DATABASE = {
    'host': 'localhost',
    'port': '5432',
    'user': 'postgres',
    'password': 'admin',
    'database': 'hackatonccb'
}

def get_soup(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        logging.error(f"Error al obtener la página {url}: {e}")
        return None

def extract_data(item):
    data = {}
    title_element = item.select_one('.poly-component__title a')
    if title_element:
        data['titulo'] = title_element.text.strip()
    
    price_element = item.select_one('.andes-money-amount__fraction')
    if price_element:
        data['precio'] = price_element.text.strip().replace('.', '')
    
    location_element = item.select_one('.poly-component__location')
    if location_element:
        data['ubicacion'] = location_element.text.strip()
    
    link_element = item.select_one('.poly-component__title a')
    if link_element:
        data['link'] = link_element['href']
    
    caracteristicas = item.select('.poly-attributes-list__item')
    for carac in caracteristicas:
        text = carac.text.strip()
        if 'm²' in text:
            data['metros_cuadrados'] = float(text.split()[0])
        elif 'baño' in text.lower():
            data['cantidad_banos'] = int(text.split()[0])
    
    return data

def scrape_page(url):
    soup = get_soup(url)
    if not soup:
        return [], None

    items = soup.select('.ui-search-layout__item')
    logging.info(f"Encontrados {len(items)} items en la página")
    
    data = [extract_data(item) for item in items if extract_data(item)]
    
    next_page = soup.select_one('.andes-pagination__button--next a')
    next_url = next_page['href'] if next_page else None
    
    return data, next_url

def save_to_db(data):
    conn = psycopg2.connect(**DATABASE)
    cur = conn.cursor()
    
    for item in data:
        try:
            cur.execute("""
                INSERT INTO locales_arriendo (titulo, precio, ubicacion, link, metros_cuadrados, cantidad_banos, fuente)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING
            """, (
                item.get('titulo'),
                item.get('precio'),
                item.get('ubicacion'),
                item.get('link'),
                item.get('metros_cuadrados'),
                item.get('cantidad_banos'),
                'MercadoLibre'
            ))
            conn.commit()
        except Exception as e:
            logging.error(f"Error al insertar item en la base de datos: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()

def main():
    url = 'https://listado.mercadolibre.com.co/locales-arriendo-bogota'
    all_data = []
    
    while url:
        logging.info(f"Scraping: {url}")
        data, url = scrape_page(url)
        if data:
            all_data.extend(data)
            save_to_db(data)
            logging.info(f"Scraped {len(data)} items. Total: {len(all_data)}")
        else:
            logging.warning("No se encontraron datos en esta página")
        time.sleep(2)
    
    logging.info(f"Scraping finalizado. Total de items: {len(all_data)}")

if __name__ == '__main__':
    main()
