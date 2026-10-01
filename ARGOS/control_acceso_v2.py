from flask import Blueprint, jsonify, request

from ARGOS import DETECTOR_BACKEND, MODEL_NAME, VERIFICATION_THRESHOLD
from ARGOS.auth_control_acceso import requiere_control_acceso_auth
from ARGOS.decorators import _face_not_detected_response
from ARGOS.views import DeepFace, decode_base64_image


control_acceso_v2 = Blueprint(
    "control_acceso_v2",
    __name__,
    url_prefix="/api/v2/control-acceso",
)


@control_acceso_v2.route("/capacidades", methods=["GET"])
@requiere_control_acceso_auth
def capacidades():
    return jsonify(
        {
            "version_contrato": "2.0",
            "modelo": MODEL_NAME,
            "detector_backend": DETECTOR_BACKEND,
            "embedding_size": 512,
            "distance_metric": "cosine",
            "threshold": VERIFICATION_THRESHOLD,
            "pad_disponible": False,
        }
    )


@control_acceso_v2.route("/extracciones", methods=["POST"])
@requiere_control_acceso_auth
def extraer():
    data = request.get_json(silent=True)
    required_fields = ("imagen", "formato", "tenant_id")
    if not isinstance(data, dict) or any(
        field not in data or data[field] in (None, "") for field in required_fields
    ):
        return jsonify({"exitoso": False, "codigo": "campos_faltantes"}), 400

    formato = data["formato"]
    if not isinstance(data["imagen"], str) or not isinstance(formato, str):
        return jsonify({"exitoso": False, "codigo": "formato_invalido"}), 422
    if formato.lower() not in ("jpeg", "jpg", "png"):
        return jsonify({"exitoso": False, "codigo": "formato_invalido"}), 422

    try:
        image_array = decode_base64_image(data["imagen"])
        embeddings = DeepFace.represent(
            img_path=image_array,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )
        if not embeddings:
            return jsonify({"exitoso": False, "codigo": "sin_rostro"}), 422
        return jsonify(
            {
                "exitoso": True,
                "vector": embeddings[0]["embedding"],
                "modelo_formato": "arcface-cosine-512",
                "version_modelo": 1,
                "pad_aprobado": False,
            }
        )
    except Exception as exc:
        face_response = _face_not_detected_response(exc, {})
        if face_response is not None:
            return jsonify({"exitoso": False, "codigo": "sin_rostro"}), 422
        return jsonify({"exitoso": False, "codigo": "extraccion_fallida"}), 500
