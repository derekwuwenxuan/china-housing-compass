from datetime import datetime, timezone
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from china_housing_compass.dashboard import build_dashboard
from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import import_snapshot, load_snapshot
from china_housing_compass.providers.structured_import import StructuredImportProvider
from china_housing_compass.refresh import RefreshRequest, run_refresh


FIXTURE = Path(__file__).parent / "fixtures" / "normalized_snapshot.json"
RESEARCH_FIXTURE = Path(__file__).parent / "fixtures" / "research_layers_snapshot.json"


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db_path = self.root / "housing.sqlite"
        db = ResearchDatabase(self.db_path)
        db.initialize()
        imported = import_snapshot(db, load_snapshot(FIXTURE))
        property_id = imported["property_id"]
        now = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
        db.record_refresh(
            property_id,
            "success",
            ("official_project", "field_quote"),
            ("official_project", "field_quote"),
            {},
            now,
            now,
        )
        db.save_valuation_run(
            property_id,
            "owner_occupation",
            "wait",
            "medium",
            {
                "comparable_fair_range": ["1500000", "1700000"],
                "rent_supported_value": "1200000",
                "risk_adjusted_max_price": "1450000",
                "scenarios": {
                    "base": {"delivery_value": "1650000"},
                    "stress": {"delivery_value": "1188000"}
                },
                "missing_categories": ["verified rent", "resale transactions"]
            },
        )
        db.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_dashboard_is_offline_source_backed_and_has_required_sections(self):
        outputs = build_dashboard(self.db_path, self.root / "dashboard")
        by_name = {path.name: path for path in outputs}
        project_html = by_name["synthetic-river-garden.html"].read_text(encoding="utf-8")

        self.assertIn("China Housing Compass", project_html)
        self.assertIn("Last successful refresh", project_html)
        self.assertIn("72", project_html)
        self.assertIn("Source grade A", project_html)
        for section in (
            "Recommendation",
            "Valuation ranges",
            "Five-year context",
            "Price and rent comparables",
            "Inventory and supply",
            "Developer and delivery risk",
            "Infrastructure status",
            "Affordability",
            "Delivery scenarios",
            "Sources and evidence",
            "Missing evidence and freshness",
        ):
            self.assertIn(section, project_html)
        self.assertNotIn("cdn.", project_html.lower())
        self.assertNotIn("<script src=", project_html.lower())
        self.assertIn("index.html", by_name)

    def test_dashboard_escapes_property_and_source_text(self):
        db = ResearchDatabase(self.db_path)
        db.connection.execute(
            "UPDATE properties SET project_name=? WHERE id=1",
            ("<img src=x onerror=alert(1)>",),
        )
        db.connection.execute(
            "UPDATE evidence SET source=? WHERE id=1",
            ("<script>alert(1)</script>",),
        )
        db.connection.commit()
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "escaped-dashboard")
        project_path = next(path for path in outputs if path.name != "index.html")
        html = project_path.read_text(encoding="utf-8")
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;img", html)
        self.assertIn("&lt;script&gt;", html)

    def test_dashboard_renders_escaped_social_and_land_history_layers(self):
        """Missing research-layer renderers would hide source-backed risk context."""

        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        payload["research_layers"]["social_items"][0]["summary"] = '<img src=x onerror="alert(1)">'
        payload["research_layers"]["cultural_factors"][0]["cultural_interpretation"] = "<script>alert(2)</script>"
        payload["research_layers"]["social_research_runs"][0].update(
            observed_on="2026-01-01", retrieved_on="2026-01-01"
        )
        db = ResearchDatabase(self.db_path)
        imported = import_snapshot(db, payload)
        db.connection.execute(
            "UPDATE social_items SET metadata_json=? WHERE property_id=?",
            (json.dumps({"username": "private-user", "browser_session_id": "secret-session"}), imported["property_id"]),
        )
        db.connection.commit()
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "research-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "合成研究样本" in path.read_text(encoding="utf-8")
        )

        for section in (
            "Social reputation and captured comments",
            "Parcel history",
            "Environmental legacy",
            "Cultural acceptance and resale perception",
        ):
            self.assertIn(section, project_html)
        self.assertIn("2 posts / 3 comments", project_html)
        self.assertIn("authorized browser", project_html.lower())
        self.assertIn("Freshness: stale", project_html)
        self.assertIn("Exact parcel: unknown", project_html)
        self.assertIn("&lt;img", project_html)
        self.assertIn("&lt;script&gt;", project_html)
        self.assertNotIn('<img src=x onerror="alert(1)">', project_html)
        self.assertNotIn("<script>alert(2)</script>", project_html)
        self.assertNotIn("private-user", project_html)
        self.assertNotIn("secret-session", project_html)

    def test_dashboard_keeps_social_row_grade_separate_from_source_registry_grade(self):
        """A high-grade source observation must not upgrade social posts or comments."""

        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        social_source = next(
            source for source in payload["sources"]
            if source["source_id"] == "synthetic-social-posts"
        )
        social_source["grade"] = "A"
        db = ResearchDatabase(self.db_path)
        import_snapshot(db, payload)
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "social-grade-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "合成研究样本" in path.read_text(encoding="utf-8")
        )

        self.assertEqual(project_html.count("Evidence grade / 证据等级: D"), 5)
        self.assertNotIn("Evidence grade / 证据等级: A", project_html)
        self.assertNotIn("Evidence grade / 证据等级: B", project_html)
        self.assertEqual(project_html.count("Source registry grade / 来源登记等级: A"), 5)

    def test_dashboard_uses_latest_social_snapshot_and_exact_parcel_finding(self):
        """Old append-only samples must not inflate the current dashboard evidence."""

        initial = load_snapshot(RESEARCH_FIXTURE)
        latest = deepcopy(initial)
        latest["snapshot_id"] = "synthetic-research-2026-08-12"
        latest["research_layers"] = {
            "social_research_runs": [{
                "run_key": "synthetic-run-current", "source_id": "synthetic-social-run",
                "access_mode": "public_web", "platforms": ["current-forum"],
                "queries": ["current project"], "requested_count": 2, "obtained_count": 1,
                "failures": {"blocked-forum": "<b>needs login</b>"},
                "observed_on": "2026-08-12", "retrieved_on": "2026-08-12", "grade": "C",
            }, {
                "run_key": "synthetic-run-current-sibling", "source_id": "synthetic-social-run",
                "access_mode": "indexed_snippet", "platforms": ["sibling-video"],
                "queries": ["current delivery"], "requested_count": 1, "obtained_count": 0,
                "failures": {"sibling-video": "source unavailable"},
                "observed_on": "2026-08-12", "retrieved_on": "2026-08-12", "grade": "C",
            }],
            "social_items": [{
                "item_key": "current-post", "source_id": "synthetic-social-posts",
                "platform": "current-forum", "locator": "https://example.test/current/1",
                "access_mode": "public_web", "author_role": "visitor", "content_type": "experience",
                "stance": "positive", "summary": "Current post only.",
                "published_on": "2026-08-11", "observed_on": "2026-08-12",
                "retrieved_on": "2026-08-12", "grade": "D",
            }],
            "social_comments": [{
                "comment_key": "current-comment", "source_id": "synthetic-social-posts",
                "parent_item_key": "current-post", "stance": "negative", "summary": "Current comment only.",
                "observed_on": "2026-08-12", "retrieved_on": "2026-08-12", "grade": "D",
            }],
            "parcel_history_findings": [{
                "finding_key": "synthetic-history-current", "source_id": "synthetic-history",
                "geography_scope": "exact_parcel", "historical_use": "residential",
                "finding_state": "officially_verified", "observed_on": "2026-08-12",
                "retrieved_on": "2026-08-12", "grade": "B",
            }],
        }
        db = ResearchDatabase(self.db_path)
        import_snapshot(db, initial)
        import_snapshot(db, latest)
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "latest-research-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "合成研究样本" in path.read_text(encoding="utf-8")
        )

        self.assertIn("1 posts / 1 comments", project_html)
        self.assertIn("current-forum", project_html)
        self.assertIn("sibling-video", project_html)
        self.assertIn("public web", project_html)
        self.assertIn("indexed snippet", project_html)
        self.assertNotIn("Synthetic post summary two.", project_html)
        self.assertIn("blocked-forum: &lt;b&gt;needs login&lt;/b&gt;", project_html)
        self.assertIn("sibling-video: source unavailable", project_html)
        self.assertNotIn("blocked-forum: <b>needs login</b>", project_html)
        self.assertIn("Exact parcel: residential", project_html)
        self.assertNotIn("Exact parcel: unknown", project_html)

    def test_dashboard_without_runs_uses_latest_social_snapshot(self):
        """No-run social imports must not merge distinct samples from older snapshots."""

        older = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        older["snapshot_id"] = "synthetic-no-run-old"
        older["property"]["project_name"] = "无运行社交样本"
        older["research_layers"] = {
            "social_items": [{
                "item_key": "old-no-run-post", "source_id": "synthetic-social-posts",
                "platform": "old-forum", "locator": "https://example.test/old/1",
                "access_mode": "public_web", "author_role": "visitor", "content_type": "experience",
                "stance": "negative", "summary": "Older no-run post.",
                "published_on": "2026-08-10", "observed_on": "2026-08-11",
                "retrieved_on": "2026-08-11", "grade": "D",
            }],
            "social_comments": [{
                "comment_key": "old-no-run-comment", "source_id": "synthetic-social-posts",
                "parent_item_key": "old-no-run-post", "stance": "negative", "summary": "Older no-run comment.",
                "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
            }],
        }
        latest = deepcopy(older)
        latest["snapshot_id"] = "synthetic-no-run-current"
        latest["research_layers"]["social_items"][0].update(
            item_key="current-no-run-post", platform="current-no-run-forum", summary="Current no-run post.",
            published_on="2026-08-11", observed_on="2026-08-12", retrieved_on="2026-08-12",
        )
        latest["research_layers"]["social_comments"][0].update(
            comment_key="current-no-run-comment", parent_item_key="current-no-run-post",
            summary="Current no-run comment.", observed_on="2026-08-12", retrieved_on="2026-08-12",
        )
        db = ResearchDatabase(self.db_path)
        import_snapshot(db, older)
        import_snapshot(db, latest)
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "no-run-research-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "无运行社交样本" in path.read_text(encoding="utf-8")
        )

        self.assertIn("1 posts / 1 comments", project_html)
        self.assertIn("Current no-run post.", project_html)
        self.assertNotIn("Older no-run post.", project_html)

    def test_dashboard_prefers_newer_items_over_an_older_research_run(self):
        """An older run must not hide a newer item/comment-only social snapshot."""

        older = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        older["snapshot_id"] = "synthetic-old-run"
        older["property"]["project_name"] = "新旧社交快照样本"
        older["research_layers"] = {
            "social_research_runs": [{
                "run_key": "old-run", "source_id": "synthetic-social-run",
                "access_mode": "public_web", "platforms": ["old-run-forum"],
                "queries": ["old query"], "requested_count": 1, "obtained_count": 1, "failures": {},
                "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "C",
            }],
            "social_items": [{
                "item_key": "old-run-post", "source_id": "synthetic-social-posts",
                "platform": "old-run-forum", "locator": "https://example.test/old-run/1",
                "access_mode": "public_web", "author_role": "visitor", "content_type": "experience",
                "stance": "negative", "summary": "Older run post.",
                "published_on": "2026-08-10", "observed_on": "2026-08-11",
                "retrieved_on": "2026-08-11", "grade": "D",
            }],
            "social_comments": [{
                "comment_key": "old-run-comment", "source_id": "synthetic-social-posts",
                "parent_item_key": "old-run-post", "stance": "negative", "summary": "Older run comment.",
                "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
            }],
        }
        latest = deepcopy(older)
        latest["snapshot_id"] = "synthetic-new-items"
        latest["research_layers"].pop("social_research_runs")
        latest["research_layers"]["social_items"][0].update(
            item_key="new-item-post", platform="new-item-forum", summary="Newer item-only post.",
            observed_on="2026-08-12", retrieved_on="2026-08-12",
        )
        latest["research_layers"]["social_comments"][0].update(
            comment_key="new-item-comment", parent_item_key="new-item-post", summary="Newer item-only comment.",
            observed_on="2026-08-12", retrieved_on="2026-08-12",
        )
        db = ResearchDatabase(self.db_path)
        import_snapshot(db, older)
        import_snapshot(db, latest)
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "newer-items-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "新旧社交快照样本" in path.read_text(encoding="utf-8")
        )

        self.assertIn("1 posts / 1 comments", project_html)
        self.assertIn("Newer item-only post.", project_html)
        self.assertNotIn("Older run post.", project_html)
        self.assertNotIn("old-run-forum", project_html)

    def test_dashboard_renders_complete_research_views_and_escapes_new_fields(self):
        payload = deepcopy(load_snapshot(RESEARCH_FIXTURE))
        first_post = payload["research_layers"]["social_items"][0]
        first_post["engagement"] = {"likes": "<b>9</b>"}
        first_post["commercial"] = {
            "commercial_interest": True,
            "marker": '<img src=x onerror="commercial()">',
        }
        first_post["metadata"] = {
            "unverified_allegations": ["<script>unverified()</script>"],
        }
        payload["research_layers"]["social_items"][1]["commercial"] = {
            "commercial_interest": False,
        }
        first_comment = payload["research_layers"]["social_comments"][0]
        first_comment["themes"] = ["noise <svg onload=theme()>" ]
        first_comment["engagement"] = {"likes": 4}
        parcel = payload["research_layers"]["parcel_history_findings"][1]
        parcel.update(
            start_on="1998-01-01",
            end_on="2008-12-31",
            distance_meters=420,
            direction="north <script>direction()</script>",
        )
        environment = payload["research_layers"]["environmental_findings"][0]
        environment["valuation_treatment"] = "risk reserve <b>required</b>"
        cultural = payload["research_layers"]["cultural_factors"][0]
        cultural["objective_counterpart"] = "traffic safety <img src=x>"
        cultural["liquidity_treatment"] = "narrow target buyers <script>x()</script>"

        db = ResearchDatabase(self.db_path)
        imported = import_snapshot(db, payload)
        now = datetime(2026, 8, 12, tzinfo=timezone.utc)
        db.record_refresh(
            imported["property_id"],
            "partial",
            ("social", "parcel"),
            ("parcel",),
            {"social": "login <b>required</b>"},
            now,
            now,
        )
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "complete-research-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "合成研究样本" in path.read_text(encoding="utf-8")
        )

        for expected in (
            "Sample time window: 2026-08-10 – 2026-08-11",
            "noise &lt;svg onload=theme()&gt;",
            "Commercial-marked posts: 1/2 (50.0%)",
            "likes: &lt;b&gt;9&lt;/b&gt;",
            "&lt;script&gt;unverified()&lt;/script&gt;",
            "1998-01-01 – 2008-12-31",
            "420 m",
            "north &lt;script&gt;direction()&lt;/script&gt;",
            "risk reserve &lt;b&gt;required&lt;/b&gt;",
            "traffic safety &lt;img src=x&gt;",
            "narrow target buyers &lt;script&gt;x()&lt;/script&gt;",
            "Social refresh: stale",
            "login &lt;b&gt;required&lt;/b&gt;",
            "parcel",
            "fresh",
        ):
            self.assertIn(expected, project_html)
        for unsafe in (
            "<svg onload=theme()>",
            "<script>unverified()</script>",
            '<img src=x onerror="commercial()">',
            "<script>direction()</script>",
        ):
            self.assertNotIn(unsafe, project_html)

    def test_dashboard_uses_immutable_snapshot_source_provenance(self):
        first = load_snapshot(RESEARCH_FIXTURE)
        later = deepcopy(first)
        later["snapshot_id"] = "synthetic-provenance-2026-08-12"
        later["sources"][2].update(
            url="https://example.test/history/new",
            title="New history title",
            grade="C",
            retrieved_on="2026-08-12",
        )
        later["research_layers"] = {
            "parcel_history_findings": [{
                "finding_key": "new-history", "source_id": "synthetic-history",
                "geography_scope": "within_500m", "historical_use": "new use",
                "finding_state": "lead_only", "observed_on": "2026-08-12",
                "retrieved_on": "2026-08-12", "grade": "C",
            }],
        }
        db = ResearchDatabase(self.db_path)
        import_snapshot(db, first)
        import_snapshot(db, later)
        db.close()

        outputs = build_dashboard(self.db_path, self.root / "provenance-dashboard")
        project_html = next(
            path.read_text(encoding="utf-8")
            for path in outputs
            if "合成研究样本" in path.read_text(encoding="utf-8")
        )

        self.assertIn("Synthetic history research", project_html)
        self.assertIn("https://example.test/history", project_html)
        self.assertIn("Source grade: B", project_html)
        self.assertIn("New history title", project_html)
        self.assertIn("https://example.test/history/new", project_html)
        self.assertIn("Source grade: C", project_html)

    def test_unchanged_dashboard_keeps_the_prior_success_timestamp(self):
        db = ResearchDatabase(self.db_path)
        result = run_refresh(
            db,
            {"official_project": StructuredImportProvider(FIXTURE)},
            RefreshRequest(
                1,
                categories=("official_project",),
                dashboard_dir=self.root / "unchanged-dashboard",
            ),
        )
        db.close()

        self.assertEqual("unchanged", result.status)
        project_html = (self.root / "unchanged-dashboard" / "synthetic-river-garden.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Current refresh", project_html)
        self.assertIn("unchanged", project_html)
        self.assertIn("2026-08-10T12:00:00+00:00", project_html)
        self.assertIn("no new records", project_html)
        self.assertNotIn("Latest refresh was not fully successful", project_html)


if __name__ == "__main__":
    unittest.main()
