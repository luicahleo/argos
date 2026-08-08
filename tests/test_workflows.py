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


if __name__ == "__main__":
    unittest.main()
