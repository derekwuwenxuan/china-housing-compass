import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_brand_exposes_consistent_skill_cli_and_python_interfaces(self):
        """A partial rename would publish installation instructions that cannot run."""

        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "src" / "china_housing_compass").is_dir())
        self.assertTrue((ROOT / "skills" / "china-housing-compass" / "SKILL.md").is_file())
        self.assertIn('name = "china-housing-compass"', pyproject)
        self.assertIn(
            'china-housing-compass = "china_housing_compass.cli:main"',
            pyproject,
        )
        self.assertIn("# China Housing Compass", readme)
        self.assertIn("$china-housing-compass", readme)
        self.assertIn("vibe coding", readme.lower())
        self.assertIn("photographer and operations practitioner", readme)
        self.assertIn("摄影师兼运营从业者", readme)

    def test_public_example_is_explicitly_synthetic(self):
        """A real or anonymous field case must not be published as a reusable fixture."""

        example_root = ROOT / "examples" / "synthetic-river-garden"
        snapshot_path = example_root / "evidence.json"
        self.assertTrue(snapshot_path.is_file())

        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertIs(snapshot.get("synthetic"), True)
        self.assertIn("合成示例", snapshot["property"]["project_name"])
        for source in snapshot["sources"]:
            self.assertIs(source.get("metadata", {}).get("synthetic"), True)
            self.assertEqual("example.test", urlparse(source["url"]).hostname)

        public_example_dirs = sorted(
            path.name for path in (ROOT / "examples").iterdir() if path.is_dir()
        )
        self.assertEqual(["synthetic-river-garden"], public_example_dirs)

    def test_public_tree_has_no_local_paths_or_private_runtime_state(self):
        """Fresh publication must not expose a workstation path or local research state."""

        self.assertFalse((ROOT / "housing-research").exists())
        self.assertFalse((ROOT / "docs" / "superpowers").exists())

        local_path = re.compile(r"/(?:Users|home)/[^/\s]+/")
        email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
        for path in ROOT.rglob("*"):
            if not path.is_file() or path == Path(__file__):
                continue
            if any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            self.assertIsNone(local_path.search(text), path)
            self.assertIsNone(email.search(text), path)

if __name__ == "__main__":
    unittest.main()
