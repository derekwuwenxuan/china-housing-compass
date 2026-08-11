# Valuation methodology

Keep units explicit and use Decimal arithmetic.

## Price and comparables

```text
unit price = total price / building area
new-to-resale premium = new-home comparable unit price / resale comparable unit price - 1
```

Build a range from verified transactions first. Adjust for date, exact micro-location, floor, orientation, view, age, fit-out, garden rights, area basis, taxes, vacancy and liquidity. Show each adjustment. Listings measure seller expectations and supply, not closed value. Filing price is a regulatory price type, not necessarily the net paid or resale price.

For each sufficiently matched Lianjia/Beike sample, show the asking-price and platform-reported transaction distributions separately. Prefer median and lower quantile alongside the mean because small, duplicated or high-end-skewed samples can distort averages. State sample size, time window, inclusion rules and whether the displayed platform aggregate could be independently reconstructed.

For aggregate-only user screenshots, follow [platform-screenshot-evidence.md](platform-screenshot-evidence.md). Multiplying the displayed aggregate by the target area produces only an `area-equivalent scenario`. If the aggregate materially conflicts with other price lenses and the underlying sample cannot be inspected, mark the affected comparable lens and dual-anchor result `insufficient_evidence` rather than converting the aggregate into an exact fair value or floor.

## Judicial-auction and appraisal lenses

```text
judicial-auction winning discount = winning unit price / matched ordinary-market unit price - 1
failed-auction rate = failed auction events / concluded auction events in the stated scope/window
```

Also show distinct auctioned assets, successful assets and repeat-auction events so one property is not counted as multiple distressed homes. Use a judicial-auction result only after adjusting or excluding occupancy/eviction, title, lease, mortgage/seizure, taxes/arrears, condition, viewing and accelerated-payment effects. The court appraisal and opening bid are reference price types, not completed prices.

Show bank appraisal as a separate lens with effective date, purpose, area basis, inspection, assumptions and restrictions. Do not average it into market transactions or treat it as a guaranteed floor. Use it as corroboration when current and inspectable; explain conflicts with listings, verified transactions, rent support and judicial auctions.

## Rental lens

```text
gross yield = monthly rent × 12 / all-in cost
net yield = (monthly rent × 12 - vacancy - repairs - owner costs - taxes) / all-in cost
rent-supported price = monthly rent × 12 / required yield
```

Give a range across verified comparable rents and justified yield scenarios. Show whether rent is contract, observed asking, platform estimate or user assumption.

## Dual-anchor alignment

Compare the independently constructed comparable-market fair range with the rent-supported range. Report `dual-anchor alignment` as exactly one of:

- `aligned` — the evidence-backed ranges overlap materially;
- `diverging` — they do not overlap or require unsupported assumptions to meet;
- `insufficient_evidence` — either lens lacks enough current, deduplicated or comparable evidence.

When low-price current Lianjia/Beike comparables and the rent-supported range align, the overlap is a stronger investment/negotiation anchor. It is not a guaranteed bottom, liquidation price or promise that prices cannot fall further. For owner occupation, separately show the price of personal utility, replacement options and affordability; do not automatically use the rental anchor as the purchase ceiling.

## Affordability

```text
price-to-income = all-in home price / annual household disposable income
mortgage burden = annual principal and interest / annual after-tax household income
```

All-in price includes transaction tax/fees, agent fee, fit-out, finance and necessary immediate works. Also show down payment, loan amount, rate, term, other debt, stable monthly surplus and emergency reserve. If rate, term or cash-flow inputs are missing, do not invent a mortgage payment.

## Supply and liquidity

```text
absorption rate = sold units / released units
inventory months = comparable available inventory / recent monthly transactions
```

Keep project inventory, submarket new-home inventory and resale listings separate. A salesperson's scarcity claim requires exact building/unit and official status verification.

## Range construction

Return at least:

1. verified comparable fair range;
2. rent-supported range;
3. delivery scenario range for presales;
4. risk-adjusted maximum purchase price today;
5. conditional downside and severe-stress loss rates.
6. judicial-auction and bank-appraisal cross-checks when usable.

Do not average incompatible price types. Show the dual-anchor alignment state rather than averaging the two ranges into a false single value. When a lens lacks evidence, label it unavailable; do not backfill it from another lens.
