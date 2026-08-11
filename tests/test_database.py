from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
import tempfile
import unittest

from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import import_snapshot, load_snapshot
from china_housing_compass.models import EvidenceGrade, EvidenceRecord, PropertyRef, ValidationError


def evidence(evidence_type, value, unit="count", source="https://example.test/official/project"):
    return EvidenceRecord(
        evidence_type=evidence_type,
        value=value,
        unit=unit,
        observed_on=date(2026, 8, 10),
        retrieved_on=date(2026, 8, 10),
        source=source,
        grade=EvidenceGrade.A,
        source_id="official-project-page",
    )


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = ResearchDatabase(":memory:")
        self.db.initialize()
        self.property_id = self.db.upsert_property(
            PropertyRef("示例市", "示例区", "澄江雅苑（合成示例）", official_project_id="SYN-001")
        )
        with self.db.connection:
            self.db.connection.execute(
                """
                INSERT INTO sources(source_key, url, title, grade, retrieved_on, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("xhs-source", "https://example.test/xhs", "Synthetic source", "D", "2026-08-11", "{}"),
            )

    def tearDown(self):
        self.db.close()

    def test_evidence_is_append_only_and_source_linked(self):
        first_id = self.db.add_evidence(self.property_id, evidence("primary_inventory", 72))
        second_id = self.db.add_evidence(self.property_id, evidence("primary_inventory", 68))
        rows = self.db.list_evidence(self.property_id, "primary_inventory")
        self.assertNotEqual(first_id, second_id)
        self.assertEqual([72, 68], [row.value for row in rows])
        self.assertEqual("official-project-page", rows[0].source_id)

    def test_decimal_value_round_trips_without_float_loss(self):
        self.db.add_evidence(
            self.property_id,
            evidence("developer_quote", Decimal("1760000.00"), unit="RMB"),
        )
        row = self.db.list_evidence(self.property_id, "developer_quote")[0]
        self.assertEqual(Decimal("1760000.00"), row.value)

    def test_batch_failure_rolls_back_without_erasing_previous_rows(self):
        self.db.add_evidence(self.property_id, evidence("primary_inventory", 72))
        with self.assertRaises(Exception):
            self.db.add_evidence_batch(
                self.property_id,
                [evidence("sold_units", 48), object()],
            )
        rows = self.db.list_evidence(self.property_id)
        self.assertEqual(["primary_inventory"], [row.evidence_type for row in rows])

    def test_refresh_log_records_partial_failure(self):
        started = datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc)
        finished = datetime(2026, 8, 10, 10, 1, tzinfo=timezone.utc)
        refresh_id = self.db.record_refresh(
            property_id=self.property_id,
            status="partial",
            attempted=("official", "rent"),
            succeeded=("official",),
            failures={"rent": "source unavailable"},
            started_at=started,
            finished_at=finished,
        )
        row = self.db.latest_refresh(self.property_id)
        self.assertEqual(refresh_id, row["id"])
        self.assertEqual("partial", row["status"])
        self.assertEqual({"rent": "source unavailable"}, row["failures"])

    def test_refresh_log_records_unchanged_categories_and_latest_attempts(self):
        started = datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)
        finished = datetime(2026, 8, 11, 10, 1, tzinfo=timezone.utc)
        refresh_id = self.db.record_refresh(
            property_id=self.property_id,
            status="partial",
            attempted=("social", "parcel"),
            succeeded=(),
            failures={"social": "source unavailable"},
            started_at=started,
            finished_at=finished,
            unchanged=("parcel",),
        )

        row = self.db.latest_refresh(self.property_id)
        attempts = self.db.latest_refresh_attempts(self.property_id)
        self.assertEqual(refresh_id, row["id"])
        self.assertEqual(["parcel"], row["unchanged"])
        self.assertEqual("failed", attempts["social"]["outcome"])
        self.assertEqual("source unavailable", attempts["social"]["failure_reason"])
        self.assertEqual("unchanged", attempts["parcel"]["outcome"])

    def test_initialize_migrates_legacy_refresh_runs_for_unchanged_results(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "legacy.sqlite"
            connection = sqlite3.connect(path)
            connection.execute(
                """
                CREATE TABLE refresh_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_id INTEGER,
                    status TEXT NOT NULL,
                    attempted_json TEXT NOT NULL,
                    succeeded_json TEXT NOT NULL,
                    failures_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            connection.close()

            legacy = ResearchDatabase(path)
            try:
                columns = {
                    row["name"] for row in legacy.connection.execute("PRAGMA table_info(refresh_runs)")
                }
                self.assertIn("unchanged_json", columns)
            finally:
                legacy.close()

    def test_schema_has_snapshot_linked_source_observations(self):
        columns = {
            row["name"]
            for row in self.db.connection.execute("PRAGMA table_info(source_observations)")
        }
        self.assertEqual(
            {
                "id", "property_id", "snapshot_id", "source_key", "url", "title",
                "grade", "retrieved_on", "metadata_json", "created_at",
            },
            columns,
        )
        self.assertEqual(
            3,
            self.db.connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0],
        )

    def test_opening_v2_database_backfills_and_freezes_layer_provenance(self):
        fixture = Path(__file__).parent / "fixtures" / "research_layers_snapshot.json"
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "legacy-v2.sqlite"
            legacy = ResearchDatabase(path)
            legacy.initialize()
            imported = import_snapshot(legacy, load_snapshot(fixture))
            with legacy.connection:
                legacy.connection.execute("DROP TABLE source_observations")
                legacy.connection.execute("DELETE FROM schema_version WHERE version=3")
            legacy.close()

            migrated = ResearchDatabase(path)
            try:
                rows = migrated.list_research_layer(
                    imported["property_id"], "parcel_history_findings"
                )
                self.assertEqual("Synthetic history research", rows[0]["source_title"])
                with migrated.connection:
                    migrated.connection.execute(
                        "UPDATE sources SET title='mutated registry' WHERE source_key='synthetic-history'"
                    )
                rows = migrated.list_research_layer(
                    imported["property_id"], "parcel_history_findings"
                )
                self.assertEqual("Synthetic history research", rows[0]["source_title"])
                self.assertEqual(
                    3,
                    migrated.connection.execute(
                        "SELECT MAX(version) FROM schema_version"
                    ).fetchone()[0],
                )
            finally:
                migrated.close()

    def test_research_layers_append_snapshots_and_decode_json_fields(self):
        first = {
            "social_items": [{
                "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
                "locator": "https://example.test/xhs/1", "access_mode": "public_web",
                "author_role": "unknown", "content_type": "experience", "stance": "mixed",
                "summary": "synthetic sample", "observed_on": "2026-08-11",
                "retrieved_on": "2026-08-11", "grade": "D",
                "engagement": {"likes": 3}, "metadata": {"tags": ["noise"]},
            }],
        }
        second = {
            "social_items": [{
                **first["social_items"][0], "item_key": "xhs-2", "summary": "later sample",
            }],
        }

        with self.db.connection:
            first_counts = self.db.insert_research_layers(self.property_id, "snapshot-a", first)
            second_counts = self.db.insert_research_layers(self.property_id, "snapshot-b", second)

        rows = self.db.list_research_layer(self.property_id, "social_items")
        self.assertEqual(1, first_counts["social_items"])
        self.assertEqual(1, second_counts["social_items"])
        self.assertEqual(["xhs-1", "xhs-2"], [row["item_key"] for row in rows])
        self.assertEqual({"likes": 3}, rows[0]["engagement_json"])
        self.assertEqual({"tags": ["noise"]}, rows[0]["metadata_json"])

    def test_research_layers_reject_unknown_layer(self):
        with self.assertRaisesRegex(ValueError, "unknown research layer"):
            self.db.insert_research_layers(self.property_id, "snapshot-a", {"unknown": []})

    def test_research_layer_defaults_are_inserted_not_ignored(self):
        layers = {
            "social_items": [{
                "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
                "locator": "https://example.test/xhs/1", "access_mode": "public_web",
                "author_role": "unknown", "content_type": "experience", "stance": "mixed",
                "summary": "synthetic sample", "observed_on": "2026-08-11",
                "retrieved_on": "2026-08-11", "grade": "D",
            }],
            "social_comments": [{
                "comment_key": "comment-1", "source_id": "xhs-source", "parent_item_key": "xhs-1",
                "stance": "neutral", "observed_on": "2026-08-11", "retrieved_on": "2026-08-11",
                "grade": "D",
            }],
            "parcel_history_findings": [{
                "finding_key": "history-1", "source_id": "xhs-source", "geography_scope": "district",
                "historical_use": "chemical_industry", "finding_state": "lead_only",
                "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
            }],
            "environmental_findings": [{
                "finding_key": "environment-1", "source_id": "xhs-source", "geography_scope": "district",
                "hazard_type": "soil", "finding_state": "unknown", "observed_on": "2026-08-11",
                "retrieved_on": "2026-08-11", "grade": "D",
            }],
            "cultural_factors": [{
                "factor_key": "road-1", "source_id": "xhs-source", "geography_scope": "district",
                "observable_feature": "road alignment", "buyer_sensitivity": "standard",
                "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
            }],
        }

        with self.db.connection:
            counts = self.db.insert_research_layers(self.property_id, "snapshot-defaults", layers)

        self.assertEqual(1, counts["social_comments"])
        self.assertEqual(1, counts["parcel_history_findings"])
        self.assertEqual(1, counts["environmental_findings"])
        self.assertEqual(1, counts["cultural_factors"])
        self.assertEqual("", self.db.list_research_layer(self.property_id, "social_comments")[0]["summary"])

    def test_research_layer_storage_rejects_invalid_enum_before_writing(self):
        invalid_item = {
            "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
            "locator": "https://example.test/xhs/1", "access_mode": "public_web",
            "author_role": "unknown", "content_type": "experience", "stance": "not-a-stance",
            "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
        }

        with self.assertRaises(ValidationError):
            self.db.insert_research_layers(self.property_id, "snapshot-invalid", {"social_items": [invalid_item]})

        self.assertEqual([], self.db.list_research_layer(self.property_id, "social_items"))

    def test_research_layer_storage_rejects_browser_session_metadata(self):
        item = {
            "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
            "locator": "https://example.test/xhs/1", "access_mode": "public_web",
            "author_role": "unknown", "content_type": "experience", "stance": "mixed",
            "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
            "metadata": {"browser_session_id": "not-for-storage"},
        }
        with self.assertRaisesRegex(ValidationError, "session"):
            self.db.insert_research_layers(self.property_id, "snapshot-invalid", {"social_items": [item]})

    def test_research_layer_storage_rejects_unregistered_source(self):
        item = {
            "item_key": "xhs-1", "source_id": "missing-source", "platform": "xiaohongshu",
            "locator": "https://example.test/xhs/1", "access_mode": "public_web",
            "author_role": "unknown", "content_type": "experience", "stance": "mixed",
            "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
        }
        with self.assertRaisesRegex(ValidationError, "source_id"):
            self.db.insert_research_layers(self.property_id, "snapshot-invalid", {"social_items": [item]})

    def test_research_layer_storage_rejects_orphan_comment(self):
        comment = {
            "comment_key": "comment-1", "source_id": "xhs-source", "parent_item_key": "missing-item",
            "stance": "neutral", "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
        }
        with self.assertRaisesRegex(ValidationError, "parent_item_key"):
            self.db.insert_research_layers(self.property_id, "snapshot-invalid", {"social_comments": [comment]})

    def test_research_layer_comment_can_reference_item_in_same_snapshot(self):
        item = {
            "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
            "locator": "https://example.test/xhs/1", "access_mode": "public_web",
            "author_role": "unknown", "content_type": "experience", "stance": "mixed",
            "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
        }
        comment = {
            "comment_key": "comment-1", "source_id": "xhs-source", "parent_item_key": "xhs-1",
            "stance": "neutral", "summary": "synthetic sample", "observed_on": "2026-08-11",
            "retrieved_on": "2026-08-11", "grade": "D",
        }
        with self.db.connection:
            self.db.insert_research_layers(self.property_id, "snapshot-a", {"social_items": [item]})
            counts = self.db.insert_research_layers(self.property_id, "snapshot-a", {"social_comments": [comment]})

        self.assertEqual(1, counts["social_comments"])


if __name__ == "__main__":
    unittest.main()
