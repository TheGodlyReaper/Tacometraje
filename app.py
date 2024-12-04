from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text, extract
from datetime import datetime
from decimal import Decimal, InvalidOperation
import calendar
import locale
import base64

app = Flask(__name__)
app.secret_key = "tu_clave_secreta"  # Necesario para usar mensajes flash

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://MyDataBase?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Para mostrar los nombres del calendario en espaniol
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

class Rol(db.Model):
    __tablename__ = 'Roles'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

# Modelo de la tabla Usuarios
class Usuario(db.Model):
    __tablename__ = 'Usuarios'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(100), nullable=False)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(100), nullable=False)
    id_rol = db.Column(db.Integer, db.ForeignKey('Roles.id_rol'), nullable=False)

    rol = db.relationship('Rol', backref='usuarios')
    
class TipoViaje(db.Model):
    __tablename__ = 'Tipo_Viaje'
    id_modo = db.Column(db.Integer, primary_key=True)
    modo = db.Column(db.String(50), unique=True, nullable=False)

# Modelo de la tabla Solicitantes
class Solicitante(db.Model):
    __tablename__ = 'Solicitantes'
    id_solicitante = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_completo = db.Column(db.NVARCHAR(100), nullable=False)
    correo = db.Column(db.NVARCHAR(100), nullable=False)
    cargo = db.Column(db.NVARCHAR(50), nullable=False)

# Modelo de la tabla Tiendas
class Tienda(db.Model):
    __tablename__ = 'Tiendas'
    id_tienda = db.Column(db.String(10), primary_key=True)
    nombre_tienda = db.Column(db.String(100), nullable=False)
    siglas = db.Column(db.NVARCHAR(10), nullable=False)


# Modelo de la tabla Tipo_Visita
class TipoVisita(db.Model):
    __tablename__ = 'Tipo_Visita'
    id_tipo = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), unique=True, nullable=False)


# Modelo de la tabla Estado_Trabajo
class EstadoTrabajo(db.Model):
    __tablename__ = 'Estado_Trabajo'
    id_estado = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.String(50), unique=True, nullable=False)


# Modelo de la tabla Distancias
class Distancia(db.Model):
    __tablename__ = 'Distancias'
    id_origen = db.Column(db.String(10), db.ForeignKey('Tiendas.id_tienda'), primary_key=True)
    id_destino = db.Column(db.String(10), db.ForeignKey('Tiendas.id_tienda'), primary_key=True)
    distancia_km = db.Column(db.Numeric(10, 2), nullable=False)

    # Definición de la relación para acceder a la tienda de origen y destino
    tienda_origen = db.relationship('Tienda', foreign_keys=[id_origen])
    tienda_destino = db.relationship('Tienda', foreign_keys=[id_destino])

# Modelo de la Estado Solicitud
class EstadoSolicitud(db.Model):
    __tablename__ = 'Estado_Solicitud'
    id_estado = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.String(50), unique=True, nullable=False)

# Modelo de la tabla Recuento_Kilometros
class RecuentoKilometros(db.Model):
    __tablename__ = 'Recuento_Kilometros'
    id_recuento = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False)
    id_solicitante = db.Column(db.Integer, db.ForeignKey('Solicitantes.id_solicitante'), nullable=False)
    id_origen = db.Column(db.String(10), db.ForeignKey('Tiendas.id_tienda'), nullable=False)
    id_destino = db.Column(db.String(10), db.ForeignKey('Tiendas.id_tienda'), nullable=False)
    fecha_visita = db.Column(db.Date, nullable=False)
    kilometros = db.Column(db.Numeric(10, 2), nullable=False)
    id_tipo_visita = db.Column(db.Integer, db.ForeignKey('Tipo_Visita.id_tipo'), nullable=False)
    detalle = db.Column(db.String(500))
    id_estado_trabajo = db.Column(db.Integer, db.ForeignKey('Estado_Trabajo.id_estado'), nullable=False)
    id_estado_solicitud = db.Column(db.Integer, db.ForeignKey('Estado_Solicitud.id_estado'), nullable=False)
    id_modo_viaje = db.Column(db.Integer, db.ForeignKey('Tipo_Viaje.id_modo'), nullable=False)
    latitud = db.Column(db.Numeric(9, 6), nullable=False)
    longitud = db.Column(db.Numeric(9, 6), nullable=False)

    # Definición de la relación para acceder a los estados de solicitud
    estado_solicitud = db.relationship('EstadoSolicitud', backref='recuentos')


