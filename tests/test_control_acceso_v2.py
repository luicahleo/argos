import base64
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from ARGOS import app


def synthetic_image_payload():
    """Return a tiny synthetic JPEG; DeepFace is mocked in endpoint tests."""
    image = Image.new("RGB", (1, 1), color=(128, 128, 128))
    content = BytesIO()
    image.save(content, format="JPEG")
    return base64.b64encode(content.getvalue()).decode("ascii")


def extraction_payload(**overrides):
    payload = {
        "imagen": synthetic_image_payload(),
        "formato": "jpeg",
        "tenant_id": "00000000-0000-0000-0000-000000000000",
    }
    payload.update(overrides)
    return payload


class ControlAccesoAuthTests(unittest.TestCase):
    def setUp(self):
        os.environ["CONTROL_ACCESO_API_KEY"] = "test-key"
        self.client = app.test_client()

    def post_extraction(self, payload):
        return self.client.post(
            "/api/v2/control-acceso/extracciones",
            json=payload,
            headers={"Authorization": "Bearer test-key"},
        )

    @patch("ARGOS.views.DeepFace.represent")
    def test_extraccion_devuelve_vector(self, represent):
        represent.return_value = [{"embedding": [0.25, -0.5]}]

        response = self.post_extraction(extraction_payload())

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["exitoso"])
        self.assertEqual(data["vector"], [0.25, -0.5])
        self.assertEqual(data["modelo_formato"], "arcface-cosine-512")
        self.assertEqual(data["version_modelo"], 1)
        self.assertFalse(data["pad_aprobado"])
        represent.assert_called_once()

    def test_extraccion_requiere_imagen_formato_y_tenant(self):
        for payload in (
            {"formato": "jpeg", "tenant_id": "tenant"},
            {"imagen": synthetic_image_payload(), "tenant_id": "tenant"},
            {"imagen": synthetic_image_payload(), "formato": "jpeg"},
        ):
            with self.subTest(payload=tuple(payload)):
                response = self.post_extraction(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["codigo"], "campos_faltantes")

    @patch("ARGOS.views.DeepFace.represent")
    def test_extraccion_rechaza_formato_no_admitido(self, represent):
        response = self.post_extraction(extraction_payload(formato="gif"))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["codigo"], "formato_invalido")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_extraccion_sin_rostro_devuelve_422_generico(self, represent):
        represent.side_effect = ValueError("Face could not be detected")

        response = self.post_extraction(extraction_payload())

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["codigo"], "sin_rostro")
        self.assertNotIn("error", response.get_json())

    @patch("ARGOS.views.DeepFace.represent")
    def test_extraccion_fallida_devuelve_error_generico_sin_detalles(self, represent):
        represent.side_effect = RuntimeError("private diagnostic")

        response = self.post_extraction(extraction_payload())

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["codigo"], "extraccion_fallida")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_capacidades_sin_auth_devuelve_401(self):
        response = self.client.get("/api/v2/control-acceso/capacidades")
        self.assertEqual(response.status_code, 401)

    def test_capacidades_con_auth_invalida_devuelve_401(self):
        response = self.client.get(
            "/api/v2/control-acceso/capacidades",
            headers={"Authorization": "Bearer wrong"},
        )
        self.assertEqual(response.status_code, 401)

    def test_capacidades_expone_campos_del_contrato_v2(self):
        response = self.client.get(
            "/api/v2/control-acceso/capacidades",
            headers={"Authorization": "Bearer test-key"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["modelo"], "ArcFace")
        self.assertEqual(data["detector_backend"], "opencv")
        self.assertEqual(data["embedding_size"], 512)
        self.assertEqual(data["distance_metric"], "cosine")
        self.assertEqual(data["threshold"], 0.68)
        self.assertIs(data["pad_disponible"], False)
        self.assertEqual(data["version_contrato"], "2.0")


if __name__ == "__main__":
    unittest.main()
