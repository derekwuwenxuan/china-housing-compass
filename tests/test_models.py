from datetime import date
from decimal import Decimal
import unittest

from china_housing_compass.models import (
    EvidenceGrade,
    EvidenceRecord,
    PropertyRef,
    ScenarioInput,
    ValidationError,
    ValuationInput,
)


class ModelTests(unittest.TestCase):
    def test_evidence_requires_source_and_dates(self):
        with self.assertRaises(ValidationError):
            EvidenceRecord(
                evidence_type="primary_listing",
                value=Decimal("1760000"),
                unit="RMB",
                observed_on=date(2026, 8, 9),
                retrieved_on=date(2026, 8, 10),
                source="",
                grade=EvidenceGrade.C,
            )

    def test_evidence_retrieval_cannot_precede_observation(self):
        with self.assertRaises(ValidationError):
            EvidenceRecord(
                evidence_type="primary_inventory",
                value=72,
                unit="count",
                observed_on=date(2026, 8, 10),
                retrieved_on=date(2026, 8, 9),
                source="https://example.test/official/project",
                grade=EvidenceGrade.A,
            )

    def test_property_requires_project_or_community(self):
        with self.assertRaises(ValidationError):
            PropertyRef(city="示例市", district="示例区", project_name="")

    def test_valuation_input_rejects_negative_values_but_accepts_zero_cost(self):
        value = ValuationInput(total_price=Decimal("1760000"), area_sqm=Decimal("88"), owner_costs=Decimal("0"))
        self.assertEqual(Decimal("0"), value.owner_costs)
        with self.assertRaises(ValidationError):
            ValuationInput(total_price=Decimal("-1"), area_sqm=Decimal("88"))

    def test_scenario_rejects_duplicate_factor_labels(self):
        with self.assertRaises(ValidationError):
            ScenarioInput(
                name="downside",
                current_comparable_value=Decimal("2200000"),
                factors=(("city", Decimal("0.97")), ("city", Decimal("0.95"))),
                years_to_delivery=Decimal("0.83"),
                required_return=Decimal("0.03"),
            )


if __name__ == "__main__":
    unittest.main()
