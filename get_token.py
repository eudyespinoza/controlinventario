# Dentro de este módulo se consiguen las siguientes funciones:
# Consulta token graph
# Consulta token D365 QA
# Consulta token D365 Producción
# Consulta token Applog


import app
import log_save
import requests


def get_access_token_graph():
    token_url = app.TOKEN_CLIENT
    token_params = {
        "grant_type": "client_credentials",
        "client_id": app.CLIENT_ID_GRAPH,
        "client_secret": app.CLIENT_SECRET_GRAPH,
        "resource": "https://graph.microsoft.com"
    }

    try:
        response = requests.post(token_url, data=token_params, timeout=app.timeout_seconds)
        response.raise_for_status()  # Verificar si hay errores en la respuesta

        token_data_graph = response.json()
        access_token_graph = token_data_graph['access_token']
        log_save.log_message(f"Consulta token a Graph OK")
        return access_token_graph

    except requests.exceptions.RequestException as e:
        log_save.log_message(f"Consulta token a Graph FALLO. {e}")
        print("Error al obtener el token de acceso:", e)
        return None


def get_access_token_applog():
    url = app.TOKEN_CLIENT_APPLOG
    payload = {
        'username': app.USER_APPLOG,
        'password': app.PASS_APPLOG
    }

    response = requests.post(url, data=payload, timeout=app.timeout_seconds)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('result', {}).get('access_token', None)
        log_save.log_message(f"Consulta token Applog OK")
        return access_token
    else:
        print("Error al consultar el token:", response.text)
        log_save.log_message(f"Consulta token Applog FALLÓ")
        return None


def get_access_token_d365():
    token_url = app.TOKEN_CLIENT
    token_params = {
        "grant_type": "client_credentials",
        "client_id": app.CLIENT_ID_PROD,
        "client_secret": app.CLIENT_SECRET_PROD,
        "resource": app.CLIENTE_PROD
    }

    try:
        response = requests.post(token_url, data=token_params, timeout=app.timeout_seconds)
        response.raise_for_status()  # Verificar si hay errores en la respuesta

        token_data = response.json()
        access_token = token_data['access_token']
        log_save.log_message(f"Consulta token a D365 OK")
        return access_token

    except requests.exceptions.RequestException as e:
        log_save.log_message(f"Consulta token a D365 FALLO. {e}")
        print("Error al obtener el token de acceso:", e)
        return None


def get_access_token_d365_qa():
    token_url = app.TOKEN_CLIENT
    token_params = {
        "grant_type": "client_credentials",
        "client_id": app.CLIENT_ID_QA,
        "client_secret": app.CLIENT_SECRET_QA,
        "resource": app.CLIENTE_QA
    }

    try:
        response = requests.post(token_url, data=token_params, timeout=app.timeout_seconds)
        response.raise_for_status()  # Verificar si hay errores en la respuesta

        token_data = response.json()
        access_token = token_data['access_token']
        log_save.log_message(f"Consulta token a D365 OK")
        return access_token

    except requests.exceptions.RequestException as e:
        log_save.log_message(f"Consulta token a D365 FALLO. {e}")
        return None
