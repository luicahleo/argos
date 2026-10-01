import hmac
import os
from functools import wraps

from flask import jsonify, request


def requiere_control_acceso_auth(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        api_key = os.environ.get("CONTROL_ACCESO_API_KEY", "")
        authorization = request.headers.get("Authorization", "")
        supplied_key = authorization[7:] if authorization.startswith("Bearer ") else ""

        if not api_key or not hmac.compare_digest(supplied_key, api_key):
            return jsonify({"success": False, "error": "No autenticado"}), 401

        return func(*args, **kwargs)

    return decorated
