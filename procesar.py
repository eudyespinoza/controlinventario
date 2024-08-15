import requests
import app
import time
from flask import jsonify
import marcar_procesada
import log_save


def process_file_send(json_data, tabla):
    try:
        # Obtener el access token
        access_token = get_access_token()
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        api_url = app.API

        # Enviar la solicitud a la API
        response = requests.post(api_url, json=json_data, headers=headers)

        if response.status_code == 200:
            response_json = response.json()

            # Procesar elementos exitosos
            if response_json.get("procesados"):
                for item in response_json["procesados"]:
                    log_save.log_message(f"Se procesó correctamente {json_data}, respuesta: {response_json}")
                    # Marcar como procesada en la tabla correspondiente
                    if tabla == 'TR_OUT':
                        documento = json_data["updateStockItemRequest"][0]["DocumentNumber"][4:]  # Eliminar 'ZTRA'
                        remito = json_data["updateStockItemRequest"][0].get("PackingSlipId", '')
                        material_applog = json_data["updateStockItemRequest"][0]["ItemId"].strip()
                        marcar_procesada.marcar_como_procesada(tabla='TR_OUT', documento=documento, remito=remito,
                                                               material_applog=material_applog)
                    elif tabla == 'TR_IN':
                        documento = json_data["Items"][0]["DocumentNumber"][4:]  # Eliminar 'ZTRA'
                        material_applog = json_data["Items"][0]["ItemId"].strip()
                        marcar_procesada.marcar_como_procesada(tabla='TR_IN', documento=documento,
                                                               material_applog=material_applog)
                return jsonify({'success': True, 'message': 'Se realizó el despacho correctamente'})

            else:
                log_save.log_message(f"No se pudo procesar {json_data}. Response: {response.text}")
                return jsonify({'success': False, 'message': 'No se pudo procesar la transferencia.'})

        else:
            log_save.log_message(f"No se pudo procesar {json_data}. Response: {response.text}")
            return jsonify({'success': False, 'message': 'No se pudo procesar la transferencia.'})

    except Exception as e:
        log_save.log_message(f"Error en la función process_file_send: {e}")
        return jsonify({'success': False, 'message': 'Error interno en el servidor'})


def get_access_token():
    max_retries = 5
    retries = 0
    access_token = None

    post_data = {
        "grant_type": "client_credentials",
        "client_id": app.CLIENT_ID_MULESOFT_PROD,
        "client_secret": app.CLIENT_SECRET_MULESOFT_PROD,
        "resource": app.RESOURCE_MULESOFT_PROD
    }

    while retries < max_retries:
        response = requests.post(app.TOKEN_CLIENT, data=post_data)
        if response.status_code == 200:
            try:
                access_token = response.json().get('access_token')
                break
            except KeyError:
                log_save.log_message("Access token no encontrado en la respuesta")
                pass
        else:
            log_save.log_message(f"Error al obtener el access token: {response.status_code} - {response.text}")
        retries += 1
        time.sleep(5)

    if access_token is None:
        log_save.log_message(f"No se pudo obtener el access token después de {max_retries} intentos")
        raise Exception("No se pudo obtener el access token")

    return access_token