# Ruta de inicio
@app.route('/', methods=['GET', 'POST'])
def login():
    session.pop('user_id', None)
    if request.method == 'POST':
        identificador = request.form['nombre_usuario']
        contrasena = request.form['contrasena']

        # Verificar si el usuario existe en la base de datos
        usuario = Usuario.query.filter(
            (Usuario.nombre_usuario == identificador) | (Usuario.correo == identificador),
            Usuario.contrasena == contrasena
        ).first()

        if usuario:
            session['user_id'] = usuario.id_usuario
            flash(f'Bienvenido {usuario.nombre_completo}', 'success')
            if usuario.rol.nombre == 'administrador' or usuario.rol.nombre == 'supervisor' or usuario.rol.nombre == 'director':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Ruta de Home con el formulario de selectores
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        id_solicitante = request.form['id_solicitante']
        origen = request.form['id_origen']
        destino = request.form['id_destino']
        fecha_visita = request.form['fecha_visita']
        detalle = request.form['detalle']
        id_tipo_visita = request.form['tipo_visita']
        id_estado_trabajo = request.form['estado_trabajo']
        id_modo = request.form['tipo_viaje']

        # Obtener latitud y longitud del formulario
        latitud = request.form.get('latitud', '').strip()
        longitud = request.form.get('longitud', '').strip()

        # Validar y convertir latitud y longitud a Decimal solo si no están vacíos
        try:
            # Si latitud y longitud tienen un valor no vacío, convertimos a Decimal
            if latitud:
                latitud = Decimal(latitud)
            else:
                latitud = None  # O asignar un valor predeterminado, por ejemplo, 0.0

            if longitud:
                longitud = Decimal(longitud)
            else:
                longitud = None  # O asignar un valor predeterminado, por ejemplo, 0.0
        except (ValueError, InvalidOperation) as e:
            # Manejar el error si la conversión falla
            flash("Las coordenadas no son válidas. Asegúrese de que sean números decimales.", 'danger')
            return redirect(url_for('home'))  # Volver al formulario

        signature_data = request.form.get('signature')
        if signature_data:
            # Decodificar la imagen de la firma de base64
            header, encoded = signature_data.split(",", 1)
            decoded_signature = base64.b64decode(encoded)
            # Guardar la firma como archivo si es necesario
            with open('firma.png', 'wb') as f:
                f.write(decoded_signature)

        # Validar que el origen y destino no sean iguales
        if origen == destino:
            flash('El origen y destino no pueden ser la misma tienda', 'danger')
        else:
            # Obtener la distancia entre las tiendas seleccionadas
            distancia = Distancia.query.filter_by(id_origen=origen, id_destino=destino).first()

            if distancia:
                # Usar la distancia de la base de datos
                kilometros = distancia.distancia_km
            else:
                # Manejar el caso cuando no existe una distancia registrada
                flash('No hay una distancia registrada entre estas tiendas', 'danger')
                return redirect(url_for('home'))  # Volver al formulario

            # Crear una nueva entrada en Recuento_Kilometros
            nuevo_recuento = RecuentoKilometros(
                id_usuario=session.get('user_id'),
                # Asegúrate de que el ID de usuario se esté guardando correctamente en la sesión
                id_solicitante=id_solicitante,
                id_origen=origen,
                id_destino=destino,
                fecha_visita=datetime.strptime(fecha_visita, '%Y-%m-%d').date(),
                kilometros=float(kilometros),  # Convertir a flotante si es necesario
                detalle=detalle,
                id_tipo_visita=id_tipo_visita,
                id_estado_trabajo=id_estado_trabajo,
                id_estado_solicitud=2,
                id_modo_viaje = id_modo,
                latitud=Decimal(latitud),
                longitud=Decimal(longitud)
            )

            db.session.add(nuevo_recuento)
            db.session.commit()

            flash('Recuento de kilómetros guardado exitosamente', 'success')
            return redirect(url_for('home'))

    # Obtener datos para el formulario
    tiendas = Tienda.query.all()
    tipos_visita = TipoVisita.query.all()
    estados_trabajo = EstadoTrabajo.query.all()
    distancias = {}  # Almacenar distancias para la lógica de JavaScript
    solicitantes = Solicitante.query.all()
    tipo_viaje = TipoViaje.query.all()

    # Población de las distancias en formato de diccionario
    for distancia in Distancia.query.all():
        if distancia.id_origen not in distancias:
            distancias[distancia.id_origen] = {}
        distancias[distancia.id_origen][distancia.id_destino] = distancia.distancia_km

    return render_template('index.html', tiendas=tiendas, tipos_visita=tipos_visita, estados_trabajo=estados_trabajo,
                           distancias=distancias, solicitantes=solicitantes, tipo_viaje=tipo_viaje)

