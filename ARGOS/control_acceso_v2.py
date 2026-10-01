from flask import Blueprint, jsonify, request

from ARGOS import DETECTOR_BACKEND, MODEL_NAME, VERIFICATION_THRESHOLD
from ARGOS.auth_control_acceso import requiere_control_acceso_auth
from ARGOS.decorators import _face_not_detected_response
from ARGOS.views import DeepFace, calculate_cosine_distance, decode_base64_image


control_acceso_v2 = Blueprint(
    "control_acceso_v2",
    __name__,
    url_prefix="/api/v2/control-acceso",
)

MODELO_FORMATO = "arcface-cosine-512"
VERSION_MODELO = 1
MARGEN_AMBIGUEDAD = 0.05


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
                "modelo_formato": MODELO_FORMATO,
                "version_modelo": VERSION_MODELO,
                "pad_aprobado": False,
            }
        )
    except Exception as exc:
        face_response = _face_not_detected_response(exc, {})
        if face_response is not None:
            return jsonify({"exitoso": False, "codigo": "sin_rostro"}), 422
        return jsonify({"exitoso": False, "codigo": "extraccion_fallida"}), 500


@control_acceso_v2.route("/identificaciones", methods=["POST"])
@requiere_control_acceso_auth
def identificar():
    data = request.get_json(silent=True)
    required_fields = (
        "imagen",
        "formato",
        "tenant_id",
        "modelo_formato_esperado",
        "version_modelo_esperada",
        "candidatos",
    )
    if not isinstance(data, dict) or any(
        field not in data or data[field] in (None, "") for field in required_fields
    ):
        return jsonify({"identificado": False, "codigo": "campos_faltantes"}), 400

    formato = data["formato"]
    if not isinstance(data["imagen"], str) or not isinstance(formato, str):
        return jsonify({"identificado": False, "codigo": "formato_invalido"}), 422
    if formato.lower() not in ("jpeg", "jpg", "png"):
        return jsonify({"identificado": False, "codigo": "formato_invalido"}), 422
    if (
        data["modelo_formato_esperado"] != MODELO_FORMATO
        or data["version_modelo_esperada"] != VERSION_MODELO
    ):
        return jsonify({
            "identificado": False,
            "codigo": "modelo_incompatible",
            "modelo_formato": MODELO_FORMATO,
            "version_modelo": VERSION_MODELO,
            "pad_aprobado": False,
        }), 200

    candidatos = data["candidatos"]
    if not isinstance(candidatos, list):
        return jsonify({"identificado": False, "codigo": "formato_invalido"}), 422
    if not candidatos:
        return jsonify({
            "identificado": False,
            "codigo": "sin_candidatos",
            "modelo_formato": MODELO_FORMATO,
            "version_modelo": VERSION_MODELO,
            "pad_aprobado": False,
        }), 200
    for candidato in candidatos:
        if (
            not isinstance(candidato, dict)
            or not isinstance(candidato.get("trabajador_id"), str)
            or candidato.get("modelo_formato") != MODELO_FORMATO
        ):
            return jsonify({
                "identificado": False,
                "codigo": "modelo_incompatible",
                "modelo_formato": MODELO_FORMATO,
                "version_modelo": VERSION_MODELO,
                "pad_aprobado": False,
            }), 200

    try:
        image_array = decode_base64_image(data["imagen"])
        embeddings = DeepFace.represent(
            img_path=image_array,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )
        if not embeddings:
            return jsonify({"identificado": False, "codigo": "sin_rostro"}), 422
        probe = embeddings[0]["embedding"]
        ranked = []
        for candidato in candidatos:
            distancia = calculate_cosine_distance(probe, candidato["vector"])
            ranked.append((float(distancia), candidato["trabajador_id"]))
        ranked.sort(key=lambda item: item[0])
        best_distance, best_id = ranked[0]
        common = {
            "modelo_formato": MODELO_FORMATO,
            "version_modelo": VERSION_MODELO,
            "pad_aprobado": False,
        }
        if best_distance > VERIFICATION_THRESHOLD:
            return jsonify({"identificado": False, "codigo": "sin_coincidencia", **common})
        if len(ranked) > 1 and ranked[1][0] - best_distance <= MARGEN_AMBIGUEDAD:
            return jsonify({"identificado": False, "codigo": "ambigua", **common})
        return jsonify({"identificado": True, "trabajador_id": best_id, **common})
    except Exception as exc:
        face_response = _face_not_detected_response(exc, {})
        if face_response is not None:
            return jsonify({"identificado": False, "codigo": "sin_rostro"}), 422
        return jsonify({"identificado": False, "codigo": "extraccion_fallida"}), 500
