import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, func, distinct, cast, Float, text, Column, Integer, String, desc, asc
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql.expression import func
import folium
from streamlit_folium import st_folium, folium_static

import os
import base64
import json
from datetime import datetime
import random

# Configuración de la base de datos
engine = create_engine('postgresql://postgres:admin@localhost/hackatonccb')
Session = sessionmaker(bind=engine)
Base = declarative_base()

class LocalArriendo(Base):
    __tablename__ = 'locales_arriendo'
    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    precio = Column(String)
    ubicacion = Column(String)
    ciudad = Column(String)
    localidad = Column(String)
    barrio = Column(String)
    link = Column(String, unique=True)
    imagen_url = Column(String)
    metros_cuadrados = Column(Float)
    cantidad_banos = Column(Integer)
    fuente = Column(String)
    geolocalizacion_id = Column(Integer)

class Geolocalizacion(Base):
    __tablename__ = 'geolocalizaciones'
    id = Column(Integer, primary_key=True)
    direccion = Column(String)
    latitud = Column(Float)
    longitud = Column(Float)
    puntos_interes = Column(String)

def get_icon_for_category(category):
    icon_map = {
        'restaurantes': 'cutlery',
        'bancos': 'bank',
        'transporte_publico': 'bus'
    }
    color_map = {
        'restaurantes': 'green',
        'bancos': 'blue',
        'transporte_publico': 'orange'
    }
    return folium.Icon(color=color_map.get(category, 'gray'), 
                       icon=icon_map.get(category, 'info-sign'),
                       prefix='fa')
def get_dashboard_data(session, filters):
    # Aplicar filtros a una consulta base
    base_query = session.query(LocalArriendo)
    for filter_func in filters:
        base_query = filter_func(base_query)

    # Total de locales
    total_locales = base_query.count()

    # Precio promedio
    precio_promedio = base_query.with_entities(
        func.coalesce(func.avg(cast(func.replace(LocalArriendo.precio, '.', ''), Float)), 0)
    ).scalar()

    # Metros cuadrados promedio
    metros_promedio = base_query.with_entities(
        func.coalesce(func.avg(LocalArriendo.metros_cuadrados), 0)
    ).scalar()

    # Baños promedio
    banos_promedio = base_query.with_entities(
        func.coalesce(func.avg(LocalArriendo.cantidad_banos), 0)
    ).scalar()

    # Top 5 localidades
    top_localidades = base_query.with_entities(
        LocalArriendo.localidad,
        func.count(LocalArriendo.id).label('count')
    ).group_by(LocalArriendo.localidad).order_by(func.count(LocalArriendo.id).desc()).limit(5).all()

    # Top 5 barrios
    top_barrios = base_query.with_entities(
        LocalArriendo.barrio,
        func.count(LocalArriendo.id).label('count')
    ).group_by(LocalArriendo.barrio).order_by(func.count(LocalArriendo.id).desc()).limit(5).all()

    return {
        'total_locales': total_locales,
        'precio_promedio': precio_promedio,
        'metros_promedio': metros_promedio,
        'banos_promedio': banos_promedio,
        'top_localidades': top_localidades,
        'top_barrios': top_barrios
    }

def pagination_buttons(page, total_pages, position):
    col1, col2, col3, col4, col5 = st.columns(5)

    if page > 1:
        if col2.button("Anterior", key=f"btn_anterior_{position}_{page}"):
            st.session_state.page = page - 1
            st.session_state.scroll_to_top = True
            st.rerun()
    else:
        col2.write("")  # Espacio en blanco para mantener el diseño

    col3.write(f"Página {page} de {total_pages}")

    if page < total_pages:
        if col4.button("Siguiente", key=f"btn_siguiente_{position}_{page}"):
            st.session_state.page = page + 1
            st.session_state.scroll_to_top = True
            st.rerun()
    else:
        col4.write("")  # Espacio en blanco para mantener el diseño

