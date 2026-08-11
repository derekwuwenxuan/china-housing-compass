from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import evidence_records, import_snapshot, load_snapshot, validate_snapshot
from china_housing_compass.models import PropertyRef, ValidationError
from china_housing_compass.providers.base import Provider, SnapshotProvider
from china_housing_compass.providers.structured_import import StructuredImportProvider


FIXTURE = Path(__file__).parent / "fixtures" / "normalized_snapshot.json"
RESEARCH_FIXTURE = Path(__file__).parent / "fixtures" / "research_layers_snapshot.json"


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = ResearchDatabase(Path(self.tempdir.name) / "research.sqlite")
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_load_and_import_keeps_price_types_and_grades_separate(self):
        payload = load_snapshot(FIXTURE)
        result = import_snapshot(self.db, payload)
        records = self.db.list_evidence(result["property_id"])

        self.assertEqual(3, result["imported_evidence"])
        self.assertEqual(
            ["official_unsold_units", "developer_quoted_total_price", "model_home_available"],
            [record.evidence_type for record in records],
        )
        quote = records[1]
        self.assertEqual(Decimal("1760000"), quote.value)
        self.assertEqual("C", quote.grade.value)
        self.assertEqual("synthetic-developer-quote", quote.source_id)

    def test_missing_source_reference_fails_before_database_insertion(self):
        payload = load_snapshot(FIXTURE)
        payload = deepcopy(payload)
        payload["evidence"][0]["source_id"] = "missing-source"

        with self.assertRaises(ValidationError):
            import_snapshot(self.db, payload)
        self.assertEqual([], self.db.list_properties())

    def test_reimport_same_snapshot_is_idempotent_and_later_snapshot_appends(self):
        payload = load_snapshot(FIXTURE)
        first = import_snapshot(self.db, payload)
        second = import_snapshot(self.db, payload)
        self.assertEqual(0, second["imported_evidence"])

        later = deepcopy(payload)
        later["snapshot_id"] = "synthetic-property-2026-01-16"
        later["evidence"] = [deepcopy(later["evidence"][1])]
        later["evidence"][0]["observed_on"] = "2026-01-16"
        later["evidence"][0]["value"] = "1720000"
        later_result = import_snapshot(self.db, later)

        quotes = self.db.list_evidence(first["property_id"], "developer_quoted_total_price")
        self.assertEqual(1, later_result["imported_evidence"])
        self.assertEqual([Decimal("1760000"), Decimal("1720000")], [item.value for item in quotes])

    def test_research_source_provenance_is_snapshot_linked_and_idempotent(self):
        """A later registry update must not rewrite an older layer row's source."""

        first_payload = load_snapshot(RESEARCH_FIXTURE)
        first = import_snapshot(self.db, first_payload)
        later = deepcopy(first_payload)
        later["snapshot_id"] = "synthetic-research-2026-08-12"
        later["sources"][2].update(
            url="https://example.test/history/revised",
            title="Revised history source",
            grade="C",
            retrieved_on="2026-08-12",
        )
        later["research_layers"] = {
            "parcel_history_findings": [{
                "finding_key": "synthetic-history-revised",
                "source_id": "synthetic-history",
                "geography_scope": "within_500m",
                "historical_use": "warehouse",
                "finding_state": "lead_only",
                "observed_on": "2026-08-12",
                "retrieved_on": "2026-08-12",
                "grade": "C",
            }],
        }

        second = import_snapshot(self.db, later)
        replay = import_snapshot(self.db, later)
        rows = self.db.list_research_layer(first["property_id"], "parcel_history_findings")

        self.assertFalse(first["unchanged"])
        self.assertFalse(second["unchanged"])
        self.assertTrue(replay["unchanged"])
        self.assertEqual("Synthetic history research", rows[0]["source_title"])
        self.assertEqual("https://example.test/history", rows[0]["source_url"])
        self.assertEqual("B", rows[0]["source_grade"])
        self.assertEqual("2026-08-11", rows[0]["source_retrieved_on"])
        self.assertEqual("Revised history source", rows[-1]["source_title"])
        self.assertEqual("C", rows[-1]["source_grade"])
        self.assertEqual(
            2,
            self.db.connection.execute(
                "SELECT COUNT(*) FROM source_observations WHERE property_id=? AND source_key=?",
                (first["property_id"], "synthetic-history"),
            ).fetchone()[0],
        )

    def test_version_two_imports_generic_evidence_and_research_layers(self):
        result = import_snapshot(self.db, load_snapshot(RESEARCH_FIXTURE))
        pid = result["property_id"]

        self.assertEqual(2, result["schema_version"])
        self.assertEqual(1, result["imported_evidence"])
        self.assertEqual(2, result["imported_layers"]["social_items"])
        self.assertEqual(
            "authorized_browser",
            self.db.list_research_layer(pid, "social_research_runs")[0]["access_mode"],
        )
        self.assertEqual(3, len(self.db.list_research_layer(pid, "social_comments")))

    def test_version_two_reimport_is_tracked_by_imported_snapshots(self):
        payload = load_snapshot(RESEARCH_FIXTURE)
        first = import_snapshot(self.db, payload)
        reimport = deepcopy(payload)
        reimport["property"]["submarket"] = "must-not-overwrite-on-noop"
        second = import_snapshot(self.db, reimport)

        self.assertEqual(0, second["imported_evidence"])
        self.assertEqual({}, second["imported_layers"])
        self.assertEqual(
            1,
            self.db.connection.execute(
                "SELECT COUNT(*) FROM imported_snapshots WHERE property_id=? AND snapshot_id=?",
                (first["property_id"], payload["snapshot_id"]),
            ).fetchone()[0],
        )
        self.assertEqual(2, len(self.db.list_research_layer(first["property_id"], "social_items")))
        self.assertEqual("合成子市场", self.db.get_property(first["property_id"])["submarket"])

    def test_version_two_unknown_layer_source_rolls_back_everything(self):
        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        payload["research_layers"]["social_items"][0]["source_id"] = "unknown-source"

        with self.assertRaisesRegex(ValidationError, "source_id"):
            import_snapshot(self.db, payload)
        self.assertEqual([], self.db.list_properties())
        self.assertEqual(0, self.db.connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0])

    def test_user_forecast_cannot_affect_valuation_or_transfer(self):
        for field, value in (("valuation_weight", 1), ("transferable", True)):
            payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
            payload["evidence"][0]["metadata"][field] = value
            with self.assertRaisesRegex(ValidationError, field):
                validate_snapshot(payload)

        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        payload["evidence"][0]["metadata"]["speaker"] = "analyst"
        with self.assertRaisesRegex(ValidationError, "speaker.*user"):
            validate_snapshot(payload)

    def test_import_rejects_uninspectable_comment_parent_atomically(self):
        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        payload["research_layers"]["social_items"][0]["access_mode"] = "indexed_snippet"

        with self.assertRaisesRegex(ValidationError, "access_mode"):
            import_snapshot(self.db, payload)

        self.assertEqual([], self.db.list_properties())

    def test_import_rejects_boolean_social_sample_count_atomically(self):
        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        payload["research_layers"]["social_research_runs"][0]["requested_count"] = True

        with self.assertRaisesRegex(ValidationError, "requested_count"):
            import_snapshot(self.db, payload)

        self.assertEqual([], self.db.list_properties())

    def test_version_one_return_remains_compatible_with_empty_layer_counts(self):
        result = import_snapshot(self.db, load_snapshot(FIXTURE))
        self.assertEqual(1, result["schema_version"])
        self.assertEqual({}, result["imported_layers"])

    def test_version_one_reimport_recognizes_legacy_evidence_snapshot(self):
        payload = load_snapshot(FIXTURE)
        property_id = self.db.upsert_property(PropertyRef(**payload["property"]))
        self.db.add_evidence(
            property_id,
            evidence_records(payload)[0],
            snapshot_id=payload["snapshot_id"],
        )

        result = import_snapshot(self.db, payload)

        self.assertEqual(0, result["imported_evidence"])
        self.assertEqual(1, len(self.db.list_evidence(property_id)))
        self.assertEqual(
            1,
            self.db.connection.execute(
                "SELECT COUNT(*) FROM imported_snapshots WHERE property_id=? AND snapshot_id=?",
                (property_id, payload["snapshot_id"]),
            ).fetchone()[0],
        )

    def test_validation_rejects_unknown_units_bad_dates_and_empty_snapshot_id(self):
        payload = load_snapshot(FIXTURE)
        for field, value in (
            ("snapshot_id", ""),
            ("unit", "yuan"),
            ("observed_on", "10/08/2026"),
        ):
            broken = deepcopy(payload)
            if field == "snapshot_id":
                broken[field] = value
            else:
                broken["evidence"][0][field] = value
            with self.assertRaises(ValidationError):
                validate_snapshot(broken)

    def test_validation_rejects_non_integer_or_boolean_schema_versions(self):
        for version in ([], {}, True, False):
            payload = deepcopy(load_snapshot(FIXTURE))
            payload["schema_version"] = version
            with self.assertRaisesRegex(ValidationError, "schema_version"):
                validate_snapshot(payload)

    def test_structured_provider_conforms_to_provider_protocol(self):
        provider = StructuredImportProvider(FIXTURE)
        self.assertIsInstance(provider, Provider)
        self.assertIsInstance(provider, SnapshotProvider)
        records = provider.fetch({"retrieved_on": date(2026, 8, 10)})
        self.assertEqual(3, len(records))


if __name__ == "__main__":
    unittest.main()
