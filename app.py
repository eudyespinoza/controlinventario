import openpyxl
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import log_save
import sqlite3
from flask_session import Session
from datetime import timedelta
import configparser
import auth
import get_tr_out_in
import procesar
import requests
import pandas as pd
import io


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
        user = session.get('user')
        return render_template('index.html', user=user)
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login_post():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        authenticated, error = auth.ldap_authenticate(username, password)
        if not authenticated:
            flash("Credenciales inválidas", 'danger')
            log_save.log_message(f"credenciales incorrectas usuario: {username}")
            return redirect(url_for('login'))

        authorized, error = auth.get_authorization(username)
        if not authorized:
            flash("Usuario no autorizado", 'danger')
            log_save.log_message(f"Usuario {username} no autorizado")
            return redirect(url_for('login'))

        log_save.log_message(f"Inicio de sesion exitoso usuario: {session.get('user')}")
        return redirect(url_for('login'))

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

    return render_template('dashboard.html',
                           columnas=columnas,
                           datos=datos,
                           tabla_seleccionada=tabla_seleccionada)


@app.route('/procesadas')
def procesadas():
    if 'user' not in session:
        return redirect(url_for('login'))

    tabla_seleccionada = request.args.get('tabla', 'TR_OUT')

    if tabla_seleccionada == 'TR_OUT':
        columnas, datos = get_tr_out_in.obtener_todas_tr_out_procesadas()
    else:
        columnas, datos = get_tr_out_in.obtener_todas_tr_in_procesadas()

    return render_template('procesadas.html',
                           columnas=columnas,
                           datos=datos,
                           tabla_seleccionada=tabla_seleccionada)


@app.route('/ajuste')
def ajuste():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('upload.html')


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
        return jsonify({'success': False, 'message': 'No se obtuvieron datos para procesar'}), 400

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


@app.route('/exportar_excel')
def exportar_excel():
    if 'user' not in session:
        return redirect(url_for('login'))

    tabla_seleccionada = request.args.get('tabla', 'TR_OUT')

    # Obtener datos según la tabla seleccionada
    if tabla_seleccionada == 'TR_OUT':
        columnas, datos = get_tr_out_in.obtener_datos_tr_out()
    else:
        columnas, datos = get_tr_out_in.obtener_datos_tr_in()

    # Crear un DataFrame de Pandas con los datos obtenidos
    df = pd.DataFrame(datos, columns=columnas)

    # Crear un buffer en memoria para el archivo Excel
    output = io.BytesIO()

    # Escribir el DataFrame a un archivo Excel en el buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    output.seek(0)

    # Enviar el archivo Excel como respuesta
    return send_file(output, as_attachment=True, download_name=f"{tabla_seleccionada}_export.xlsx",
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/exportar_procesadas_excel')
def exportar_procesadas_excel():
    if 'user' not in session:
        return redirect(url_for('login'))

    tabla_seleccionada = request.args.get('tabla', 'TR_OUT')

    if tabla_seleccionada == 'TR_OUT':
        columnas, datos = get_tr_out_in.obtener_todas_tr_out_procesadas()
    else:
        columnas, datos = get_tr_out_in.obtener_todas_tr_in_procesadas()

    # Crear un DataFrame de Pandas con los datos obtenidos
    df = pd.DataFrame(datos, columns=columnas)

    # Crear un buffer en memoria para el archivo Excel
    output = io.BytesIO()

    # Escribir el DataFrame a un archivo Excel en el buffer
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    output.seek(0)

    # Enviar el archivo Excel como respuesta
    return send_file(output,
                     as_attachment=True,
                     download_name=f"{tabla_seleccionada}_procesadas_export.xlsx",
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


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

@app.route('/process', methods=['POST'])
def process_file():
    file = request.files.get('file')

    if not file:
        return jsonify({'success': False, 'message': 'No se ha seleccionado ningún archivo'})

    if not file.filename.endswith(('.xls', '.xlsx')):
        return jsonify({'success': False, 'message': 'Formato de archivo no válido'})

    try:
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active
        data = []
        headers = []

        # Contador de filas procesadas
        max_rows = 650
        row_count = 0

        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i == 0:
                headers = row  # Guardamos los encabezados
            else:
                data.append(row)
                row_count += 1
                if row_count >= max_rows:
                    return jsonify({'success': False,
                                    'message': 'El número de líneas a procesar no puede ser mayor a 650'})

        return jsonify({'success': True, 'headers': headers, 'data': data})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Ocurrió un error al procesar el archivo: {str(e)}'})


@app.route('/process-send', methods=['POST'])
def process_file_send():
    try:
        file = request.files['file']
        app.logger.info("file: %s", file)
        df = pd.read_excel(file)
        data = df.to_dict(orient='records')

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
            "updateStockItemRequest": []
        }
        for item in data:
            json_data["updateStockItemRequest"].append({
                "DocumentNumber": 1,
                "ItemId": str(item['ARTICULO']),
                "SalesDeliveryNow": float(item['CANTIDAD']),
                "QtyShipNow": 999999,
                "InventTransId": "",
                "JournalNameId": "Conteo Stock",
                "InventLocationIdFrom": str(item['DEPOSITO']) + "DP",
                "InventSiteIdFrom": "",
                "InventLocationIdTo": "",
                "InventSiteIdTo": "",
                "BerObservations": ""
            })

        access_token = procesar.get_access_token()
        headers = {"Authorization": "Bearer {}".format(access_token), "Content-Type": "application/json"}
        api_url = API_QA
        response = requests.post(api_url, json=json_data, headers=headers)
        app.logger.info("API Response: %s", response.text)
        if response.status_code == 200:
            response_json = response.json()
            if "message" in response_json and response_json["message"] == "Ok":
                log_save.log_message(f"Se realizo el ajuste correctamente {json_data}")
                return jsonify({'success': True, 'message': 'Se realizó el ajuste correctamente'})
            else:
                log_save.log_message(f"No se pudo realizar el ajuste {response.text}")
                return jsonify({'success': False, 'message': response_json["message"]})
        elif response.status_code == 500:
            response_json = response.json()
            return jsonify({'success': False, 'message': response.text})
        elif response.status_code == 400:
            response_json = response.json()
            return jsonify({'success': False, 'message': response.text})
        else:
            # Devolver respuesta JSON con mensaje de error
            return jsonify({'success': False, 'message': 'Error en la solicitud a la API'})
    except Exception as e:
        # Manejo de errores generales
        app.logger.error("Error en la función process_file_send: %s", str(e))
        return jsonify({'success': False, 'message': f'Error interno en el servidor {e}'})


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
