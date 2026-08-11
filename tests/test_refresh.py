from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
from typing import Mapping, get_type_hints
import unittest

from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import import_snapshot, load_snapshot
from china_housing_compass.models import EvidenceGrade, EvidenceRecord
from china_housing_compass.providers.base import ProviderError, RefreshProvider
from china_housing_compass.providers.structured_import import StructuredImportProvider
from china_housing_compass.refresh import RefreshRequest, run_refresh


FIXTURE = Path(__file__).parent / "fixtures" / "normalized_snapshot.json"
RESEARCH_FIXTURE = Path(__file__).parent / "fixtures" / "research_layers_snapshot.json"


class RentProvider:
    def fetch(self, context):
        self.context = context
        return [
            EvidenceRecord(
                evidence_type="asking_monthly_rent",
                value=Decimal("4200"),
                unit="RMB/month",
                observed_on=date(2026, 8, 10),
                retrieved_on=date(2026, 8, 10),
                source="saved intermediary page",
                source_id="rent-provider-2026-08-10",
                grade=EvidenceGrade.C,
                metadata={"category": "rent"},
            )
        ]


class BrokenOfficialProvider:
    def fetch(self, context):
        raise ProviderError("official page structure changed")


class MismatchedSnapshotProvider:
    def __init__(self, payload):
        self.payload = payload

    def fetch_snapshot(self, context):
        return self.payload


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db = ResearchDatabase(self.root / "housing.sqlite")
        self.db.initialize()
        self.property_id = import_snapshot(self.db, load_snapshot(FIXTURE))["property_id"]

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_mixed_success_appends_rent_preserves_inventory_and_marks_failure_stale(self):
        request = RefreshRequest(
            property_id=self.property_id,
            categories=("rent", "official_project"),
            context={"city": "示例市", "project_name": "澄江雅苑（合成示例）"},
        )
        result = run_refresh(
            self.db,
            {"rent": RentProvider(), "official_project": BrokenOfficialProvider()},
            request,
        )

        self.assertEqual("partial", result.status)
        self.assertEqual(("rent",), result.succeeded)
        self.assertEqual(("official_project",), result.stale_categories)
        self.assertIn("page structure changed", result.failures["official_project"])
        self.assertEqual(1, result.added_records)
        self.assertEqual(72, self.db.latest_evidence(self.property_id)["official_unsold_units"].value)
        self.assertEqual(Decimal("4200"), self.db.latest_evidence(self.property_id)["asking_monthly_rent"].value)
        latest = self.db.latest_refresh(self.property_id)
        self.assertEqual("partial", latest["status"])
        self.assertEqual(["rent", "official_project"], latest["attempted"])

    def test_category_filter_skips_unrequested_providers(self):
        result = run_refresh(
            self.db,
            {"rent": RentProvider(), "official_project": BrokenOfficialProvider()},
            RefreshRequest(self.property_id, categories=("rent",)),
        )
        self.assertEqual("success", result.status)
        self.assertEqual(("rent",), result.attempted)
        self.assertEqual((), result.stale_categories)

    def test_refresh_annotation_accepts_snapshot_only_providers(self):
        self.assertEqual(Mapping[str, RefreshProvider], get_type_hints(run_refresh)["providers"])

    def test_all_failed_refresh_keeps_old_evidence(self):
        before = len(self.db.list_evidence(self.property_id))
        result = run_refresh(
            self.db,
            {"official_project": BrokenOfficialProvider()},
            RefreshRequest(self.property_id),
        )
        self.assertEqual("failed", result.status)
        self.assertEqual(before, len(self.db.list_evidence(self.property_id)))
        self.assertEqual(0, result.added_records)

    def test_structured_snapshot_refresh_imports_evidence_and_all_layer_rows(self):
        imported = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        payload = load_snapshot(RESEARCH_FIXTURE)
        payload["snapshot_id"] = "synthetic-research-refresh-2026-08-11"
        refresh_path = self.root / "research-refresh.json"
        refresh_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        result = run_refresh(
            self.db,
            {"research": StructuredImportProvider(refresh_path)},
            RefreshRequest(imported["property_id"], categories=("research",)),
        )

        self.assertEqual("success", result.status)
        self.assertEqual(("research",), result.succeeded)
        self.assertEqual(11, result.added_records)
        self.assertEqual(4, len(self.db.list_research_layer(imported["property_id"], "social_items")))

    def test_invalid_structured_snapshot_refresh_preserves_existing_rows(self):
        imported = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        payload = load_snapshot(RESEARCH_FIXTURE)
        payload["snapshot_id"] = "synthetic-research-invalid-refresh"
        payload["evidence"][0]["metadata"]["valuation_weight"] = 1
        refresh_path = self.root / "research-invalid.json"
        refresh_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        before = len(self.db.list_evidence(imported["property_id"]))

        result = run_refresh(
            self.db,
            {"research": StructuredImportProvider(refresh_path)},
            RefreshRequest(imported["property_id"], categories=("research",)),
        )

        self.assertEqual("failed", result.status)
        self.assertIn("valuation_weight", result.failures["research"])
        self.assertEqual(before, len(self.db.list_evidence(imported["property_id"])))

    def test_structured_snapshot_refresh_rejects_a_different_property(self):
        imported = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        payload = load_snapshot(RESEARCH_FIXTURE)
        payload["snapshot_id"] = "synthetic-research-wrong-property"
        payload["property"]["project_name"] = "另一合成研究样本"
        before = len(self.db.list_evidence(imported["property_id"]))
        property_count = len(self.db.list_properties())

        result = run_refresh(
            self.db,
            {"research": MismatchedSnapshotProvider(payload)},
            RefreshRequest(imported["property_id"], categories=("research",)),
        )

        self.assertEqual("failed", result.status)
        self.assertIn("property_id", result.failures["research"])
        self.assertEqual(before, len(self.db.list_evidence(imported["property_id"])))
        self.assertEqual(property_count, len(self.db.list_properties()))

    def test_replayed_snapshot_is_unchanged_and_does_not_advance_success(self):
        imported = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        prior_started = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)
        prior_finished = datetime(2026, 8, 10, 10, 1, tzinfo=timezone.utc)
        self.db.record_refresh(
            imported["property_id"], "success", ("research",), ("research",), {},
            prior_started, prior_finished,
        )

        result = run_refresh(
            self.db,
            {"research": StructuredImportProvider(RESEARCH_FIXTURE)},
            RefreshRequest(imported["property_id"], categories=("research",)),
        )

        self.assertEqual("unchanged", result.status)
        self.assertEqual((), result.succeeded)
        self.assertEqual(("research",), result.unchanged)
        self.assertEqual(0, result.added_records)
        self.assertEqual("unchanged", self.db.latest_refresh(imported["property_id"])["status"])
        self.assertEqual(
            prior_finished.isoformat(),
            self.db.latest_successful_refresh(imported["property_id"])["finished_at"],
        )

    def test_fresh_unchanged_and_failed_categories_form_a_partial_result(self):
        imported = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        result = run_refresh(
            self.db,
            {
                "rent": RentProvider(),
                "research": StructuredImportProvider(RESEARCH_FIXTURE),
                "official_project": BrokenOfficialProvider(),
            },
            RefreshRequest(
                imported["property_id"],
                categories=("rent", "research", "official_project"),
            ),
        )

        self.assertEqual("partial", result.status)
        self.assertEqual(("rent",), result.succeeded)
        self.assertEqual(("research",), result.unchanged)
        self.assertEqual(("official_project",), result.stale_categories)
        self.assertEqual(1, result.added_records)

    def test_failed_refresh_rebuilds_dashboard_to_publish_staleness(self):
        result = run_refresh(
            self.db,
            {"social": BrokenOfficialProvider()},
            RefreshRequest(
                self.property_id,
                categories=("social",),
                dashboard_dir=self.root / "dashboard",
            ),
        )

        self.assertEqual("failed", result.status)
        self.assertEqual(2, len(result.dashboard_outputs))
        page = next(Path(path) for path in result.dashboard_outputs if not path.endswith("index.html"))
        self.assertIn("Social refresh: stale", page.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
