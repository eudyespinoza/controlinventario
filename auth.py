from flask import session
import app
import log_save
import get_token
import ldap3
from ldap3.core.exceptions import LDAPException, LDAPBindError
import requests


def ldap_authenticate(username, password):
    server = ldap3.Server(app.LDAP_SERVER)
    try:
        print("Verificando credenciales")
        ldap3.Connection(server, user=f"{username}@{app.LDAP_DOMAIN}", password=password, auto_bind=True)
        return True, None
    except LDAPBindError as error:
        # Error específico de credenciales inválidas
        log_save.log_message(f"Error de autenticación LDAP: Credenciales inválidas para {username}")
        return False, str(error)
    except LDAPException as error:
        # Otros errores LDAP generales
        if "WinError 10060" in str(error):
            error = "No se pudo verificar las credenciales. Parece que no estas conectado a la VPN"
            log_save.log_message(f"Falló la conexión!. {error}")
            return False, str(error)
        else:
            log_save.log_message(f"Error de autenticación LDAP: {str(error)}")
            return False, str(error)
    except Exception as error:
        log_save.log_message(f"Error de autenticación: {str(error)}")
        return False, str(error)


def get_authorization(username):
    token = get_token.get_access_token_graph()
    url = app.CLIENT_GRAPH
    headers = {
        "Authorization": "Bearer " + token
    }
    params = {
        "$select": "mail",
    }

    # Realizar la solicitud GET
    log_save.log_message(f"Validando permisos del usuario {username} en graph")
    response = requests.get(url, headers=headers, params=params, timeout=app.timeout_seconds)

    # Verificar el estado de la respuesta
    if response.status_code == 200:
        # Convertir la respuesta JSON en un diccionario
        data = response.json()
        filtered_users = list(filter(lambda user: username in user["mail"], data["value"]))
        if not filtered_users:
            error = f"El usuario {username} NO tiene permisos para usar esta aplicacion"
            log_save.log_message(str(error))
            return False, error
        else:
            session['user'] = username
            return True, None
    error = "El servidor de Microsoft Graph no responde"
    log_save.log_message(str(error))
    return False, error
