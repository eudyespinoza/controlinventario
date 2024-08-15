from hdbcli import dbapi
import app
from decimal import Decimal
import json


def consulta_movimientos(lista_tr):
    elementos = ", ".join(f"'{elemento}'" for elemento in lista_tr)
    nueva_lista = f"({elementos})"
    try:
        connect_dw = dbapi.connect(address=app.DW_HOST, port=app.DW_PORT, user=app.DW_USER,
                                   password=app.DW_PWD, encrypt=True, sslValidateCertificate=False)

        cursor_db = connect_dw.cursor()

        vista = "V_CONTROL_DE_INGRESOS"

        sql_command = f'''
        SELECT *
        FROM "{app.DW_SCHEMA}"."{vista}" WHERE "BWART" IN ('351', '352') AND "EBELN" IN {nueva_lista} 
        '''

        cursor_db.execute(sql_command)
        result = cursor_db.fetchall()
        nombres_columnas = [column[0] for column in cursor_db.description]
        connect_dw.close()
        lista_resultados = []
        for datos in result:
            # Crear un diccionario para almacenar los datos de este registro
            diccionario_resultado = {}

            # Iterar sobre las tuplas de datos y las columnas correspondientes
            for nombre_columna, valor in zip(nombres_columnas, datos):
                # Si el valor es de tipo Decimal, almacenar solo el monto
                if isinstance(valor, Decimal):
                    diccionario_resultado[nombre_columna] = float(valor)
                else:
                    diccionario_resultado[nombre_columna] = valor

            # Agregar el diccionario de este registro a la lista de resultados
            lista_resultados.append(diccionario_resultado)
        lista_resultados_json = json.dumps(lista_resultados, ensure_ascii=False)
        return lista_resultados_json, None
    except Exception as e:
        return None, str(e)

