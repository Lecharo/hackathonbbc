from flask import Flask, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import Optional
from sqlalchemy import func, distinct, cast, Float, text
from sqlalchemy.sql.expression import case

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/hackatonccb'
app.config['SECRET_KEY'] = '2ab6315bf70b1007f7631c751144fd0d'
db = SQLAlchemy(app)

# Asegúrate de que la extensión unaccent esté habilitada en tu base de datos
with app.app_context():
    db.session.execute(text('CREATE EXTENSION IF NOT EXISTS unaccent'))
    db.session.commit()

class LocalArriendo(db.Model):
    __tablename__ = 'locales_arriendo'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String)
    precio = db.Column(db.String)
    ubicacion = db.Column(db.String)  # Campo de ubicación completo
    ciudad = db.Column(db.String)
    localidad = db.Column(db.String)
    barrio = db.Column(db.String)
    link = db.Column(db.String, unique=True)
    imagen_url = db.Column(db.String)
    metros_cuadrados = db.Column(db.Float)
    cantidad_banos = db.Column(db.Integer)
    fuente = db.Column(db.String)

class FilterForm(FlaskForm):
    precio_min = IntegerField('Precio Mínimo', validators=[Optional()])
    precio_max = IntegerField('Precio Máximo', validators=[Optional()])
    ubicacion = StringField('Ubicación', validators=[Optional()])  # Campo para buscar en la ubicación completa
    ciudad = StringField('Ciudad', validators=[Optional()])
    localidad = StringField('Localidad', validators=[Optional()])
    barrio = StringField('Barrio', validators=[Optional()])
    metros_min = IntegerField('Metros Cuadrados Mínimos', validators=[Optional()])
    banos_min = IntegerField('Baños Mínimos', validators=[Optional()])
    submit = SubmitField('Filtrar')

def get_dashboard_data(filtered_query):
    total_locales = filtered_query.count()
    precio_promedio = filtered_query.with_entities(func.avg(cast(func.replace(LocalArriendo.precio, '.', ''), Float))).scalar()
    metros_promedio = filtered_query.with_entities(func.avg(LocalArriendo.metros_cuadrados)).scalar()
    banos_promedio = filtered_query.with_entities(func.avg(LocalArriendo.cantidad_banos)).scalar()
    
    top_localidades = filtered_query.with_entities(
        LocalArriendo.localidad,
        func.count(distinct(LocalArriendo.id)).label('count')
    ).group_by(LocalArriendo.localidad).order_by(text('count DESC')).limit(5).all()

    top_barrios = filtered_query.with_entities(
        LocalArriendo.barrio,
        func.count(distinct(LocalArriendo.id)).label('count')
    ).group_by(LocalArriendo.barrio).order_by(text('count DESC')).limit(5).all()

    return {
        'total_locales': total_locales,
        'precio_promedio': precio_promedio,
        'metros_promedio': metros_promedio,
        'banos_promedio': banos_promedio,
        'top_localidades': top_localidades,
        'top_barrios': top_barrios
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    form = FilterForm(request.args)
    query = LocalArriendo.query

    if request.method == 'POST':
        form = FilterForm(request.form)

    if form.validate():
        if form.precio_min.data:
            query = query.filter(cast(func.replace(LocalArriendo.precio, '.', ''), Float) >= form.precio_min.data)
        if form.precio_max.data:
            query = query.filter(cast(func.replace(LocalArriendo.precio, '.', ''), Float) <= form.precio_max.data)
        if form.ubicacion.data:
            query = query.filter(func.lower(func.unaccent(LocalArriendo.ubicacion)).like(
                func.lower(func.unaccent(f'%{form.ubicacion.data}%'))
            ))
        if form.ciudad.data:
            query = query.filter(func.lower(func.unaccent(LocalArriendo.ciudad)).like(
                func.lower(func.unaccent(f'%{form.ciudad.data}%'))
            ))
        if form.localidad.data:
            query = query.filter(func.lower(func.unaccent(LocalArriendo.localidad)).like(
                func.lower(func.unaccent(f'%{form.localidad.data}%'))
            ))
        if form.barrio.data:
            query = query.filter(func.lower(func.unaccent(LocalArriendo.barrio)).like(
                func.lower(func.unaccent(f'%{form.barrio.data}%'))
            ))
        if form.metros_min.data:
            query = query.filter(LocalArriendo.metros_cuadrados >= form.metros_min.data)
        if form.banos_min.data:
            query = query.filter(LocalArriendo.cantidad_banos >= form.banos_min.data)
        if form.fuente.data:
            query = query.filter(LocalArriendo.fuente == form.fuente.data)

    page = request.args.get('page', 1, type=int)
    locales = query.paginate(page=page, per_page=20, error_out=False)
    dashboard_data = get_dashboard_data(query)
    
    return render_template('index.html', locales=locales, form=form, dashboard_data=dashboard_data)

if __name__ == '__main__':
    app.run(debug=True)