def get_icon_for_category(category):
    icon_map = {
        'restaurantes': 'cutlery',
        'bancos': 'bank',
        'transporte_publico': 'bus'
    }
    color_map = {
        'restaurantes': 'green',
        'bancos': 'blue',
        'transporte_publico': 'orange'
    }
    return folium.Icon(color=color_map.get(category, 'gray'), 
                       icon=icon_map.get(category, 'info-sign'),
                       prefix='fa')

def main():
    st.set_page_config(layout="wide")
    
    # Crear un espacio vacío en la parte superior
    top_space = st.empty()

    # Agregar este bloque para manejar el desplazamiento
    if 'scroll_to_top' in st.session_state and st.session_state.scroll_to_top:
        st.markdown("""
            <script>
                function scrollToTop() {
                    window.scrollTo(0, 0);
                    window.parent.scrollTo(0, 0);
                    document.body.scrollTop = 0; // Para Safari
                    document.documentElement.scrollTop = 0; // Para Chrome, Firefox, IE y Opera
                }
                scrollToTop();
            </script>
        """, unsafe_allow_html=True)
        st.session_state.scroll_to_top = False

    # Agregar un ancla al inicio de la página
    st.markdown('<a id="top"></a>', unsafe_allow_html=True)
    
    # Estilos CSS personalizados
    st.markdown("""
    <style>
    .main-title {
        color: #f00b32;
        font-size: 36px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0;
    }
    .subtitle {
        color: #f00b32;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin-top: 0;
    }
    .metric-card {
        background-color: #f00b32;
        color: #ffffff;
        padding: 10px;
        border-radius: 5px;
    }
    .metric-title {
        font-size: 18px;
        font-weight: bold;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
    }
    a {
        color: #2fb5f0;
    }
    .stButton>button {
        background-color: #f00b32;
        color: #ffffff;
    }
    .info-links {
        display: flex;
        justify-content: space-around;
        margin-bottom: 20px;
    }
    .info-link {
        text-align: center;
    }
    .info-link img {
        width: 50px;
        height: 50px;
    }
    .info-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .info-box:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-5px);
    }
    .info-box img {
        width: 50px;
        height: 50px;
        margin-bottom: 10px;
    }
    .info-box a {
        color: #f00b32;
        text-decoration: none;
        font-weight: bold;
    }
    .stat-container {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stat-box {
        background-color: white;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
       
    </style>
    """, unsafe_allow_html=True)

    # Obtener la ruta absoluta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))

    st.markdown('<p class="main-title">Búsqueda inteligente de locales comerciales</p>', unsafe_allow_html=True)
    
    #st.markdown(f"""
    #    <div class="info-box">
    #        <p class="main-title">Búsqueda inteligente de locales comerciales</p>
    #        <p class="subtitle">Te asesoramos para que encuentres tu lugar de trabajo ideal</p>
    #    </div>
    #""", unsafe_allow_html=True)
        
    st.markdown('<p class="subtitle">Te asesoramos para que encuentres tu lugar de trabajo ideal</p>', unsafe_allow_html=True)

    # Enlaces de información
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="info-box">
            <a href="https://talentotech.gov.co/portal/" target="_blank">
                <img src="data:image/png;base64,{base64.b64encode(open(os.path.join(current_dir, "static", "favicon_talento_tech.png"), "rb").read()).decode()}" alt="Talento Tech">
                <br>Acerca de Talento Tech
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="info-box">
            <a href="https://www.ccb.org.co/camara-comercio-bogota/nosotros" target="_blank">
                <img src="data:image/png;base64,{base64.b64encode(open(os.path.join(current_dir, "static", "favicon_camara_comercio.png"), "rb").read()).decode()}" alt="Cámara de Comercio">
                <br>Acerca de Cámara de Comercio
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="info-box">
            <a href="https://p4s.co/hackathon-talentotech-locales-comerciales-ccb-presencial" target="_blank">
                <img src="data:image/png;base64,{base64.b64encode(open(os.path.join(current_dir, "static", "favicon_cuadrado_p4s.png"), "rb").read()).decode()}" alt="Hackathon">
                <br>Información sobre la Hackaton
            </a>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="info-box">
            <a href="https://app.powerbi.com/view?r=eyJrIjoiMzI5ZjVlYzQtYzAyYi00ZDhiLTg5OWMtZTNjZmU0NTQ0MjAyIiwidCI6ImZkMzU1NjU1LWUzYzktNDc3NS1hNjA4LWQxZWEyZDMyYmUxZSIsImMiOjR9" target="_blank">            
                <img src="data:image/png;base64,{base64.b64encode(open(os.path.join(current_dir, 'static', 'logo_findlocalSmart.jpg'), 'rb').read()).decode()}" alt="Informe Power BI">
                <br>Informe de Power BI
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    # Cuadros de información
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px; margin-top: 20px; margin-bottom: 20px;">
        <h3 style="color: #f00b32; text-align: center;">Nuestra solución</h3>
        <p style="text-align: justify; color: #000000; font-size: 16px; line-height: 1.6; font-weight: 500;">
        En un mundo empresarial cada vez más dinámico, la identificación de locales comerciales adecuados puede ser un desafío. 
        Nuestro proyecto, desarrollado para la Cámara de Comercio en el marco del Hackathon de Talento Tech (MinTIC), 
        tiene como objetivo simplificar este proceso a través de una solución innovadora de análisis de datos.
        con el cual aspiramos a empoderar a los empresarios y arrendadores.
        </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px; margin-top: 20px; margin-bottom: 20px;">
        <h3 style="color: #f00b32; text-align: center;">Quienes somos</h3>
        <p style="text-align: justify; color: #000000; font-size: 16px; line-height: 1.6; font-weight: 500;">
        Nuestro grupo de trabajo se caracteriza por una equilibrada combinación de desarrolladores y analistas que se aseguran de darle a su empresa las mejores opciones de locales disponibles en Bogotá. Con nuestra experiencia en webscrapping y data analytics le ayudaremos a que su búsqueda sea cómoda, eficiente y exitosa. Con LocalFindSmart encontrar su lugar de trabajo ideal es pan comido.
        </p>
        </div>
        """, unsafe_allow_html=True)

    session = Session()

    # Definir variables de filtro
    st.sidebar.header("Filtros")
    precio_min = st.sidebar.number_input("Precio Mínimo", min_value=0)
    precio_max = st.sidebar.number_input("Precio Máximo", min_value=0)
    ubicacion = st.sidebar.text_input("Ubicación")
    metros_min = st.sidebar.number_input("Metros Cuadrados Mínimos", min_value=0)
    banos_min = st.sidebar.number_input("Baños Mínimos", min_value=0)

    # Añadir opciones de ordenamiento
    st.sidebar.header("Ordenar por")
    sort_option = st.sidebar.selectbox(
        "Seleccione criterio de ordenamiento",
        ["Precio (menor a mayor)", "Precio (mayor a menor)", 
         "Metros cuadrados (menor a mayor)", "Metros cuadrados (mayor a menor)",
         "Baños (menor a mayor)", "Baños (mayor a menor)"]
    )

    # Definir filtros
    filters = []
    if precio_min:
        filters.append(lambda q: q.filter(cast(func.replace(LocalArriendo.precio, '.', ''), Float) >= precio_min))
    if precio_max:
        filters.append(lambda q: q.filter(cast(func.replace(LocalArriendo.precio, '.', ''), Float) <= precio_max))
    if ubicacion:
        filters.append(lambda q: q.filter(func.unaccent(func.lower(LocalArriendo.ubicacion)).ilike(func.unaccent(f'%{ubicacion.lower()}%'))))
    if metros_min:
        filters.append(lambda q: q.filter(LocalArriendo.metros_cuadrados >= metros_min))
    if banos_min:
        filters.append(lambda q: q.filter(LocalArriendo.cantidad_banos >= banos_min))

    # Aplicar filtros y ordenamiento para la lista de resultados
    query = session.query(LocalArriendo)
    for filter_func in filters:
        query = filter_func(query)

    # Aplicar ordenamiento
    if sort_option == "Precio (menor a mayor)":
        query = query.order_by(cast(func.replace(LocalArriendo.precio, '.', ''), Float).asc())
    elif sort_option == "Precio (mayor a menor)":
        query = query.order_by(cast(func.replace(LocalArriendo.precio, '.', ''), Float).desc())
    elif sort_option == "Metros cuadrados (menor a mayor)":
        query = query.order_by(LocalArriendo.metros_cuadrados.asc())
    elif sort_option == "Metros cuadrados (mayor a menor)":
        query = query.order_by(LocalArriendo.metros_cuadrados.desc())
    elif sort_option == "Baños (menor a mayor)":
        query = query.order_by(LocalArriendo.cantidad_banos.asc())
    elif sort_option == "Baños (mayor a menor)":
        query = query.order_by(LocalArriendo.cantidad_banos.desc())

    # Obtener datos del dashboard
    dashboard_data = get_dashboard_data(session, filters)

    # Mostrar estadísticas
    #st.markdown('<div class="stat-container">', unsafe_allow_html=True)
    st.markdown("""
        <div class="stat-container" style="background-color: #e6e9ef; border: 1px solid #d1d5db; padding: 30px; margin-bottom: 30px;">
            <h2 style="color: #f00b32; text-align: center; margin-bottom: 20px;">Resumen Estadístico</h2>
    """, unsafe_allow_html=True)
    
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Total Locales", dashboard_data['total_locales'])
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Precio Promedio", f"${dashboard_data['precio_promedio']:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Metros² Promedio", f"{dashboard_data['metros_promedio']:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.metric("Baños Promedio", f"{dashboard_data['banos_promedio']:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.subheader("Top 5 Localidades")
        st.table(pd.DataFrame(dashboard_data['top_localidades'], columns=['Localidad', 'Cantidad']))
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="stat-box">', unsafe_allow_html=True)
        st.subheader("Top 5 Barrios")
        st.table(pd.DataFrame(dashboard_data['top_barrios'], columns=['Barrio', 'Cantidad']))
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Cierre del contenedor de estadísticas
    st.markdown('<hr style="border: 1px solid #e9ecef; margin-top: 30px; margin-bottom: 30px;">', unsafe_allow_html=True)
    
    # Ancla para el desplazamiento
    st.markdown('<div id="top-of-results"></div>', unsafe_allow_html=True)

    # Paginación
    total_results = query.count()
    items_per_page = 50
    total_pages = (total_results - 1) // items_per_page + 1

    # Usar session state para mantener el número de página
    if 'page' not in st.session_state:
        st.session_state.page = 1

    # Botones de paginación arriba
    st.write("Navegación de páginas:")
    pagination_buttons(st.session_state.page, total_pages, "top")

    # Crear un contenedor para los resultados
    results_container = st.container()

    # Calcular el offset basado en la página actual
    start = (st.session_state.page - 1) * items_per_page

    # Obtener los resultados para la página actual
    locales = query.offset(start).limit(items_per_page).all()

    # Mostrar resultados dentro del contenedor
    with results_container:
        st.write(f"Mostrando resultados {start + 1} - {min(start + items_per_page, total_results)} de {total_results}")
        
        if not locales:
            st.warning("No se encontraron resultados con los filtros aplicados.")
        else:
            for local in locales:
                st.markdown(f'<p class="subtitle">{local.titulo}</p>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.image(local.imagen_url, use_column_width=True)
                with col2:
                    st.write(f"Precio: ${local.precio}")
                    st.write(f"Ubicación: {local.ubicacion}")
                    st.write(f"Metros cuadrados: {local.metros_cuadrados}")
                    st.write(f"Baños: {local.cantidad_banos}")
                    st.write(f"Fuente: {local.fuente}")
                    st.markdown(f"[Ver en {local.fuente}]({local.link})")
                    
                    # Obtener información de geolocalización
                    geolocalizacion = session.query(Geolocalizacion).filter_by(id=local.geolocalizacion_id).first()
                    if geolocalizacion and geolocalizacion.latitud and geolocalizacion.longitud:
                        # Usar una clave única para cada local en session_state
                        map_key = f"show_map_{local.id}"
                        if map_key not in st.session_state:
                            st.session_state[map_key] = False
                        
                        if st.button(f"{'Ocultar' if st.session_state[map_key] else 'Ver'} mapa", key=f"btn_{local.id}"):
                            st.session_state[map_key] = not st.session_state[map_key]
                        
                        if st.session_state[map_key]:
                            m = folium.Map(location=[geolocalizacion.latitud, geolocalizacion.longitud], zoom_start=15)
                            folium.Marker(
                                [geolocalizacion.latitud, geolocalizacion.longitud],
                                popup=local.titulo,
                                icon=folium.Icon(color='red', icon='home')
                            ).add_to(m)
                            
                            # Añadir puntos de interés al mapa
                            if geolocalizacion.puntos_interes:
                                poi = geolocalizacion.puntos_interes
                                if isinstance(poi, str):
                                    try:
                                        poi = json.loads(poi)
                                    except json.JSONDecodeError:
                                        st.warning("Error al decodificar los puntos de interés")
                                        poi = {}
                                if isinstance(poi, dict):
                                    for category, places in poi.items():
                                        for place in places:
                                            # Generar coordenadas aleatorias cercanas al local
                                            lat_offset = (random.random() - 0.5) * 0.001
                                            lon_offset = (random.random() - 0.5) * 0.001
                                            poi_lat = geolocalizacion.latitud + lat_offset
                                            poi_lon = geolocalizacion.longitud + lon_offset
                                            
                                            folium.Marker(
                                                [poi_lat, poi_lon],
                                                popup=f"{category}: {place}",
                                                icon=get_icon_for_category(category)
                                            ).add_to(m)
                            
                            # Usar folium_static en lugar de st_folium
                            folium_static(m)

    # Botones de paginación abajo
    st.write("Navegación de páginas:")
    pagination_buttons(st.session_state.page, total_pages, "bottom")

    # Después de la sección de paginación, añade esto:

    st.markdown("---")  # Esto crea una línea divisoria

    st.markdown("""
    <h2 style="color: #f00b32; text-align: center;">Nuestro Equipo</h2>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px; text-align: center;">
        <h3 style="color: #000000;">Luis E. Chacon R.</h3>
        <p style="color: #000000;">Rol: Desarrollador</p>
        <p style="color: #000000;">Ingeniero de Sistemas - Especialista en Ingenieria de Software. Desarrollo Python</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px; text-align: center;">
        <h3 style="color: #000000;">Miguel E. Escobar Ch.</h3>
        <p style="color: #000000;">Rol: Analista de Datos</p>
        <p style="color: #000000;">Ingeniero Aeronautico. Desarrollo Python para análisis de datos</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px; text-align: center;">
        <h3 style="color: #000000;">Brayan E. Moreno V.</h3>
        <p style="color: #000000;">Rol: Desarrollador</p>
        <p style="color: #000000;">Estudiante Talento Tech Desarrollo Front End. Desarrollo HTML, CSS, JavaScript</p>
        </div>
        """, unsafe_allow_html=True)

    session.close()

if __name__ == '__main__':
    if 'page' not in st.session_state:
        st.session_state.page = 1
    main()