# Ruta de recuperación de contraseña
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    usuarios = Usuario.query.all()  # Obtener todos los usuarios
    estado = EstadoSolicitud.query.all()
    recuentos_kilometros = RecuentoKilometros.query

    # Filtrar por usuario
    user_id = request.form.get('user_id')
    if user_id:
        recuentos_kilometros = recuentos_kilometros.filter_by(id_usuario=user_id)
    
    # Filtrar por estado de solicitud
    state_id = request.form.get('state_id')
    if state_id:
        recuentos_kilometros = recuentos_kilometros.filter_by(id_estado_solicitud=state_id)

    # Filtrar por fechas
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        recuentos_kilometros = recuentos_kilometros.filter(
            RecuentoKilometros.fecha_visita.between(fecha_inicio, fecha_fin)
        )
    
    recuentos_kilometros = recuentos_kilometros.all()

    # Convertir los registros a un formato más amigable
    recuentos_con_nombres = []
    for recuento in recuentos_kilometros:
        usuario = db.session.get(Usuario, recuento.id_usuario)
        solicitante = db.session.get(Solicitante, recuento.id_solicitante)
        tienda_origen = db.session.get(Tienda, recuento.id_origen)
        tienda_destino = db.session.get(Tienda, recuento.id_destino)
        estado_trabajo = db.session.get(EstadoTrabajo, recuento.id_estado_trabajo)
        estado_solicitud = db.session.get(EstadoSolicitud, recuento.id_estado_solicitud)

        recuentos_con_nombres.append({
            'id_recuento': recuento.id_recuento,
            'usuario_nombre': usuario.nombre_completo if usuario else 'Desconocido',
            'solicitante_nombre': solicitante.nombre_completo if solicitante else 'Desconocido',
            'origen_nombre': tienda_origen.siglas if tienda_origen else 'Desconocido',
            'destino_nombre': tienda_destino.siglas if tienda_destino else 'Desconocido',
            'fecha_visita': recuento.fecha_visita,
            'kilometros': recuento.kilometros,
            'detalle': recuento.detalle,
            'estado_trabajo': estado_trabajo.estado if estado_trabajo else 'Desconocido',
            'estado_solicitud': estado_solicitud.estado if estado_solicitud else 'Desconocido',
        })

    return render_template('dashboard.html', recuentos=recuentos_con_nombres, usuarios=usuarios, estado = estado)

# Ruta de recuperación de contraseña
@app.route('/recovery')
def recovery():
    return render_template('recovery.html')

@app.route('/travel-routes')
def get_travel_routes():
    routes = db.session.query(
        RecuentoKilometros,
        Usuario.nombre_completo  # Accede correctamente al campo `nombre_completo` de la tabla Usuario
    ).join(Usuario, Usuario.id_usuario == RecuentoKilometros.id_usuario).all()

    # Construir los datos que se enviarán al frontend
    route_data = []
    for route in routes:
        # Asegurarse de que latitud y longitud sean números válidos
        lat = float(route.RecuentoKilometros.latitud) if route.RecuentoKilometros.latitud is not None else None
        lng = float(route.RecuentoKilometros.longitud) if route.RecuentoKilometros.longitud is not None else None

        route_data.append({
            'technician_name': route.nombre_completo,
            'latitude': lat,
            'longitude': lng
        })
    
    return jsonify(route_data)

@app.route('/technician-routes')
def get_all_technician_routes():
    technician_id = request.args.get('tecnico', type=int)  # Obtener el ID del técnico si se envía
    query = db.session.query(
        RecuentoKilometros,
        Usuario.nombre_completo
    ).join(Usuario, Usuario.id_usuario == RecuentoKilometros.id_usuario)

    # Filtrar por técnico si se especifica
    if technician_id:
        query = query.filter(RecuentoKilometros.id_usuario == technician_id)

    routes = query.all()

    # Construir los datos de las rutas
    route_data = []
    for route in routes:
        lat = float(route.RecuentoKilometros.latitud) if route.RecuentoKilometros.latitud is not None else None
        lng = float(route.RecuentoKilometros.longitud) if route.RecuentoKilometros.longitud is not None else None

        route_data.append({
            'technician_name': route.nombre_completo,
            'latitude': lat,
            'longitude': lng,
            'visit_date': route.RecuentoKilometros.fecha_visita.strftime('%Y-%m-%d')
        })
    
    return jsonify(route_data)

@app.route('/map')
def map_view():
    return render_template('maps.html')


