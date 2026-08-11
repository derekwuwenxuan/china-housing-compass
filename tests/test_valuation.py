from decimal import Decimal
import unittest

from china_housing_compass.models import ValidationError
from china_housing_compass.valuation import (
    absorption_rate,
    chargeable_gfa,
    floor_land_price,
    gross_rental_yield,
    inventory_months,
    land_to_home_price_ratio,
    listing_unit_price,
    mortgage_burden_ratio,
    net_rental_yield,
    new_to_resale_premium,
    price_to_income_ratio,
    rent_supported_price,
)


class ValuationTests(unittest.TestCase):
    def test_video_land_example(self):
        self.assertEqual(Decimal("30000"), chargeable_gfa(Decimal("10000"), Decimal("3")))
        self.assertEqual(
            Decimal("10000.00"),
            floor_land_price(Decimal("300000000"), Decimal("10000"), Decimal("3")),
        )
        self.assertEqual(
            Decimal("0.2500"),
            land_to_home_price_ratio(Decimal("10000"), Decimal("40000")),
        )

    def test_rent_supported_price_and_yields(self):
        self.assertEqual(
            Decimal("1500000.00"),
            rent_supported_price(Decimal("5000"), Decimal("0.04")),
        )
        self.assertEqual(
            Decimal("0.0200"),
            gross_rental_yield(Decimal("5000"), Decimal("3000000")),
        )
        self.assertEqual(
            Decimal("0.0180"),
            net_rental_yield(
                monthly_rent=Decimal("5000"),
                all_in_cost=Decimal("3000000"),
                annual_vacancy=Decimal("3000"),
                annual_repairs=Decimal("1500"),
                annual_owner_costs=Decimal("1500"),
            ),
        )

    def test_synthetic_quote_unit_price(self):
        self.assertEqual(
            Decimal("20000.00"),
            listing_unit_price(Decimal("1760000"), Decimal("88")),
        )

    def test_affordability_supply_and_premium(self):
        self.assertEqual(Decimal("8.0000"), price_to_income_ratio(Decimal("1760000"), Decimal("220000")))
        self.assertEqual(Decimal("0.3600"), mortgage_burden_ratio(Decimal("6600"), Decimal("220000")))
        self.assertEqual(Decimal("0.4000"), absorption_rate(Decimal("48"), Decimal("120")))
        self.assertEqual(Decimal("9.0000"), inventory_months(Decimal("72"), Decimal("8")))
        self.assertEqual(Decimal("0.1000"), new_to_resale_premium(Decimal("22000"), Decimal("20000")))

    def test_invalid_denominators_and_negative_costs_are_rejected(self):
        with self.assertRaises(ValidationError):
            floor_land_price(100, 10, 0)
        with self.assertRaises(ValidationError):
            rent_supported_price(5000, 0)
        with self.assertRaises(ValidationError):
            inventory_months(72, 0)
        with self.assertRaises(ValidationError):
            net_rental_yield(5000, 3000000, annual_repairs=-1)


if __name__ == "__main__":
    unittest.main()
