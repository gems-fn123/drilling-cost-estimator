from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestAzureDeployAssets(unittest.TestCase):
    def test_required_app_service_files_exist(self) -> None:
        self.assertTrue((ROOT / "app.py").exists())
        self.assertTrue((ROOT / "requirements.txt").exists())
        self.assertTrue((ROOT / ".streamlit" / "config.toml").exists())
        self.assertTrue((ROOT / ".github" / "workflows" / "azure-streamlit-deploy.yml").exists())

    def test_streamlit_config_uses_port_8000(self) -> None:
        config_text = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("port = 8000", config_text)
        self.assertIn("headless = true", config_text)

    def test_requirements_include_streamlit(self) -> None:
        requirements_text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("streamlit", requirements_text.lower())


if __name__ == "__main__":
    unittest.main()
