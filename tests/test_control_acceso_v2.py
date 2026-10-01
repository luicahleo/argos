import os
import unittest

from ARGOS import app


class ControlAccesoAuthTests(unittest.TestCase):
    def setUp(self):
        os.environ["CONTROL_ACCESO_API_KEY"] = "test-key"
        self.client = app.test_client()

    def test_capacidades_sin_auth_devuelve_401(self):
        response = self.client.get("/api/v2/control-acceso/capacidades")
        self.assertEqual(response.status_code, 401)

    def test_capacidades_con_auth_invalida_devuelve_401(self):
        response = self.client.get(
            "/api/v2/control-acceso/capacidades",
            headers={"Authorization": "Bearer wrong"},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
