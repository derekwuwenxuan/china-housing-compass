"""Evidence-bounded red flags, confidence, and purchase recommendations."""

from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence, Tuple

from .models import (
    Assessment,
    EvidenceGrade,
    EvidenceRecord,
    RiskFinding,
    ValidationError,
    decimal_value,
)


GRADE_WEIGHT = {
    EvidenceGrade.A: Decimal("1.00"),
    EvidenceGrade.B: Decimal("0.80"),
    EvidenceGrade.C: Decimal("0.55"),
    EvidenceGrade.D: Decimal("0.25"),
}


def _truthy(records: Sequence[EvidenceRecord], evidence_type: str) -> bool:
    return any(record.evidence_type == evidence_type and record.value is True for record in records)


def _trusted_truthy(records: Sequence[EvidenceRecord], evidence_type: str) -> bool:
    return any(
        record.evidence_type == evidence_type
        and record.value is True
        and record.grade in (EvidenceGrade.A, EvidenceGrade.B)
        for record in records
    )


def _positive(records: Sequence[EvidenceRecord], evidence_type: str) -> bool:
    for record in records:
        if record.evidence_type != evidence_type:
            continue
        try:
            if decimal_value(record.value, evidence_type) > 0:
                return True
        except ValidationError:
            continue
    return False


def detect_red_flags(evidence: Iterable[EvidenceRecord]) -> Tuple[RiskFinding, ...]:
    """Detect only risks supported by the supplied, source-graded evidence."""

    records = tuple(evidence)
    findings = []

    if _positive(records, "official_unsold_units") and _truthy(records, "sales_last_unit_claim"):
        findings.append(
            RiskFinding(
                code="inventory_claim_conflict",
                title="Sales scarcity claim conflicts with official inventory",
                severity="high",
                decisive=True,
                evidence_types=("official_unsold_units", "sales_last_unit_claim"),
                explanation="Do not pay a deposit until the exact unit and official inventory are reconciled.",
            )
        )

    if _truthy(records, "official_model_home_commitment") and _truthy(
        records, "model_home_available"
    ) is False and any(record.evidence_type == "model_home_available" for record in records):
        findings.append(
            RiskFinding(
                code="unavailable_promised_product_evidence",
                title="Promised product evidence is unavailable",
                severity="high",
                decisive=True,
                evidence_types=("official_model_home_commitment", "model_home_available"),
                explanation="Product quality and usable-space claims cannot yet be inspected.",
            )
        )

    if _trusted_truthy(records, "payment_outside_escrow"):
        findings.append(
            RiskFinding(
                code="payment_outside_escrow",
                title="Payment requested outside regulated escrow",
                severity="critical",
                decisive=True,
                evidence_types=("payment_outside_escrow",),
                explanation="Do not transfer funds outside the verified regulatory payment path.",
            )
        )

    if _trusted_truthy(records, "missing_contractual_rights"):
        findings.append(
            RiskFinding(
                code="missing_contractual_rights",
                title="Material buyer rights are absent from the contract",
                severity="critical",
                decisive=True,
                evidence_types=("missing_contractual_rights",),
            )
        )

    if _trusted_truthy(records, "developer_official_penalty"):
        findings.append(
            RiskFinding(
                code="official_developer_penalty",
                title="Developer has a corroborated official penalty",
                severity="high",
                decisive=False,
                evidence_types=("developer_official_penalty",),
                explanation="Verify whether the cited entity, conduct, and project are directly relevant.",
            )
        )

    complaint_types = (
        "developer_forum_complaint",
        "parent_brand_forum_complaint",
    )
    for complaint_type in complaint_types:
        if _truthy(records, complaint_type):
            findings.append(
                RiskFinding(
                    code="uncorroborated_reputation_signal",
                    title="Uncorroborated reputation complaint",
                    severity="medium",
                    decisive=False,
                    evidence_types=(complaint_type,),
                    explanation="Treat as a research lead, not proof of a project-company violation.",
                )
            )

    return tuple(findings)


def calculate_confidence(
    evidence: Iterable[EvidenceRecord], required_categories: Sequence[str]
) -> Tuple[str, Tuple[str, ...]]:
    """Grade confidence from category coverage and the best evidence grade per category."""

    required = tuple(required_categories)
    if not required:
        raise ValidationError("required_categories cannot be empty")
    if len(required) != len(set(required)):
        raise ValidationError("required_categories must be unique")

    best = {}
    for record in evidence:
        category = str(record.metadata.get("category", record.evidence_type))
        weight = GRADE_WEIGHT[record.grade]
        best[category] = max(weight, best.get(category, Decimal("0")))

    missing = tuple(category for category in required if category not in best)
    score = sum((best.get(category, Decimal("0")) for category in required), Decimal("0"))
    score /= Decimal(len(required))
    if not missing and score >= Decimal("0.80"):
        confidence = "high"
    elif score >= Decimal("0.50"):
        confidence = "medium"
    else:
        confidence = "low"
    return confidence, missing


def recommend(
    values: Mapping[str, Any],
    findings: Iterable[RiskFinding],
    objective: str,
    *,
    confidence: str = "medium",
    missing_categories: Sequence[str] = (),
) -> Assessment:
    """Return buy/negotiate/wait/walk-away, with decisive findings overriding price."""

    if not objective.strip():
        raise ValidationError("objective is required")
    if confidence not in ("high", "medium", "low"):
        raise ValidationError("confidence must be high, medium, or low")

    all_findings = tuple(findings)
    decisive = tuple(item for item in all_findings if item.decisive)
    non_decisive = tuple(item for item in all_findings if not item.decisive)

    if any(item.severity == "critical" for item in decisive):
        recommendation = "walk_away"
    elif decisive:
        recommendation = "wait"
    else:
        try:
            asking = decimal_value(values["asking_price"], "asking_price")
            maximum = decimal_value(values["risk_adjusted_max_price"], "risk_adjusted_max_price")
        except KeyError as exc:
            raise ValidationError(f"missing value: {exc.args[0]}") from exc
        if asking <= 0 or maximum <= 0:
            raise ValidationError("asking_price and risk_adjusted_max_price must be greater than zero")

        if confidence == "low":
            recommendation = "wait"
        elif asking <= maximum:
            recommendation = "buy"
        elif asking <= maximum * Decimal("1.15"):
            recommendation = "negotiate"
        else:
            recommendation = "wait"

        if any(item.severity == "high" for item in non_decisive) and recommendation == "buy":
            recommendation = "negotiate"

    return Assessment(
        recommendation=recommendation,
        confidence=confidence,
        decisive_findings=decisive,
        non_decisive_findings=non_decisive,
        missing_categories=tuple(missing_categories),
        value_ranges=values,
    )