# Ruta para servir imágenes estáticas
@app.route('/img/<path:filename>')
def serve_image(filename):
    return send_from_directory('static/img', filename)


# Vistas para cada sección del dashboard

@app.route('/vista-general')
def vista_general():
    # Existing metrics
    total_kilometros = db.session.query(func.sum(RecuentoKilometros.kilometros)).scalar() or 0
    total_viajes = RecuentoKilometros.query.count()
    usuarios_activos = db.session.query(Usuario).join(RecuentoKilometros).distinct().count()
    
    # Tiendas más visitadas
    tiendas_visitadas = db.session.query(
        Tienda.siglas, 
        func.count(RecuentoKilometros.id_recuento).label('total_visitas')
    ).join(RecuentoKilometros, Tienda.id_tienda == RecuentoKilometros.id_destino)\
     .group_by(Tienda.siglas)\
     .order_by(text('total_visitas DESC'))\
     .limit(5).all()
    
    # Usuarios con más kilómetros
    usuarios_kilometros = db.session.query(
        Usuario.nombre_completo, 
        func.sum(RecuentoKilometros.kilometros).label('total_kilometros')
    ).join(RecuentoKilometros).group_by(Usuario.nombre_completo)\
     .order_by(text('total_kilometros DESC'))\
     .limit(5).all()
    
    # Estado de solicitudes
    estados_solicitud = db.session.query(
        EstadoSolicitud.estado, 
        func.sum(RecuentoKilometros.kilometros).label('total_kilometros')
    ).join(RecuentoKilometros).group_by(EstadoSolicitud.estado).all()
    
    return render_template('vista_general.html', 
        total_kilometros=total_kilometros, 
        total_viajes=total_viajes,
        usuarios_activos=usuarios_activos,
        tiendas_visitadas=tiendas_visitadas,
        usuarios_kilometros=usuarios_kilometros,
        estados_solicitud=estados_solicitud
    )

@app.route('/aprobar-recuento/<int:id_recuento>', methods=['POST'])
def aprobar_recuento(id_recuento):
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))

    # Obtener el usuario actual
    usuario_actual = Usuario.query.get(session['user_id'])

    # Buscar el recuento
    recuento = RecuentoKilometros.query.get(id_recuento)
    
    if not recuento:
        flash('Recuento no encontrado.', 'danger')
        return redirect(url_for('vista_detallada'))

    # Lógica de aprobación basada en el rol del usuario
    try:
        if usuario_actual.rol.nombre == 'supervisor':
            # Si el estado actual es Pendiente (id 2), cambiarlo a Pendiente Director (id 3)
            if recuento.id_estado_solicitud == 2:
                recuento.id_estado_solicitud = 3  # Pendiente Director
                db.session.commit()
                flash('Recuento enviado para aprobación del director.', 'success')
            else:
                flash('No se puede aprobar este recuento en este momento.', 'warning')
        
        elif usuario_actual.rol.nombre == 'director':
            # Si el estado actual es Pendiente Director (id 3), cambiarlo a Aprobado por Director (id 4)
            if recuento.id_estado_solicitud == 3:
                recuento.id_estado_solicitud = 4  # Aprobado por Director
                db.session.commit()
                flash('Recuento aprobado por director.', 'success')
            else:
                flash('No se puede aprobar este recuento en este momento.', 'warning')
        
        else:
            flash('No tienes permisos para aprobar recuentos.', 'danger')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al aprobar el recuento: {str(e)}', 'danger')

    return redirect(url_for('vista_detallada'))

