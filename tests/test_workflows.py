from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_ci_valida_develop_y_master(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("branches: [master, develop]", workflow)

    def test_deploy_es_manual_y_exclusivo_de_master(self):
        workflow = (ROOT / ".github/workflows/deploy-argos.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertNotIn("branches: [ main, master ]", workflow)
        self.assertIn("github.ref == 'refs/heads/master'", workflow)
        self.assertIn("inputs.confirmar == 'PRODUCCION'", workflow)
        self.assertIn("Verificar CI verde del commit", workflow)

    def test_health_es_independiente_de_icarus_api(self):
        source = (ROOT / "ARGOS/views.py").read_text(encoding="utf-8")
        health = source.split('@app.route("/health", methods=["GET"])', 1)[1].split(
            "@app.route(", 1
        )[0]
        self.assertNotIn("api_client.health_check", health)
        self.assertNotIn('"icarus_api"', health)

    def test_deploy_usa_candidato_y_preserva_la_imagen_anterior(self):
        script = (ROOT / "deploy-production.sh").read_text(encoding="utf-8")
        self.assertIn("argos:previous", script)
        self.assertIn('CANDIDATE_IMAGE="argos:control-acceso-validacion"', script)
        self.assertIn("argos-v2-candidate", script)
        self.assertIn("--memory 2g", script)
        self.assertIn("--log-opt max-size=10m", script)
        self.assertIn("--log-opt max-file=5", script)
        self.assertIn('--env-file "$ENV_FILE"', script)
        self.assertIn("/api/v2/control-acceso/capacidades", script)
        self.assertIn("/api/v2/control-acceso/extracciones", script)
        self.assertIn("/api/v2/control-acceso/identificaciones", script)
        self.assertIn("candidate_status POST /api/verify 400", script)
        self.assertIn('docker rename "$CANDIDATE_CONTAINER" argos', script)
        self.assertIn("trap", script)
        self.assertGreaterEqual(script.count("rollback_on_error 1"), 2)
        self.assertIn("argos:latest", script)
        self.assertIn("--exclude='.env.production'", script)
        self.assertLess(
            script.index("candidate_status GET /api/v2/control-acceso/capacidades"),
            script.index("docker stop argos"),
        )


if __name__ == "__main__":
    unittest.main()
