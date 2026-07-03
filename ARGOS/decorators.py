"""
ARGOS - Shared Flask route decorator

Encapsula el esqueleto repetido en las rutas de views.py: logging de request/response, validacion
de campos requeridos en el body JSON (-> 400) y captura generica de excepciones (-> 500).
"""

import time
from functools import wraps
from flask import request, jsonify
from ARGOS.logger import log_request, log_response, log_error


def api_route(required_fields=None, error_extra=None):
    """
    Decorador para rutas Flask que reciben un body JSON.

    El handler decorado recibe `(data, start_time)` como primeros dos argumentos — `data` es el
    JSON ya parseado y validado (garantizado no-None y con los `required_fields` presentes) y
    `start_time` permite calcular la duracion en el punto de exito de cada handler, que sigue
    siendo especifico de cada uno (el mensaje/payload de exito no se generaliza aqui).

    required_fields: claves top-level que deben existir en el body para no responder 400.
    error_extra: dict opcional fusionado en el body de error 400/500 (ej. {"identified": False})
    para preservar el contrato de respuesta de cada endpoint sin duplicar el try/except.
    """
    required_fields = required_fields or []
    error_extra = error_extra or {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            endpoint = request.path
            start_time = time.time()
            data = request.get_json(silent=True)

            log_request(endpoint, data)

            missing = [f for f in required_fields if not data or f not in data]
            if missing:
                error = f"Missing '{missing[0]}' field" if len(missing) == 1 \
                    else f"Missing field(s): {', '.join(missing)}"
                log_response(endpoint, False, error)
                return jsonify({"success": False, "error": error, **error_extra}), 400

            try:
                return func(data, start_time, *args, **kwargs)
            except Exception as e:
                log_error(endpoint, e)
                return jsonify({"success": False, "error": str(e), **error_extra}), 500

        return wrapper

    return decorator