@app.route('/vista-detallada', methods=['GET', 'POST'])
def vista_detallada():
    # Verificar si el usuario está autenticado
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))

    # Obtener el usuario actual al principio de la función
    usuario_actual = Usuario.query.get(session['user_id'])

    usuarios = Usuario.query.all()  # Obtener todos los usuarios
    estado = EstadoSolicitud.query.all()
    recuentos_kilometros = RecuentoKilometros.query

    # Inicializar filtros con valores por defecto
    filtros = {
        'user_id': None,
        'state_id': None,
        'fecha_inicio': None,
        'fecha_fin': None
    }

    # Filtrar por usuario
    user_id = request.form.get('user_id')
    if user_id:
        filtros['user_id'] = user_id  # Actualizar filtros con el valor seleccionado
        recuentos_kilometros = recuentos_kilometros.filter_by(id_usuario=user_id)
    
    # Filtrar por estado de solicitud
    state_id = request.form.get('state_id')
    if state_id:
        filtros['state_id'] = state_id  # Actualizar filtros con el valor seleccionado
        recuentos_kilometros = recuentos_kilometros.filter_by(id_estado_solicitud=state_id)

    # Filtrar por fechas
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        filtros['fecha_inicio'] = fecha_inicio  # Actualizar filtros con el valor seleccionado
        filtros['fecha_fin'] = fecha_fin  # Actualizar filtros con el valor seleccionado
        recuentos_kilometros = recuentos_kilometros.filter(
            RecuentoKilometros.fecha_visita.between(fecha_inicio, fecha_fin)
        )
    
    recuentos_kilometros = recuentos_kilometros.all()

    # Convertir los registros a un formato más amigable
    recuentos_con_nombres = []
    for recuento in recuentos_kilometros:
        usuario = db.session.get(Usuario, recuento.id_usuario)
        solicitante = db.session.get(Solicitante, recuento.id_solicitante)
        tienda_origen = db.session.get(Tienda, recuento.id_origen)
        tienda_destino = db.session.get(Tienda, recuento.id_destino)
        estado_trabajo = db.session.get(EstadoTrabajo, recuento.id_estado_trabajo)
        estado_solicitud = db.session.get(EstadoSolicitud, recuento.id_estado_solicitud)
        modo_viaje = db.session.get(TipoViaje, recuento.id_modo_viaje)

        # Determinar si el usuario puede aprobar basado en su rol y el estado actual
        puede_aprobar = False
        if usuario_actual.rol.nombre == 'supervisor':
            # El supervisor puede aprobar solicitudes en estado Pendiente (id 2)
            puede_aprobar = (recuento.id_estado_solicitud == 2)
        elif usuario_actual.rol.nombre == 'director':
            # El director puede aprobar solicitudes en estado Pendiente Director (id 3)
            puede_aprobar = (recuento.id_estado_solicitud == 3)

        recuentos_con_nombres.append({
            'id_recuento': recuento.id_recuento,
            'usuario_nombre': usuario.nombre_completo if usuario else 'Desconocido',
            'solicitante_nombre': solicitante.nombre_completo if solicitante else 'Desconocido',
            'origen_nombre': tienda_origen.siglas if tienda_origen else 'Desconocido',
            'destino_nombre': tienda_destino.siglas if tienda_destino else 'Desconocido',
            'fecha_visita': recuento.fecha_visita,
            'kilometros': recuento.kilometros,
            'detalle': recuento.detalle,
            'estado_trabajo': estado_trabajo.estado if estado_trabajo else 'Desconocido',
            'estado_solicitud': estado_solicitud.estado if estado_solicitud else 'Desconocido',
            'modo_viaje': modo_viaje.modo if modo_viaje else 'Desconocido',
            'puede_aprobar': puede_aprobar
        })

    return render_template('vista_detallada.html', filtros=filtros, recuentos=recuentos_con_nombres, usuarios=usuarios, estado=estado)



import calendar  # Importar la biblioteca para obtener nombres de meses

@app.route('/vista-estadisticas')
def vista_estadisticas():
    # Verificar autenticación
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero.', 'danger')
        return redirect(url_for('login'))

    # Obtener usuarios para el selector
    usuarios = Usuario.query.all()

    # Obtener el ID del técnico del filtro
    technician_id = request.args.get('tecnico', type=int)

    # Estadísticas más avanzadas
    query = db.session.query(
        extract('year', RecuentoKilometros.fecha_visita).label('year'),
        extract('month', RecuentoKilometros.fecha_visita).label('month'),
        func.sum(RecuentoKilometros.kilometros).label('total_kilometros')
    ).group_by(
        extract('year', RecuentoKilometros.fecha_visita),
        extract('month', RecuentoKilometros.fecha_visita)
    ).order_by('year', 'month')

    # Aplicar filtro por técnico si se selecciona
    if technician_id:
        query = query.filter(RecuentoKilometros.id_usuario == technician_id)

    stats_por_mes = query.all()

    # Convertir números de mes a nombres
    stats_por_mes = [
        (calendar.month_name[int(stat[1])].capitalize(), stat[0], stat[2])
        for stat in stats_por_mes
    ]

    estados_solicitud = db.session.query(
        EstadoSolicitud.estado,
        func.count(RecuentoKilometros.id_recuento).label('total')
    ).join(RecuentoKilometros).group_by(EstadoSolicitud.estado).all()

    return render_template(
        'vista_estadisticas.html',
        usuarios=usuarios,  # Agregar usuarios al contexto
        stats_por_mes=stats_por_mes,
        estados_solicitud=estados_solicitud
    )


if __name__ == '__main__':
    app.run(debug=True)