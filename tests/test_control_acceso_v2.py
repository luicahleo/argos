import base64
import logging
import os
import unittest
from io import BytesIO, StringIO
from unittest.mock import patch

from PIL import Image

from ARGOS import app


def synthetic_image_payload(size=(1, 1), image_format="JPEG"):
    """Return a tiny synthetic JPEG; DeepFace is mocked in endpoint tests."""
    image = Image.new("RGB", size, color=(128, 128, 128))
    content = BytesIO()
    image.save(content, format=image_format)
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

    def post_identification(self, payload):
        return self.client.post(
            "/api/v2/control-acceso/identificaciones",
            json=payload,
            headers={"Authorization": "Bearer test-key"},
        )

    def identification_payload(self, probe_vector, candidate_vector):
        return {
            "imagen": synthetic_image_payload(),
            "formato": "jpeg",
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "modelo_formato_esperado": "arcface-cosine-512",
            "version_modelo_esperada": 1,
            "candidatos": [
                {
                    "trabajador_id": "11111111-1111-1111-1111-111111111111",
                    "vector": candidate_vector,
                    "modelo_formato": "arcface-cosine-512",
                    "version_enrolamiento": 1,
                }
            ],
        }

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_coincide_con_candidato(self, represent):
        vector = [1.0] + [0.0] * 511
        represent.return_value = [{"embedding": vector}]

        response = self.post_identification(self.identification_payload(vector, vector))

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["identificado"])
        self.assertEqual(data["trabajador_id"], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(data["modelo_formato"], "arcface-cosine-512")
        self.assertEqual(data["version_modelo"], 1)
        self.assertFalse(data["pad_aprobado"])
        self.assertNotIn("distancia", data)
        self.assertNotIn("candidatos", data)

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_sin_coincidencia_devuelve_codigo(self, represent):
        probe = [1.0] + [0.0] * 511
        candidate = [-1.0] + [0.0] * 511
        represent.return_value = [{"embedding": probe}]

        response = self.post_identification(self.identification_payload(probe, candidate))

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["identificado"])
        self.assertEqual(data["codigo"], "sin_coincidencia")
        self.assertNotIn("trabajador_id", data)
        self.assertNotIn("distancia", data)
        self.assertNotIn("candidatos", data)

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_acepta_version_de_enrolamiento_independiente(self, represent):
        vector = [1.0] + [0.0] * 511
        represent.return_value = [{"embedding": vector}]
        payload = self.identification_payload(vector, vector)
        payload["candidatos"][0]["version_enrolamiento"] = 3

        response = self.post_identification(payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["identificado"])

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

    def test_identificacion_requiere_imagen(self):
        vector = [1.0] + [0.0] * 511
        payload = self.identification_payload(vector, vector)
        del payload["imagen"]

        response = self.post_identification(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["codigo"], "campos_faltantes")

    @patch("ARGOS.views.DeepFace.represent")
    def test_endpoints_rechazan_base64_malformado_con_error_generico(self, represent):
        vector = [1.0] + [0.0] * 511
        invalid_image = base64.b64encode(b"not an image").decode("ascii")
        cases = (
            (self.post_extraction, extraction_payload(imagen="not base64!")),
            (self.post_identification, self.identification_payload(vector, vector) | {"imagen": "not base64!"}),
            (self.post_extraction, extraction_payload(imagen=invalid_image)),
            (self.post_identification, self.identification_payload(vector, vector) | {"imagen": invalid_image}),
        )
        for post, payload in cases:
            with self.subTest(endpoint=post.__name__):
                response = post(payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.get_json()["codigo"], "formato_invalido")
                self.assertNotIn("error", response.get_json())
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_endpoints_rechazan_imagenes_mayores_a_2_mib(self, represent):
        encoded = base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode("ascii")
        vector = [1.0] + [0.0] * 511
        cases = (
            (self.post_extraction, extraction_payload(imagen=encoded)),
            (self.post_identification, self.identification_payload(vector, vector) | {"imagen": encoded}),
        )
        for post, payload in cases:
            with self.subTest(endpoint=post.__name__):
                response = post(payload)
                self.assertEqual(response.status_code, 413)
                self.assertEqual(response.get_json()["codigo"], "payload_muy_grande")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_endpoints_rechazan_dimensiones_mayores_a_1920(self, represent):
        image = synthetic_image_payload(size=(1921, 1))
        vector = [1.0] + [0.0] * 511
        cases = (
            (self.post_extraction, extraction_payload(imagen=image)),
            (self.post_identification, self.identification_payload(vector, vector) | {"imagen": image}),
        )
        for post, payload in cases:
            with self.subTest(endpoint=post.__name__):
                response = post(payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.get_json()["codigo"], "imagen_muy_grande")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_endpoints_rechazan_formato_declarado_distinto_al_real(self, represent):
        png = synthetic_image_payload(image_format="PNG")
        vector = [1.0] + [0.0] * 511
        cases = (
            (self.post_extraction, extraction_payload(imagen=png, formato="jpeg")),
            (self.post_identification, self.identification_payload(vector, vector) | {"imagen": png}),
        )
        for post, payload in cases:
            with self.subTest(endpoint=post.__name__):
                response = post(payload)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.get_json()["codigo"], "formato_invalido")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_rechaza_modelo_de_candidato_incompatible(self, represent):
        vector = [1.0] + [0.0] * 511
        payload = self.identification_payload(vector, vector)
        payload["candidatos"][0]["modelo_formato"] = "otro-modelo"

        response = self.post_identification(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["codigo"], "modelo_incompatible")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_con_distancias_iguales_es_ambigua(self, represent):
        vector = [1.0] + [0.0] * 511
        payload = self.identification_payload(vector, vector)
        payload["candidatos"].append({
            "trabajador_id": "22222222-2222-2222-2222-222222222222",
            "vector": vector,
            "modelo_formato": "arcface-cosine-512",
            "version_enrolamiento": 7,
        })
        represent.return_value = [{"embedding": vector}]

        response = self.post_identification(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["codigo"], "ambigua")
        self.assertNotIn("trabajador_id", response.get_json())

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_limita_candidatos_a_cincuenta(self, represent):
        vector = [1.0] + [0.0] * 511
        payload = self.identification_payload(vector, vector)
        payload["candidatos"] *= 51

        response = self.post_identification(payload)

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["codigo"], "payload_muy_grande")
        represent.assert_not_called()

    @patch("ARGOS.views.DeepFace.represent")
    def test_identificacion_no_registra_vectores_ni_identificadores(self, represent):
        vector = [1.0] + [0.0] * 511
        worker_id = "11111111-1111-1111-1111-111111111111"
        payload = self.identification_payload(vector, vector)
        tenant_id = payload["tenant_id"]
        image = payload["imagen"]
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        represent.return_value = [{"embedding": vector}]
        try:
            response = self.post_identification(payload)
        finally:
            root_logger.removeHandler(handler)
            handler.close()

        self.assertEqual(response.status_code, 200)
        logs = log_output.getvalue()
        self.assertNotIn(str(vector), logs)
        self.assertNotIn(worker_id, logs)
        self.assertNotIn(tenant_id, logs)
        self.assertNotIn(image, logs)
        self.assertNotIn(str(payload), logs)

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
