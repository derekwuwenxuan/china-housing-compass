from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from china_housing_compass.cli import main
from china_housing_compass.database import ResearchDatabase
from china_housing_compass.importers import load_snapshot
from china_housing_compass.models import ScenarioInput
from china_housing_compass.risk import detect_red_flags, recommend
from china_housing_compass.scenarios import run_standard_scenarios
from china_housing_compass.valuation import floor_land_price, listing_unit_price


ROOT = Path(__file__).parents[1]
CASE = ROOT / "examples" / "synthetic-river-garden"


class SyntheticEndToEndTests(unittest.TestCase):
    def test_public_case_runs_without_private_identity_or_false_certainty(self):
        property_data = json.loads((CASE / "property.json").read_text(encoding="utf-8"))
        payload = load_snapshot(CASE / "evidence.json")
        scenario_data = json.loads((CASE / "scenarios.json").read_text(encoding="utf-8"))

        self.assertIs(property_data["synthetic"], True)
        self.assertEqual("示例区", property_data["district"])
        self.assertEqual("示例置业有限公司", property_data["project_company"])
        self.assertEqual(Decimal("20000.00"), listing_unit_price(1760000, 88))
        self.assertNotIn("phone", json.dumps(payload, ensure_ascii=False).lower())
        self.assertNotIn("email", json.dumps(payload, ensure_ascii=False).lower())

        by_type = {item["evidence_type"]: item for item in payload["evidence"]}
        self.assertEqual(120, by_type["official_released_units"]["value"])
        self.assertEqual(72, by_type["official_unsold_units"]["value"])
        self.assertEqual(48, by_type["official_sold_units"]["value"])
        self.assertTrue(by_type["scenario_monthly_rent_low"]["metadata"]["is_scenario"])
        self.assertTrue(by_type["scenario_land_transaction_total"]["metadata"]["is_assumption"])
        self.assertEqual(
            Decimal("10000.00"),
            floor_land_price(
                by_type["scenario_land_transaction_total"]["value"],
                by_type["official_land_area_sqm"]["value"],
                by_type["official_far"]["value"],
            ),
        )

    def test_case_import_risk_scenarios_and_dashboard(self):
        with tempfile.TemporaryDirectory() as tempdir:
            workspace = Path(tempdir) / "research"
            self.assertEqual(0, main(["init", str(workspace)]))
            self.assertEqual(
                0,
                main(["import", str(workspace), str(CASE / "evidence.json")]),
            )
            db = ResearchDatabase(workspace / "housing.sqlite")
            latest = db.latest_evidence(1)
            findings = detect_red_flags(latest.values())
            assessment = recommend(
                {"asking_price": Decimal("1760000"), "risk_adjusted_max_price": Decimal("1550000")},
                findings,
                "owner_occupation",
            )
            self.assertIn(assessment.recommendation, ("wait", "walk_away"))
            self.assertIn("inventory_claim_conflict", assessment.veto_codes)
            self.assertIn("unavailable_promised_product_evidence", assessment.veto_codes)

            scenario_data = json.loads((CASE / "scenarios.json").read_text(encoding="utf-8"))
            base = scenario_data["base_input"]
            item = ScenarioInput(
                name="template",
                current_comparable_value=Decimal(base["current_comparable_value"]),
                factors=(("placeholder", Decimal("1")),),
                years_to_delivery=Decimal(base["years_to_delivery"]),
                required_return=Decimal(base["required_return"]),
                purchase_costs=Decimal(base["purchase_costs"]),
                financing_costs=Decimal(base["financing_costs"]),
                risk_reserve=Decimal(base["risk_reserve"]),
            )
            factor_sets = {
                name: tuple((label, Decimal(value)) for label, value in factors)
                for name, factors in scenario_data["factor_sets"].items()
            }
            results = run_standard_scenarios(item, factor_sets)
            self.assertTrue({"base", "downside", "stress"}.issubset(results))
            self.assertGreater(results["base"].delivery_value, results["stress"].delivery_value)
            self.assertNotIn("certain 50% loss", scenario_data["disclaimer"].lower())
            self.assertIn("no scenario is a guaranteed bottom", scenario_data["disclaimer"].lower())
            self.assertNotIn("必跌一半", scenario_data["disclaimer"])

            db.save_valuation_run(
                1,
                "owner_occupation",
                assessment.recommendation,
                "medium",
                {
                    "risk_adjusted_max_price": "1550000",
                    "scenarios": {
                        name: {"delivery_value": str(value.delivery_value)}
                        for name, value in results.items()
                    },
                    "missing_categories": ["verified transactions", "actual project rent"],
                },
            )
            db.close()
            self.assertEqual(0, main(["dashboard", str(workspace)]))
            html = (workspace / "dashboard" / "synthetic-river-garden.html").read_text(encoding="utf-8")
            self.assertIn("wait", html)
            self.assertIn("stress", html)
            self.assertIn("72", html)


if __name__ == "__main__":
    unittest.main()
