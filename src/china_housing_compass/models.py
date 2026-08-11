"""Validated domain records used across China Housing Compass."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Tuple


class ValidationError(ValueError):
    """Raised when evidence or valuation input is internally inconsistent."""


class EvidenceGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


SUPPORTED_UNITS = {
    "RMB",
    "RMB/㎡",
    "RMB/month",
    "㎡",
    "count",
    "ratio",
    "index",
    "months",
    "years",
    "date",
    "boolean",
    "text",
}


def decimal_value(value: Any, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise ValidationError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_type: str
    value: Any
    unit: str
    observed_on: date
    retrieved_on: date
    source: str
    grade: EvidenceGrade
    source_id: str = ""
    scope: str = "property"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_type.strip():
            raise ValidationError("evidence_type is required")
        if not self.source.strip():
            raise ValidationError("source is required")
        if self.unit not in SUPPORTED_UNITS:
            raise ValidationError(f"unsupported unit: {self.unit}")
        if self.retrieved_on < self.observed_on:
            raise ValidationError("retrieved_on cannot precede observed_on")
        if not self.scope.strip():
            raise ValidationError("scope is required")


@dataclass(frozen=True)
class PropertyRef:
    city: str
    district: str
    project_name: str = ""
    community_name: str = ""
    submarket: str = ""
    building: str = ""
    unit_name: str = ""
    developer_brand: str = ""
    project_company: str = ""
    official_project_id: str = ""
    parcel_id: str = ""

    def __post_init__(self) -> None:
        if not self.city.strip():
            raise ValidationError("city is required")
        if not self.district.strip():
            raise ValidationError("district is required")
        if not (self.project_name.strip() or self.community_name.strip()):
            raise ValidationError("project_name or community_name is required")

    @property
    def display_name(self) -> str:
        return self.project_name or self.community_name


@dataclass(frozen=True)
class ValuationInput:
    total_price: Decimal
    area_sqm: Decimal
    monthly_rent: Optional[Decimal] = None
    annual_household_income: Optional[Decimal] = None
    owner_costs: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        total_price = decimal_value(self.total_price, "total_price")
        area_sqm = decimal_value(self.area_sqm, "area_sqm")
        owner_costs = decimal_value(self.owner_costs, "owner_costs")
        if total_price <= 0:
            raise ValidationError("total_price must be greater than zero")
        if area_sqm <= 0:
            raise ValidationError("area_sqm must be greater than zero")
        if owner_costs < 0:
            raise ValidationError("owner_costs cannot be negative")
        for name, value in (
            ("monthly_rent", self.monthly_rent),
            ("annual_household_income", self.annual_household_income),
        ):
            if value is not None and decimal_value(value, name) < 0:
                raise ValidationError(f"{name} cannot be negative")


@dataclass(frozen=True)
class ScenarioInput:
    name: str
    current_comparable_value: Decimal
    factors: Sequence[Tuple[str, Decimal]]
    years_to_delivery: Decimal
    required_return: Decimal
    purchase_costs: Decimal = Decimal("0")
    financing_costs: Decimal = Decimal("0")
    risk_reserve: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("scenario name is required")
        labels = [label for label, _ in self.factors]
        if len(labels) != len(set(labels)):
            raise ValidationError("scenario factor labels must be unique")
        if decimal_value(self.current_comparable_value, "current_comparable_value") <= 0:
            raise ValidationError("current_comparable_value must be greater than zero")
        if decimal_value(self.years_to_delivery, "years_to_delivery") < 0:
            raise ValidationError("years_to_delivery cannot be negative")
        if decimal_value(self.required_return, "required_return") <= Decimal("-1"):
            raise ValidationError("required_return must be greater than -1")
        for label, factor in self.factors:
            if not label.strip():
                raise ValidationError("factor label is required")
            if decimal_value(factor, f"factor:{label}") <= 0:
                raise ValidationError("scenario factors must be greater than zero")
        for name, value in (
            ("purchase_costs", self.purchase_costs),
            ("financing_costs", self.financing_costs),
            ("risk_reserve", self.risk_reserve),
        ):
            if decimal_value(value, name) < 0:
                raise ValidationError(f"{name} cannot be negative")


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    delivery_value: Decimal
    maximum_purchase_price_today: Decimal
    applied_factors: Tuple[str, ...]
    factor_values: Tuple[Decimal, ...]


@dataclass(frozen=True)
class RiskFinding:
    code: str
    title: str
    severity: str
    decisive: bool
    evidence_types: Tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class Assessment:
    recommendation: str
    confidence: str
    decisive_findings: Tuple[RiskFinding, ...]
    non_decisive_findings: Tuple[RiskFinding, ...]
    missing_categories: Tuple[str, ...]
    value_ranges: Mapping[str, Any]

    @property
    def veto_codes(self) -> Tuple[str, ...]:
        return tuple(finding.code for finding in self.decisive_findings)
