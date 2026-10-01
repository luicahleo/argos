from flask import Blueprint, jsonify

from ARGOS import DETECTOR_BACKEND, MODEL_NAME, VERIFICATION_THRESHOLD
from ARGOS.auth_control_acceso import requiere_control_acceso_auth


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
