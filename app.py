from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import log_save
import sqlite3
from flask_session import Session
from datetime import timedelta
import configparser
import auth
import get_tr_out_in
import procesar


# Leer configuración desde config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuración de sesiones flask
app = Flask(__name__)
app.secret_key = config['flask']['secret_key']
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
Session(app)

# Definir timeout para consultas
timeout_minutes = 2
timeout_seconds = timeout_minutes * 60

# Configuración LDAP
LDAP_SERVER = config['ldap']['server']
LDAP_DOMAIN = config['ldap']['domain']
LDAP_BASE_DN = config['ldap']['base_dn']

# Configuracion de conexión Mulesoft
API = config['mulesoft']['api_prod']
API_QA = config['mulesoft']['api_qa']
CLIENT_ID_MULESOFT = config['mulesoft']['client_id']
CLIENT_ID_MULESOFT_PROD = config['mulesoft']['client_id_prod']
CLIENT_SECRET_MULESOFT_PROD = config['mulesoft']['client_secret_prod']
CLIENT_SECRET_MULESOFT = config['mulesoft']['client_secret']
RESOURCE_MULESOFT = config['mulesoft']['resource']
RESOURCE_MULESOFT_PROD = config['mulesoft']['resource_prod']

# Configuración de conexión al DW
DW_USER = config['dw']['user'].replace("'", "")
DW_PWD = config['dw']['password'].replace("'", "")
DW_HOST = config['dw']['host'].replace("'", "")
DW_PORT = config['dw']['port'].replace("'", "")
DW_A071 = config['dw']['ingestion_a071']
DW_KONP = config['dw']['ingestion_konp']
DW_SCHEMA = config['dw']['consuptio_schema'].replace("'", "")

# Configuración de conexión GRAPH
CLIENT_GRAPH = config['graph']['client']
CLIENT_ID_GRAPH = config['graph']['client_id']
CLIENT_SECRET_GRAPH = config['graph']['client_secret']

# Configuración de conexión a D365
TOKEN_CLIENT = config['d365']['token_client']

# Configuración de la base de datos SQL
SQL_SERVER = config['database_enum']['server']
SQL_SERVER_QA = config['database_enum']['server_qa']
SQL_DATABASE = config['database_enum']['database']
SQL_USERNAME = config['database_enum']['username']
SQL_PASSWORD = config['database_enum']['password']

DB_PATH = 'log.db'


@app.route('/')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login_post():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        authenticated, error = auth.ldap_authenticate(username, password)
        if not authenticated:
            flash(error, 'danger')
            log_save.log_message(f"credenciales incorrectas usuario: {username}")
            return redirect(url_for('login'))

        authorized, error = auth.get_authorization(username)
        if not authorized:
            flash(error, 'danger')
            log_save.log_message(f"Usuario {username} no autorizado")
            return redirect(url_for('login'))

        log_save.log_message(f"Inicio de sesion exitoso usuario: {session.get('user')}")
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    tabla_seleccionada = request.args.get('tabla', 'TR_OUT')
    if tabla_seleccionada == 'TR_OUT':
        columnas, datos = get_tr_out_in.obtener_datos_tr_out()
    else:
        columnas, datos = get_tr_out_in.obtener_datos_tr_in()

    return render_template('dashboard.html', columnas=columnas, datos=datos, tabla_seleccionada=tabla_seleccionada)


@app.route('/actualizar')
def actualizar():
    tabla_seleccionada = request.args.get('tabla', 'TR_OUT')
    if tabla_seleccionada == 'TR_OUT':
        columnas, datos = get_tr_out_in.obtener_datos_tr_out()
    else:
        columnas, datos = get_tr_out_in.obtener_datos_tr_in()

    return jsonify({
        'columnas': columnas,
        'datos': datos
    })


@app.route('/procesar', methods=['POST'])
def procesar_transferencia():
    if not request.json:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    fila = request.json
    tabla = fila.get('tabla')  # Obtenemos la tabla seleccionada

    lista_keracasa = ["SM01", "LF01", "SJ01", "DT01", "IT01", "FV01", "LN01", "MR01", "ES01"]

    if tabla == 'TR_OUT':
        json_data = {
            "DocumentType": "5",
            "OperationType": "3",
            "TalonarioRemito": "",
            "ShipCarrierName": "",
            "DriverDocumentId": "",
            "TruckPlateId": "",
            "TrailerPlateId": "",
            "CompanionDocumentId": "",
            "ShipCarrierId": "",
            "updateStockItemRequest": [
                {
                    "DocumentNumber": fila['documento'],
                    "ItemId": fila['material_applog'],
                    "SalesDeliveryNow": fila['cantidad'],
                    "QtyShipNow": float(fila['cantidad']),
                    "InventTransId": fila.get('posicion', ''),  # Posición puede ser opcional
                    "JournalNameId": "",
                    "InventLocationIdFrom": fila['origen'] + "DP",
                    "InventSiteIdFrom": "LF" if fila['origen'] in lista_keracasa else fila['origen'][:2],
                    "InventLocationIdTo": fila['destino'] + "DP",
                    "InventSiteIdTo": "LF" if fila['destino'] in lista_keracasa else fila['destino'][:2],
                    "BerObservations": "",
                    "PackingSlipId": fila.get('remito', '')  # Remito puede ser opcional
                }
            ]
        }
    else:
        json_data = {
            "DocumentType": "4",
            "OperationType": "3",
            "Items": [
                {
                    "PackingSlipId": "",
                    "ShipDocumentId": "",
                    "DocumentNumber": fila['documento'],
                    "ItemId": fila['material_applog'],
                    "SalesDeliveryNow": fila['cantidad'],
                    "InventLocationIdTo": fila['destino'] + "DP",
                    "FailedDeliveryReasonId": "",
                    "InventTransId": "",
                    "CierreDirecto": 1
                }
            ]
        }

    # Pasamos la tabla seleccionada a la función de procesamiento
    return procesar.process_file_send(json_data, tabla)


@app.route('/log', methods=['GET', 'POST'])
def log():
    logs = []
    if request.method == 'POST':
        username = request.form.get('username')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        message = request.form.get('message')

        query = 'SELECT timestamp, username, message FROM logs WHERE 1=1'
        params = []

        if username:
            query += ' AND username = ?'
            params.append(username)

        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date + ' 23:59:59')

        if message:
            query += ' AND message LIKE ?'
            params.append('%' + message + '%')

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            logs = cursor.fetchall()

    return render_template('log.html', logs=logs, request=request)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
