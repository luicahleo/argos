"""
ARGOS - Shared Flask route decorator

Encapsula el esqueleto repetido en las rutas de views.py: logging de request/response, validacion
de campos requeridos en el body JSON (-> 400), mapeo de fallos de deteccion facial de DeepFace
a 422 estructurado (code="face-not-detected") y captura generica de excepciones (-> 500).
"""

import re
import time
from functools import wraps
from flask import request, jsonify
from ARGOS.logger import log_request, log_response, log_error

try:
    # Disponible en deepface moderno; si no existe, basta el fallback por mensaje.
    from deepface.modules.exceptions import FaceNotDetected
except ImportError:  # pragma: no cover
    FaceNotDetected = None

_IMG_PATH_RE = re.compile(r"Exception while processing (img[12])_path")


def _face_not_detected_response(exc: Exception, error_extra: dict):
    """
    422 estructurado si `exc` es un fallo de deteccion de rostro de DeepFace; None si no.

    - DeepFace.verify envuelve la FaceNotDetected en un ValueError
      "Exception while processing imgN_path" -> se indica que imagen fallo.
    - DeepFace.represent la lanza directa (enforce_detection=True).
    """
    msg = str(exc)
    m = _IMG_PATH_RE.search(msg)
    if m:
        image = m.group(1)
        return jsonify({
            "success": False,
            "code": "face-not-detected",
            "image": image,
            "error": f"No se detectó rostro en la imagen {image[-1]}",
            **error_extra
        }), 422
    is_face_not_detected = (FaceNotDetected is not None and isinstance(exc, FaceNotDetected)) \
        or "Face could not be detected" in msg
    if is_face_not_detected:
        return jsonify({
            "success": False,
            "code": "face-not-detected",
            "error": "No se detectó rostro en la imagen",
            **error_extra
        }), 422
    return None


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
                resp = _face_not_detected_response(e, error_extra)
                if resp is not None:
                    log_response(endpoint, False, f"422 face-not-detected: {e}")
                    return resp
                log_error(endpoint, e)
                return jsonify({"success": False, "error": str(e), **error_extra}), 500

        return wrapper

    return decorator
