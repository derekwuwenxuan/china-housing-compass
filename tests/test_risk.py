from datetime import date
from decimal import Decimal
import unittest

from china_housing_compass.models import EvidenceGrade, EvidenceRecord
from china_housing_compass.risk import calculate_confidence, detect_red_flags, recommend


def fact(evidence_type, value, grade, *, category=""):
    metadata = {"category": category} if category else {}
    return EvidenceRecord(
        evidence_type=evidence_type,
        value=value,
        unit="boolean" if isinstance(value, bool) else "count",
        observed_on=date(2026, 8, 10),
        retrieved_on=date(2026, 8, 10),
        source="test source",
        grade=grade,
        metadata=metadata,
    )


def value_ranges():
    return {
        "asking_price": Decimal("1760000"),
        "risk_adjusted_max_price": Decimal("1550000"),
        "comparable_fair_low": Decimal("1450000"),
        "comparable_fair_high": Decimal("1650000"),
    }


class RiskTests(unittest.TestCase):
    def test_inventory_contradiction_and_missing_promised_model_home_trigger_wait(self):
        findings = detect_red_flags(
            [
                fact("official_unsold_units", 72, EvidenceGrade.A),
                fact("sales_last_unit_claim", True, EvidenceGrade.D),
                fact("official_model_home_commitment", True, EvidenceGrade.A),
                fact("model_home_available", False, EvidenceGrade.C),
            ]
        )
        assessment = recommend(
            values=value_ranges(),
            findings=findings,
            objective="owner_occupation",
        )

        self.assertEqual("wait", assessment.recommendation)
        self.assertIn("inventory_claim_conflict", assessment.veto_codes)
        self.assertIn("unavailable_promised_product_evidence", assessment.veto_codes)
        self.assertEqual(value_ranges(), assessment.value_ranges)

    def test_off_escrow_payment_is_walk_away_veto(self):
        findings = detect_red_flags(
            [fact("payment_outside_escrow", True, EvidenceGrade.A)]
        )
        assessment = recommend(value_ranges(), findings, "owner_occupation")
        self.assertEqual("walk_away", assessment.recommendation)
        self.assertIn("payment_outside_escrow", assessment.veto_codes)

    def test_forum_complaint_does_not_establish_official_violation(self):
        findings = detect_red_flags(
            [fact("developer_forum_complaint", True, EvidenceGrade.D)]
        )
        self.assertNotIn("official_developer_penalty", [item.code for item in findings])
        self.assertTrue(any(item.code == "uncorroborated_reputation_signal" for item in findings))
        self.assertFalse(any(item.decisive for item in findings))

    def test_official_penalty_raises_risk_without_becoming_automatic_project_fact(self):
        findings = detect_red_flags(
            [
                fact("developer_official_penalty", True, EvidenceGrade.A),
                fact("parent_brand_forum_complaint", True, EvidenceGrade.D),
            ]
        )
        codes = [item.code for item in findings]
        self.assertIn("official_developer_penalty", codes)
        self.assertNotIn("official_project_company_penalty", codes)

    def test_confidence_requires_category_coverage_and_respects_source_grade(self):
        evidence = [
            fact("official_inventory", 72, EvidenceGrade.A, category="inventory"),
            fact("field_model_home", False, EvidenceGrade.C, category="product"),
        ]
        confidence, missing = calculate_confidence(
            evidence,
            ("inventory", "product", "transactions", "rent"),
        )
        self.assertEqual("low", confidence)
        self.assertEqual(("transactions", "rent"), missing)

    def test_no_veto_uses_price_gap_for_negotiation(self):
        assessment = recommend(value_ranges(), (), "owner_occupation", confidence="high")
        self.assertEqual("negotiate", assessment.recommendation)
        self.assertEqual("high", assessment.confidence)
        self.assertEqual((), assessment.decisive_findings)


if __name__ == "__main__":
    unittest.main()
