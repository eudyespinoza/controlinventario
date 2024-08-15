# Dentro de este módulo se consiguen las siguientes funciones:
# Inicializacion de la DB para los logs
# Funcion para guardar los logs establecidos


import app
import sqlite3
import datetime


# Crear tabla si no existe
def initialize_db():
    with sqlite3.connect(app.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                username TEXT,
                message TEXT
            )
        ''')
        conn.commit()


# Función para registrar el mensaje
def log_message(message):
    initialize_db()
    username = app.session.get('user', 'Usuario_Desconocido')
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with sqlite3.connect(app.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (timestamp, username, message) 
            VALUES (?, ?, ?)
        ''', (timestamp, username, message))
        conn.commit()

    # Eliminar registros que tengan más de 3 meses
    three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(app.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM logs 
            WHERE timestamp < ?
        ''', (three_months_ago,))
        conn.commit()
