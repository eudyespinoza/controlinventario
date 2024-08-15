import pyodbc
import app
import logging
import log_save


def conectar_db():
    try:
        conexion = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            f'SERVER={app.SQL_SERVER};'
            f'DATABASE={app.SQL_DATABASE};'
            f'UID={app.SQL_USERNAME};'
            f'PWD={app.SQL_PASSWORD}'
        )
        return conexion
    except pyodbc.Error as e:
        log_save.log_message(f"Error al conectar con la base de datos: {e}")
        raise


def marcar_como_procesada(tabla, documento, material_applog, remito=None):
    conexion = None
    cursor = None
    try:
        # Conexión a la base de datos
        conexion = conectar_db()
        cursor = conexion.cursor()

        # Construir la consulta y los parámetros según la tabla
        if tabla == 'TR_OUT':
            if remito is None:
                raise ValueError("El campo 'remito' es necesario para la tabla TR_OUT.")
            concat_out = f"ZTRA{documento}{material_applog}{remito}"
            consulta = f"""
            UPDATE [DB_ENUM].[dbo].[TR_OUT]
            SET [procesada] = 1
            WHERE concat = '{concat_out}'
            """

        elif tabla == 'TR_IN':
            concat_in = f"ZTRA{documento}{material_applog}"
            consulta = f"""
            UPDATE [DB_ENUM].[dbo].[TR_IN]
            SET [procesada] = 1
            WHERE concat = '{concat_in}'
            """

        else:
            raise ValueError("Tabla no soportada. Utilice 'TR_OUT' o 'TR_IN'.")

        # Ejecutar la consulta
        cursor.execute(consulta)

        conexion.commit()

        logging.info(f"Registro en tabla {tabla} marcado como procesado: "
                     f"documento={documento}, material_applog={material_applog}, remito={remito}")
        log_save.log_message(f"Registro en tabla {tabla} marcado como procesado: "
                        f"documento={documento}, material_applog={material_applog}, remito={remito}")

    except pyodbc.Error as e:
        log_save.log_message(f"Error al ejecutar la consulta SQL en la tabla {tabla}: {e}")
        raise

    except ValueError as e:
        log_save.log_message(f"Error en los parámetros: {e}")
        raise

    finally:
        # Cerrar el cursor y la conexión de manera segura
        if cursor:
            try:
                cursor.close()
            except pyodbc.Error as e:
                log_save.log_message(f"Error al cerrar el cursor: {e}")

        if conexion:
            try:
                conexion.close()
            except pyodbc.Error as e:
                log_save.log_message(f"Error al cerrar la conexión con la base de datos: {e}")
