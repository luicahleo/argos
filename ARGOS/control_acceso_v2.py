import base64
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from flask import Blueprint, jsonify, request

from ARGOS import DETECTOR_BACKEND, MODEL_NAME, VERIFICATION_THRESHOLD
from ARGOS.auth_control_acceso import requiere_control_acceso_auth
from ARGOS.decorators import _face_not_detected_response
from ARGOS.views import DeepFace, calculate_cosine_distance


control_acceso_v2 = Blueprint(
    "control_acceso_v2",
    __name__,
    url_prefix="/api/v2/control-acceso",
)

MODELO_FORMATO = "arcface-cosine-512"
VERSION_MODELO = 1
MARGEN_AMBIGUEDAD = 0.05
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_CANDIDATOS = 50


class ImagenBase64Invalida(ValueError):
    pass


class ImagenDemasiadoGrande(ValueError):
    pass


class ImagenDimensionesExcedidas(ValueError):
    pass


def _validar_imagen_base64(value, formato_declarado):
    """Validate strict base64 and decoded image size before image processing."""
    encoded = value.partition(",")[2] if "," in value else value
    if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ImagenDemasiadoGrande
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ImagenBase64Invalida from None
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImagenDemasiadoGrande
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ImagenBase64Invalida from None
    with Image.open(BytesIO(image_bytes)) as image:
        if image.format not in ("JPEG", "PNG"):
            raise ImagenBase64Invalida
        formato_esperado = "JPEG" if formato_declarado.lower() in ("jpeg", "jpg") else "PNG"
        if image.format != formato_esperado:
            raise ImagenBase64Invalida
        if image.width > 1920 or image.height > 1920:
            raise ImagenDimensionesExcedidas
    return image_bytes


def _decodificar_imagen_validada(image_bytes):
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    import numpy as np

    return np.array(image)


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
        image_bytes = _validar_imagen_base64(data["imagen"], formato)
    except ImagenDemasiadoGrande:
        return jsonify({"exitoso": False, "codigo": "payload_muy_grande"}), 413
    except ImagenDimensionesExcedidas:
        return jsonify({"exitoso": False, "codigo": "imagen_muy_grande"}), 422
    except ImagenBase64Invalida:
        return jsonify({"exitoso": False, "codigo": "formato_invalido"}), 422

    try:
        image_array = _decodificar_imagen_validada(image_bytes)
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
    if len(candidatos) > MAX_CANDIDATOS:
        return jsonify({"identificado": False, "codigo": "payload_muy_grande"}), 413
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
        image_bytes = _validar_imagen_base64(data["imagen"], formato)
    except ImagenDemasiadoGrande:
        return jsonify({"identificado": False, "codigo": "payload_muy_grande"}), 413
    except ImagenDimensionesExcedidas:
        return jsonify({"identificado": False, "codigo": "imagen_muy_grande"}), 422
    except ImagenBase64Invalida:
        return jsonify({"identificado": False, "codigo": "formato_invalido"}), 422

    try:
        image_array = _decodificar_imagen_validada(image_bytes)
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
