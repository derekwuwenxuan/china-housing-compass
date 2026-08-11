from pathlib import Path
import re
import unittest

from china_housing_compass.dashboard import TEMPLATE_PATH


ROOT = Path(__file__).parents[1]


class PackagingTests(unittest.TestCase):
    def test_mit_license_and_bilingual_readme_exist(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 China Housing Compass contributors", license_text)
        self.assertIn("## Installation", readme)
        self.assertIn("## 中文使用说明", readme)
        self.assertIn("guaranteed bottom", readme.lower())
        self.assertIn("china-housing-compass init", readme)

    def test_skill_entrypoint_and_packaged_template_are_present(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        setup_compat = (ROOT / "setup.py").read_text(encoding="utf-8")
        self.assertIn('china-housing-compass = "china_housing_compass.cli:main"', pyproject)
        self.assertIn('"schema.sql", "templates/*.html"', pyproject)
        self.assertIn('"schema.sql", "templates/*.html"', setup_compat)
        self.assertTrue((ROOT / "skills" / "china-housing-compass" / "SKILL.md").is_file())
        self.assertTrue(TEMPLATE_PATH.is_file())

    def test_dashboard_template_stays_self_contained_with_evidence_badges(self):
        """External assets or missing evidence states would weaken offline review."""

        template = TEMPLATE_PATH.read_text(encoding="utf-8").lower()
        self.assertIn(".badge", template)
        self.assertIn(".badge-stale", template)
        for network_markup in (
            r"https?://",
            r"(?:src|href|action)\s*=\s*['\"]?//",
            r"url\(\s*['\"]?(?:https?:)?//",
            r"<\s*(?:script|iframe|object|embed|link)\b",
            r"@import",
            r"cdn",
        ):
            self.assertNotRegex(template, network_markup)

    def test_contributing_explains_source_provenance(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("city provider", contributing.lower())
        self.assertIn("provenance", contributing.lower())
        self.assertIn("private", contributing.lower())

    def test_skill_routes_social_and_land_history_due_diligence(self):
        skill_root = ROOT / "skills" / "china-housing-compass"
        skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        synthetic_case = (skill_root / "references" / "synthetic-river-garden-case.md").read_text(
            encoding="utf-8"
        )
        report_contract = (
            skill_root / "references" / "report-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("authorized browser", skill_text.lower())
        self.assertIn("social-media-and-comments.md", skill_text)
        self.assertIn("parcel-history-and-cultural-acceptance.md", skill_text)
        self.assertLessEqual(len(skill_text.splitlines()), 500)
        self.assertIn("case-scoped", synthetic_case.lower())
        self.assertIn("non-transferable", synthetic_case.lower())
        self.assertIn("zero-weight", synthetic_case.lower())
        self.assertIn("Social reputation and captured comments", report_contract)
        self.assertIn(
            "Parcel history, environment, infrastructure, and cultural acceptance",
            report_contract,
        )
        self.assertEqual(
            [
                ("1", "Decision"),
                ("2", "Exact identity"),
                ("3", "Price types now"),
                ("4", "Valuation ranges"),
                ("5", "Formula worksheet"),
                ("6", "Five-year context"),
                ("7", "Developer, contract, construction, and delivery"),
                ("8", "Social reputation and captured comments"),
                ("9", "Parcel history, environment, infrastructure, and cultural acceptance"),
                ("10", "Affordability"),
                ("11", "Conditional scenarios"),
                ("12", "Evidence, sampling, and freshness"),
                ("13", "Missing evidence and next actions"),
            ],
            re.findall(r"^## (\d+)\. (.+)$", report_contract, flags=re.MULTILINE),
        )
        for routed_reference in (
            "social-media-and-comments.md",
            "parcel-history-and-cultural-acceptance.md",
        ):
            self.assertTrue((skill_root / "references" / routed_reference).is_file())

    def test_skill_prioritizes_primary_intermediaries_and_china_macro_scenarios(self):
        skill_root = ROOT / "skills" / "china-housing-compass"
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8").lower()
        sources = (
            skill_root / "references" / "china-data-sources.md"
        ).read_text(encoding="utf-8").lower()
        valuation = (
            skill_root / "references" / "valuation-methodology.md"
        ).read_text(encoding="utf-8").lower()
        report = (
            skill_root / "references" / "report-contract.md"
        ).read_text(encoding="utf-8").lower()
        delivery = (
            skill_root / "references" / "delivery-scenario-model.md"
        ).read_text(encoding="utf-8").lower()
        database = (
            skill_root / "references" / "database-and-refresh.md"
        ).read_text(encoding="utf-8").lower()

        acquisition_contract = "\n".join((skill, sources, database))
        for required in (
            "lianjia",
            "beike",
            "anysearch",
            "computer use",
            "platform coverage matrix",
            "deduplicate",
            "never silently substitute",
        ):
            self.assertIn(required, acquisition_contract)
        self.assertIn("attempt both lianjia and beike", acquisition_contract)
        self.assertIn("at least two independent intermediary platforms", acquisition_contract)
        for required in (
            "asking-price distribution",
            "platform-reported transaction distribution",
            "mean, median and lower quantile",
            "judicial-auction",
            "failed-auction rate",
            "bank appraisal",
        ):
            self.assertIn(required, acquisition_contract)

        valuation_contract = "\n".join((valuation, report, delivery, skill))
        for required in (
            "dual-anchor alignment",
            "aligned",
            "diverging",
            "insufficient_evidence",
            "one-to-three-year",
            "china-first",
            "kondratiev",
            "zero-weight",
        ):
            self.assertIn(required, valuation_contract)

        parcel_contract = (
            skill_root / "references" / "parcel-history-and-cultural-acceptance.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("exact-parcel evidence", parcel_contract)
        self.assertIn("default valuation weight of zero", parcel_contract)
        self.assertIn("must not enter a price adjustment", parcel_contract)

    def test_skill_handles_user_supplied_platform_aggregate_without_promoting_it_to_a_floor(self):
        """An aggregate-only screenshot must not become an exact unit value."""

        skill_root = ROOT / "skills" / "china-housing-compass"
        reference_path = skill_root / "references" / "platform-screenshot-evidence.md"
        self.assertTrue(
            reference_path.is_file(),
            "the skill must route aggregate-only screenshots to a dedicated evidence contract",
        )

        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8").lower()
        reference = reference_path.read_text(encoding="utf-8").lower()
        expected = (
            ROOT
            / "tests"
            / "skill_scenarios"
            / "platform-screenshot-conflict-results.md"
        ).read_text(encoding="utf-8").lower()

        self.assertIn("platform-screenshot-evidence.md", skill)
        for required in (
            "user_supplied_screenshot",
            "sample_count: unknown",
            "area-equivalent scenario",
            "insufficient_evidence",
            "asking average",
            "platform-reported transaction average",
            "per-record transaction",
            "raw screenshot",
            "structurally dependent",
        ):
            self.assertIn(required, reference)
            self.assertIn(required, expected)

        self.assertNotRegex(reference, r"(?:rmb|¥|￥)\s*[\d,.]+")
        self.assertNotRegex(reference, r"\b\d{4,}\b")

    def test_gitignore_excludes_private_and_generated_state(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            "*.sqlite",
            "housing-research/",
            "dashboard/generated/",
            "reports/generated/",
            ".env",
            "__pycache__/",
            "credentials*.json",
        ):
            self.assertIn(pattern, ignored)


if __name__ == "__main__":
    unittest.main()
