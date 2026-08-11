from decimal import Decimal
import unittest

from china_housing_compass.models import ScenarioInput, ValidationError
from china_housing_compass.scenarios import (
    calculate_delivery_loss_rate,
    calculate_delivery_value,
    calculate_maximum_purchase_price,
    run_standard_scenarios,
)


def scenario(name="downside", factors=None):
    return ScenarioInput(
        name=name,
        current_comparable_value=Decimal("2200000"),
        factors=factors
        or (
            ("city", Decimal("0.97")),
            ("submarket", Decimal("0.95")),
            ("project", Decimal("0.90")),
            ("product", Decimal("0.98")),
        ),
        years_to_delivery=Decimal("0.83"),
        required_return=Decimal("0.03"),
        purchase_costs=Decimal("30000"),
        financing_costs=Decimal("50000"),
        risk_reserve=Decimal("100000"),
    )


class ScenarioTests(unittest.TestCase):
    def test_delivery_value_multiplies_disclosed_factors(self):
        result = calculate_delivery_value(scenario())

        self.assertEqual(Decimal("1788078.60"), result.delivery_value)
        self.assertLess(result.maximum_purchase_price_today, result.delivery_value)
        self.assertEqual(("city", "submarket", "project", "product"), result.applied_factors)
        self.assertEqual(
            (Decimal("0.97"), Decimal("0.95"), Decimal("0.90"), Decimal("0.98")),
            result.factor_values,
        )

    def test_max_price_discount_and_costs_are_applied_once(self):
        item = scenario(
            factors=(
                ("city", Decimal("1")),
                ("submarket", Decimal("1")),
                ("project", Decimal("1")),
                ("product", Decimal("1")),
            )
        )
        maximum = calculate_maximum_purchase_price(item)
        expected = (
            Decimal("2200000") / ((Decimal("1.03")) ** Decimal("0.83"))
            - Decimal("180000")
        ).quantize(Decimal("0.01"))
        self.assertEqual(expected, maximum)

    def test_delivery_loss_rate_uses_all_in_cost(self):
        self.assertEqual(
            Decimal("0.2500"),
            calculate_delivery_loss_rate(Decimal("2400000"), Decimal("1800000")),
        )
        self.assertEqual(
            Decimal("-0.1000"),
            calculate_delivery_loss_rate(Decimal("2000000"), Decimal("2200000")),
        )

    def test_standard_scenarios_include_four_required_rows_and_optional_rows(self):
        factor_sets = {
            "upside": (("market", Decimal("1.05")),),
            "base": (("market", Decimal("1.00")),),
            "downside": (("market", Decimal("0.90")),),
            "stress": (("market", Decimal("0.72")),),
            "delay": (("market", Decimal("0.85")), ("delay", Decimal("0.96"))),
        }

        results = run_standard_scenarios(scenario("template"), factor_sets)

        self.assertEqual(("upside", "base", "downside", "stress", "delay"), tuple(results))
        self.assertEqual("stress", results["stress"].name)
        self.assertLess(results["stress"].delivery_value, results["base"].delivery_value)

    def test_missing_standard_scenario_and_invalid_loss_cost_are_rejected(self):
        with self.assertRaises(ValidationError):
            run_standard_scenarios(scenario(), {"base": (("market", Decimal("1")),)})
        with self.assertRaises(ValidationError):
            calculate_delivery_loss_rate(0, 0)


if __name__ == "__main__":
    unittest.main()
