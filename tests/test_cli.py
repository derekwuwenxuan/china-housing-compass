from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest

from china_housing_compass.cli import main
from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import import_snapshot, load_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "normalized_snapshot.json"
RESEARCH_FIXTURE = Path(__file__).parent / "fixtures" / "research_layers_snapshot.json"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name) / "housing-research"

    def tearDown(self):
        self.tempdir.cleanup()

    def run_cli(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_init_creates_local_workspace_and_database(self):
        code, output, error = self.run_cli(["init", str(self.workspace)])
        self.assertEqual(0, code, error)
        self.assertIn("housing.sqlite", output)
        for name in ("inputs", "snapshots", "reports", "dashboard"):
            self.assertTrue((self.workspace / name).is_dir())
        self.assertTrue((self.workspace / "housing.sqlite").is_file())

    def test_import_dashboard_and_status_workflow(self):
        self.assertEqual(0, self.run_cli(["init", str(self.workspace)])[0])
        code, output, error = self.run_cli(
            ["import", str(self.workspace), str(FIXTURE)]
        )
        self.assertEqual(0, code, error)
        self.assertIn("Imported 3 evidence records", output)
        self.assertNotIn("research-layer", output)

        db = ResearchDatabase(self.workspace / "housing.sqlite")
        now = datetime(2026, 8, 10, tzinfo=timezone.utc)
        db.record_refresh(1, "partial", ("rent", "official_project"), ("rent",), {"official_project": "changed"}, now, now)
        db.close()

        code, output, error = self.run_cli(["status", str(self.workspace)])
        self.assertEqual(0, code, error)
        self.assertIn("Last refresh: partial", output)
        self.assertIn("Stale categories: official_project", output)

        code, output, error = self.run_cli(["dashboard", str(self.workspace)])
        self.assertEqual(0, code, error)
        self.assertTrue((self.workspace / "dashboard" / "synthetic-river-garden.html").is_file())

    def test_import_reports_research_layer_counts_for_version_two_snapshot(self):
        self.assertEqual(0, self.run_cli(["init", str(self.workspace)])[0])

        code, output, error = self.run_cli(
            ["import", str(self.workspace), str(RESEARCH_FIXTURE)]
        )

        self.assertEqual(0, code, error)
        self.assertIn("Imported 1 evidence records", output)
        self.assertIn("10 research-layer records", output)

        code, output, error = self.run_cli(
            ["import", str(self.workspace), str(RESEARCH_FIXTURE)]
        )

        self.assertEqual(0, code, error)
        self.assertIn("Imported 0 evidence records", output)
        self.assertIn("0 research-layer records", output)

    def test_refresh_and_status_expose_an_unchanged_snapshot(self):
        self.assertEqual(0, self.run_cli(["init", str(self.workspace)])[0])
        self.assertEqual(
            0,
            self.run_cli(["import", str(self.workspace), str(FIXTURE)])[0],
        )

        code, output, error = self.run_cli([
            "refresh", str(self.workspace), "1",
            "--provider", f"official_project={FIXTURE}",
        ])

        self.assertEqual(0, code, error)
        self.assertIn("Refresh status: unchanged", output)
        self.assertIn("Unchanged categories: official_project", output)

        code, output, error = self.run_cli([
            "status", str(self.workspace), "--property-id", "1",
        ])
        self.assertEqual(0, code, error)
        self.assertIn("Last refresh: unchanged", output)
        self.assertIn("Unchanged categories: official_project", output)

    def test_invalid_snapshot_unit_returns_nonzero(self):
        self.assertEqual(0, self.run_cli(["init", str(self.workspace)])[0])
        payload = load_snapshot(FIXTURE)
        payload["evidence"][0]["unit"] = "yuan"
        invalid = self.workspace / "inputs" / "invalid.json"
        invalid.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        code, output, error = self.run_cli(["import", str(self.workspace), str(invalid)])
        self.assertEqual(2, code)
        self.assertIn("unsupported unit", error)
        self.assertEqual("", output)

    def test_non_integer_schema_version_returns_validation_error(self):
        self.assertEqual(0, self.run_cli(["init", str(self.workspace)])[0])
        payload = load_snapshot(FIXTURE)
        payload["schema_version"] = []
        invalid = self.workspace / "inputs" / "invalid-version.json"
        invalid.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        code, output, error = self.run_cli(["import", str(self.workspace), str(invalid)])

        self.assertEqual(2, code)
        self.assertIn("schema_version", error)
        self.assertEqual("", output)

    def test_help_lists_all_six_commands(self):
        code, output, error = self.run_cli(["--help"])
        self.assertEqual(0, code, error)
        for command in ("init", "import", "valuate", "dashboard", "refresh", "status"):
            self.assertIn(command, output)


if __name__ == "__main__":
    unittest.main()
