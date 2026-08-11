"""Pure Decimal valuation formulas for China Housing Compass.

Monetary results use RMB and are rounded to fen. Ratios retain four decimal
places so callers can format them as percentages without losing precision.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .models import ValidationError, decimal_value


MONEY_QUANTUM = Decimal("0.01")
RATIO_QUANTUM = Decimal("0.0001")


def _number(value: Any, name: str, *, allow_zero: bool = True) -> Decimal:
    result = decimal_value(value, name)
    if result < 0 or (not allow_zero and result == 0):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise ValidationError(f"{name} must be {qualifier}")
    return result


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _ratio(value: Decimal) -> Decimal:
    return value.quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)


def chargeable_gfa(land_area_sqm: Any, far: Any) -> Decimal:
    """Return chargeable gross floor area: land area x floor-area ratio."""

    area = _number(land_area_sqm, "land_area_sqm", allow_zero=False)
    floor_area_ratio = _number(far, "far", allow_zero=False)
    return area * floor_area_ratio


def floor_land_price(total_land_price: Any, land_area_sqm: Any, far: Any) -> Decimal:
    """Return floor land price in RMB per square metre of chargeable GFA."""

    total = _number(total_land_price, "total_land_price")
    return _money(total / chargeable_gfa(land_area_sqm, far))


def land_to_home_price_ratio(floor_price: Any, home_sale_unit_price: Any) -> Decimal:
    """Return the land-to-home-price ratio from the first video framework."""

    land = _number(floor_price, "floor_price")
    home = _number(home_sale_unit_price, "home_sale_unit_price", allow_zero=False)
    return _ratio(land / home)


def listing_unit_price(total_price: Any, area_sqm: Any) -> Decimal:
    """Return quoted or transacted unit price in RMB per square metre."""

    total = _number(total_price, "total_price")
    area = _number(area_sqm, "area_sqm", allow_zero=False)
    return _money(total / area)


def gross_rental_yield(monthly_rent: Any, all_in_cost: Any) -> Decimal:
    """Return annual gross rent divided by the all-in acquisition cost."""

    rent = _number(monthly_rent, "monthly_rent")
    cost = _number(all_in_cost, "all_in_cost", allow_zero=False)
    return _ratio((rent * Decimal("12")) / cost)


def net_rental_yield(
    monthly_rent: Any,
    all_in_cost: Any,
    annual_vacancy: Any = 0,
    annual_repairs: Any = 0,
    annual_owner_costs: Any = 0,
    annual_taxes: Any = 0,
) -> Decimal:
    """Return annual rent after recurring costs divided by all-in cost."""

    rent = _number(monthly_rent, "monthly_rent")
    cost = _number(all_in_cost, "all_in_cost", allow_zero=False)
    deductions = sum(
        (
            _number(annual_vacancy, "annual_vacancy"),
            _number(annual_repairs, "annual_repairs"),
            _number(annual_owner_costs, "annual_owner_costs"),
            _number(annual_taxes, "annual_taxes"),
        ),
        Decimal("0"),
    )
    return _ratio(((rent * Decimal("12")) - deductions) / cost)


def rent_supported_price(monthly_rent: Any, target_yield: Any) -> Decimal:
    """Reverse annual rent into a price supported by the target gross yield."""

    rent = _number(monthly_rent, "monthly_rent")
    yield_rate = _number(target_yield, "target_yield", allow_zero=False)
    return _money((rent * Decimal("12")) / yield_rate)


def new_to_resale_premium(new_home_unit_price: Any, resale_unit_price: Any) -> Decimal:
    """Return the percentage premium of a new home over a resale comparable."""

    new_price = _number(new_home_unit_price, "new_home_unit_price")
    resale_price = _number(resale_unit_price, "resale_unit_price", allow_zero=False)
    return _ratio((new_price / resale_price) - Decimal("1"))


def price_to_income_ratio(all_in_price: Any, annual_household_income: Any) -> Decimal:
    """Return all-in home price divided by annual household income."""

    price = _number(all_in_price, "all_in_price")
    income = _number(annual_household_income, "annual_household_income", allow_zero=False)
    return _ratio(price / income)


def mortgage_burden_ratio(monthly_payment: Any, annual_after_tax_income: Any) -> Decimal:
    """Return annual mortgage payments as a share of after-tax annual income."""

    payment = _number(monthly_payment, "monthly_payment")
    income = _number(annual_after_tax_income, "annual_after_tax_income", allow_zero=False)
    return _ratio((payment * Decimal("12")) / income)


def absorption_rate(sold_units: Any, released_units: Any) -> Decimal:
    """Return sold units divided by released units."""

    sold = _number(sold_units, "sold_units")
    released = _number(released_units, "released_units", allow_zero=False)
    if sold > released:
        raise ValidationError("sold_units cannot exceed released_units")
    return _ratio(sold / released)


def inventory_months(inventory_units: Any, recent_monthly_transactions: Any) -> Decimal:
    """Return months required to clear inventory at the recent transaction pace."""

    inventory = _number(inventory_units, "inventory_units")
    transactions = _number(
        recent_monthly_transactions,
        "recent_monthly_transactions",
        allow_zero=False,
    )
    return _ratio(inventory / transactions)
