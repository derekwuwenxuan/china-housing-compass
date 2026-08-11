from copy import deepcopy
import unittest

from china_housing_compass.models import ValidationError
from china_housing_compass.research_layers import validate_research_layers


class ResearchLayerValidationTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "item_key": "xhs-1", "source_id": "xhs-source", "platform": "xiaohongshu",
            "locator": "https://example.test/xhs/1", "access_mode": "public_web",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11",
            "author_role": "unknown", "content_type": "experience",
            "stance": "mixed", "summary": "synthetic sample", "grade": "D",
        }

    def test_social_item_rejects_unknown_access_mode(self):
        item = deepcopy(self.item)
        item["access_mode"] = "captcha_bypass"
        with self.assertRaisesRegex(ValidationError, "access_mode"):
            validate_research_layers({"social_items": [item]}, {"xhs-source"})

    def test_social_items_and_comments_reject_grades_a_or_b(self):
        """Ordinary social evidence cannot inherit primary-record authority."""

        for grade in ("A", "B"):
            with self.subTest(layer="social_items", grade=grade):
                item = deepcopy(self.item)
                item["grade"] = grade
                with self.assertRaisesRegex(ValidationError, "grade"):
                    validate_research_layers({"social_items": [item]}, {"xhs-source"})

            with self.subTest(layer="social_comments", grade=grade):
                item = deepcopy(self.item)
                comment = {
                    "comment_key": "comment-1", "source_id": "xhs-source",
                    "parent_item_key": "xhs-1", "stance": "negative",
                    "observed_on": "2026-08-11", "retrieved_on": "2026-08-11",
                    "grade": grade,
                }
                with self.assertRaisesRegex(ValidationError, "grade"):
                    validate_research_layers(
                        {"social_items": [item], "social_comments": [comment]},
                        {"xhs-source"},
                    )

    def test_comment_rejects_an_uninspectable_parent_item(self):
        """A snippet or unavailable item cannot substantiate visible comments."""

        comment = {
            "comment_key": "comment-1", "source_id": "xhs-source",
            "parent_item_key": "xhs-1", "stance": "negative",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
        }
        for access_mode in ("indexed_snippet", "unavailable"):
            with self.subTest(access_mode=access_mode):
                item = deepcopy(self.item)
                item["access_mode"] = access_mode
                with self.assertRaisesRegex(ValidationError, "access_mode"):
                    validate_research_layers(
                        {"social_items": [item], "social_comments": [comment]},
                        {"xhs-source"},
                    )

    def test_social_run_counts_are_non_boolean_non_negative_integers(self):
        run = {
            "run_key": "run-1", "source_id": "xhs-source", "access_mode": "public_web",
            "requested_count": 3, "obtained_count": 2,
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "C",
        }
        for field, value in (
            ("requested_count", True),
            ("requested_count", -1),
            ("requested_count", 1.5),
            ("obtained_count", False),
            ("obtained_count", -1),
            ("obtained_count", "2"),
        ):
            with self.subTest(field=field, value=value):
                invalid = deepcopy(run)
                invalid[field] = value
                with self.assertRaisesRegex(ValidationError, field):
                    validate_research_layers({"social_research_runs": [invalid]}, {"xhs-source"})

    def test_area_history_requires_explicit_geography_scope(self):
        finding = {
            "finding_key": "history-1", "source_id": "official-history",
            "historical_use": "chemical_industry", "finding_state": "lead_only",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "C",
        }
        with self.assertRaisesRegex(ValidationError, "geography_scope"):
            validate_research_layers({"parcel_history_findings": [finding]}, {"official-history"})

    def test_comment_requires_parent_in_same_snapshot(self):
        comment = {
            "comment_key": "comment-1", "source_id": "xhs-source",
            "parent_item_key": "missing-item", "stance": "negative",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
        }
        with self.assertRaisesRegex(ValidationError, "parent_item_key"):
            validate_research_layers({"social_comments": [comment]}, {"xhs-source"})

    def test_social_item_rejects_unregistered_source_and_reversed_dates(self):
        missing_source = deepcopy(self.item)
        missing_source["source_id"] = "missing"
        with self.assertRaisesRegex(ValidationError, "source_id"):
            validate_research_layers({"social_items": [missing_source]}, {"xhs-source"})

        reversed_dates = deepcopy(self.item)
        reversed_dates["retrieved_on"] = "2026-08-10"
        with self.assertRaisesRegex(ValidationError, "retrieved_on"):
            validate_research_layers({"social_items": [reversed_dates]}, {"xhs-source"})

    def test_research_layers_reject_browser_session_data(self):
        item = deepcopy(self.item)
        item["metadata"] = {"browser_session_id": "not-for-storage"}
        with self.assertRaisesRegex(ValidationError, "session"):
            validate_research_layers({"social_items": [item]}, {"xhs-source"})

    def test_optional_research_dates_must_be_iso_and_ordered(self):
        item = deepcopy(self.item)
        item["published_on"] = "2026/08/10"
        with self.assertRaisesRegex(ValidationError, "published_on"):
            validate_research_layers({"social_items": [item]}, {"xhs-source"})

        finding = {
            "finding_key": "history-1", "source_id": "xhs-source",
            "geography_scope": "district", "historical_use": "chemical_industry",
            "finding_state": "lead_only", "start_on": "2026-08-11", "end_on": "2026-08-10",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "C",
        }
        with self.assertRaisesRegex(ValidationError, "end_on"):
            validate_research_layers({"parcel_history_findings": [finding]}, {"xhs-source"})

    def test_cultural_factor_requires_geography_scope(self):
        factor = {
            "factor_key": "road-1", "source_id": "xhs-source",
            "observable_feature": "road alignment", "buyer_sensitivity": "standard",
            "observed_on": "2026-08-11", "retrieved_on": "2026-08-11", "grade": "D",
        }
        with self.assertRaisesRegex(ValidationError, "geography_scope"):
            validate_research_layers({"cultural_factors": [factor]}, {"xhs-source"})
