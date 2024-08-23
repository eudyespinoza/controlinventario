import pyodbc
import app
import log_save
import re


def conectar_db():
    try:
        conexion = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f'SERVER={app.SQL_SERVER_QA};'
            f'DATABASE={app.SQL_DATABASE};'
            f'UID={app.SQL_USERNAME};'
            f'PWD={app.SQL_PASSWORD}'
        )
        return conexion
    except pyodbc.Error as e:
        log_save.log_message(f"Error al conectar con la base de datos: {e}")
        raise


def convertir_error_legible(error):

    match_stock = re.search(r'libre por debajo de ([\d,\.]+) (PI|M2|KG|M3)', error)

    if match_stock:
        cantidad = match_stock.group(1)
        unidad = match_stock.group(2)
        return f"Error de Stock {cantidad} {unidad}"

    match_valoracion = re.search(r'están bloqueados por el usuario (\w+)', error)

    if match_valoracion:
        usuario = match_valoracion.group(1)
        return f"Material bloqueado en SAP por {usuario}."

    match_documento = re.search(r'NO OK:El usuario (\w+) ya está tratando \w+', error)

    if match_documento:
        usuario = match_documento.group(1)
        return f"El usuario {usuario} está tratando el documento"

    elif "no contiene ninguna posición" in error:
        return "Linea eliminada. Ver con Analista de Distribución"
    elif "Cantidad tomada excedido" in error:
        return "Pedido no despachado o Error en despacho"
    elif "500" in error:
        return "Error de comunicación entre los sistemas. Intente más tarde"
    elif "material no concuerdan con los datos de pedido" in error:
        return "OT creada con múltiples destinos. Ver con Analista Distribución"
    else:
        return "Error de comunicació entre los sistemas. Intente más tarde"


def obtener_datos_tr_out():
    conexion = conectar_db()
    cursor = conexion.cursor()
    consulta = """
        SELECT fecha, documento, remito, material_applog, cantidad, origen, destino, error, posicion
        FROM TR_OUT 
        WHERE procesada = 0 OR procesada IS NULL
    """
    cursor.execute(consulta)
    filas = cursor.fetchall()
    columnas = [column[0] for column in cursor.description]
    conexion.close()

    # Crear una lista de diccionarios y convertir el error en un mensaje legible
    datos = []
    for fila in filas:
        registro = {columnas[i]: fila[i] for i in range(len(columnas))}
        registro['error'] = convertir_error_legible(registro['error'])
        datos.append(registro)
    return columnas, datos


def obtener_datos_tr_in():
    conexion = conectar_db()
    cursor = conexion.cursor()
    consulta = """
        SELECT fecha, documento, material_applog, cantidad, destino, error
        FROM TR_IN 
        WHERE procesada = 0 OR procesada IS NULL
    """
    cursor.execute(consulta)
    filas = cursor.fetchall()
    columnas = [column[0] for column in cursor.description]
    conexion.close()

    # Crear una lista de diccionarios y convertir el error en un mensaje legible
    datos = []
    for fila in filas:
        registro = {columnas[i]: fila[i] for i in range(len(columnas))}
        registro['error'] = convertir_error_legible(registro['error'])
        datos.append(registro)
    return columnas, datos


def obtener_todas_tr_out_procesadas():
    conexion = conectar_db()
    cursor = conexion.cursor()
    consulta = """
        SELECT fecha_procesada, fecha, documento, remito, material_applog, cantidad, origen, destino, error, posicion, usuario_procesada
        FROM TR_OUT 
        WHERE procesada = 1
    """
    cursor.execute(consulta)
    filas = cursor.fetchall()
    columnas = [column[0] for column in cursor.description]
    conexion.close()

    datos = []
    for fila in filas:
        registro = {columnas[i]: fila[i] for i in range(len(columnas))}
        registro['error'] = convertir_error_legible(registro['error'])
        registro['fecha'] = registro['fecha'].strftime('%d/%m/%Y %H:%M:%S')
        registro['fecha_procesada'] = registro['fecha_procesada'].strftime('%d/%m/%Y %H:%M:%S')
        datos.append(registro)
    return columnas, datos


def obtener_todas_tr_in_procesadas():
    conexion = conectar_db()
    cursor = conexion.cursor()
    consulta = """
        SELECT fecha_procesada, fecha, documento, material_applog, cantidad, destino, error, usuario_procesada
        FROM TR_IN 
        WHERE procesada = 1
    """
    cursor.execute(consulta)
    filas = cursor.fetchall()
    columnas = [column[0] for column in cursor.description]
    conexion.close()

    datos = []
    for fila in filas:
        registro = {columnas[i]: fila[i] for i in range(len(columnas))}
        registro['error'] = convertir_error_legible(registro['error'])
        registro['fecha'] = registro['fecha'].strftime('%d/%m/%Y %H:%M:%S')
        registro['fecha_procesada'] = registro['fecha_procesada'].strftime('%d/%m/%Y %H:%M:%S')
        datos.append(registro)
    return columnas, datos
