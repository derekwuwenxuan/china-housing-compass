"""Delivery-date scenarios for presale and completed Chinese homes."""

from dataclasses import replace
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Mapping, Sequence, Tuple

from .models import ScenarioInput, ScenarioResult, ValidationError, decimal_value


MONEY_QUANTUM = Decimal("0.01")
RATIO_QUANTUM = Decimal("0.0001")
STANDARD_SCENARIOS = ("upside", "base", "downside", "stress")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _raw_delivery_value(item: ScenarioInput) -> Decimal:
    value = decimal_value(item.current_comparable_value, "current_comparable_value")
    for label, factor in item.factors:
        value *= decimal_value(factor, f"factor:{label}")
    return value


def calculate_maximum_purchase_price(item: ScenarioInput) -> Decimal:
    """Discount delivery value to today and subtract each explicit cost once."""

    delivery_value = _raw_delivery_value(item)
    required_return = decimal_value(item.required_return, "required_return")
    years = decimal_value(item.years_to_delivery, "years_to_delivery")
    discount_factor = (Decimal("1") + required_return) ** years
    present_value = delivery_value / discount_factor
    maximum = (
        present_value
        - decimal_value(item.purchase_costs, "purchase_costs")
        - decimal_value(item.financing_costs, "financing_costs")
        - decimal_value(item.risk_reserve, "risk_reserve")
    )
    return _money(maximum)


def calculate_delivery_value(item: ScenarioInput) -> ScenarioResult:
    """Calculate a fully disclosed scenario result without assigning probability."""

    labels = tuple(label for label, _ in item.factors)
    values = tuple(decimal_value(value, f"factor:{label}") for label, value in item.factors)
    return ScenarioResult(
        name=item.name,
        delivery_value=_money(_raw_delivery_value(item)),
        maximum_purchase_price_today=calculate_maximum_purchase_price(item),
        applied_factors=labels,
        factor_values=values,
    )


def calculate_delivery_loss_rate(all_in_cost: Any, delivery_net_value: Any) -> Decimal:
    """Return conditional delivery loss relative to the buyer's all-in cost."""

    cost = decimal_value(all_in_cost, "all_in_cost")
    net_value = decimal_value(delivery_net_value, "delivery_net_value")
    if cost <= 0:
        raise ValidationError("all_in_cost must be greater than zero")
    if net_value < 0:
        raise ValidationError("delivery_net_value cannot be negative")
    return ((cost - net_value) / cost).quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)


def run_standard_scenarios(
    base_input: ScenarioInput,
    factors: Mapping[str, Sequence[Tuple[str, Decimal]]],
) -> Dict[str, ScenarioResult]:
    """Run required scenarios plus caller-supplied delay or quality cases.

    The mapping must explicitly provide upside, base, downside and stress factor
    sets. Extra rows such as ``delay`` and ``quality_dispute`` are preserved in
    caller order. No probabilities are inferred.
    """

    missing = [name for name in STANDARD_SCENARIOS if name not in factors]
    if missing:
        raise ValidationError("missing standard scenarios: " + ", ".join(missing))

    ordered_names = list(STANDARD_SCENARIOS)
    ordered_names.extend(name for name in factors if name not in STANDARD_SCENARIOS)
    results: Dict[str, ScenarioResult] = {}
    for name in ordered_names:
        if not name.strip():
            raise ValidationError("scenario name is required")
        item = replace(base_input, name=name, factors=tuple(factors[name]))
        results[name] = calculate_delivery_value(item)
    return results
