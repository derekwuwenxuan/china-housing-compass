from datetime import date
from pathlib import Path
import unittest

from china_housing_compass.models import ValidationError
from china_housing_compass.providers.nanjing import (
    parse_njhouse_project_page,
    parse_njhouse_sale_info,
)


FIXTURES = Path(__file__).parent / "fixtures" / "nanjing"
SOURCE = "https://example.test/nanjing/project/SYN-NJ-001"
DATES = {"observed_on": date(2026, 1, 15), "retrieved_on": date(2026, 1, 16)}


class NanjingProviderTests(unittest.TestCase):
    def test_sale_info_retains_buildings_and_calculates_consistent_project_totals(self):
        html = (FIXTURES / "project_sale_info.html").read_text(encoding="utf-8")
        records = parse_njhouse_sale_info(html, SOURCE, DATES)
        latest = {record.evidence_type: record for record in records if record.scope == "property"}
        building_rows = [record for record in records if record.scope == "building"]

        self.assertEqual(120, latest["official_released_units"].value)
        self.assertEqual(72, latest["official_unsold_units"].value)
        self.assertEqual(48, latest["official_sold_units"].value)
        self.assertEqual({"1#", "2#"}, {record.metadata["building"] for record in building_rows})
        self.assertTrue(all(record.source == SOURCE for record in records))
        self.assertTrue(all(record.grade.value == "A" for record in records))

    def test_project_page_extracts_exact_entity_and_delivery_identity(self):
        html = (FIXTURES / "project_home_page.html").read_text(encoding="utf-8")
        records = parse_njhouse_project_page(html, SOURCE, DATES)
        by_type = {record.evidence_type: record.value for record in records}

        self.assertEqual("澄江雅苑（合成示例）", by_type["official_project_name"])
        self.assertEqual("示例置业有限公司", by_type["official_project_company"])
        self.assertEqual("2028-12-31", by_type["official_planned_delivery_date"])

    def test_changed_or_inconsistent_page_raises_instead_of_reusing_stale_data(self):
        with self.assertRaisesRegex(ValidationError, "projectInfoBuildingSaleInfo"):
            parse_njhouse_sale_info("<html>page layout changed</html>", SOURCE, DATES)

        inconsistent = """
        <script>var projectInfoBuildingSaleInfo = {
          "projectName":"澄江雅苑（合成示例）",
          "buildings":[{"buildingName":"1#","released":50,"unsold":31,"sold":20}]
        };</script>
        """
        with self.assertRaisesRegex(ValidationError, "inconsistent"):
            parse_njhouse_sale_info(inconsistent, SOURCE, DATES)


if __name__ == "__main__":
    unittest.main()
