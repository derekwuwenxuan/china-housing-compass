# User-supplied intermediary screenshot evidence

Read this reference when a user supplies a Lianjia, Beike or other intermediary screenshot containing a community price, transaction label, listing count, rent or trend chart.

## Classify before calculating

Use `user_supplied_screenshot` as the access mode. A screenshot-derived platform aggregate is grade C unless its underlying records are independently verified. It is not government data, an independently verified completed transaction or a professional appraisal merely because the app labels it “成交均价.”

Record only the visible, decision-relevant facts:

- platform and visible metric label;
- project/community and geographic scope, with identity confidence;
- price type, RMB value and period shown;
- observed date shown by the app and retrieval/supply date;
- access mode and source locator;
- `sample_count: unknown` when the screenshot does not disclose it;
- whether underlying records and methodology are inspectable;
- crop/context limitations and conflicts with other evidence.

If exact community identity depends on the user's context rather than visible screenshot text, say so. Do not promote inferred identity to verified identity.

## Keep price types separate

Store the **asking average** and **platform-reported transaction average** as separate evidence rows. Do not blend either with verified transactions, filing prices, court-auction results, bank appraisals or rents.

A chart tooltip rounded to one decimal unit and a more precise headline on the same screen are two presentations of one source, not independent records. Preserve the more precise visible value for calculation and the rounded display as a presentation note; do not double-count them.

## Aggregate-only calculation boundary

When the screenshot supplies only a unit-price aggregate, the permitted translation is:

```text
area-equivalent scenario = displayed aggregate unit price × exact property area
```

Label the output `area-equivalent scenario`. It is not an exact unit valuation, a matched comparable, proof of a completed sale, a liquidation value or a price floor. Do not adjust an aggregate-only value for floor, orientation, condition, tenure, garden, fit-out or taxes without inspectable supporting samples.

Before promoting a platform aggregate into a comparable-market anchor, request the sample count and per-record transaction date, area, layout, floor, total price, unit price and transaction nature. Also request the inclusion window and platform methodology when available.

## Conflict gate

Show the relative gap between the asking average and platform-reported transaction average, and compare both with current listings, verified rents, court-auction results and appraisals without averaging incompatible price types.

If the aggregate would materially change a deposit or purchase decision but the sample count, composition or underlying records remain unavailable:

1. preserve the conflict rather than selecting the convenient number;
2. mark the affected comparable lens and dual-anchor result `insufficient_evidence`;
3. request the missing transaction detail before using the aggregate as the central fair-value anchor;
4. recommend **wait** when the unresolved aggregate is decisive to the deposit decision.

An unresolved aggregate does not force **wait** when independent, matched evidence already supports the decision. It also does not justify an automatic buy, walk-away decision, exact bottom or crash prediction.

Do not automatically count Lianjia and Beike as independent corroboration when the visible records may be duplicated, licensed from the same source or otherwise structurally dependent. Explain the dependence and lower confidence until item-level independence can be checked.

## Privacy and local tracking

Extract minimized aggregates and provenance into local tracking. Do not copy a raw screenshot into the public repository or public-safe database when it contains account controls, notification counts, agent names, phone/contact details, usernames, avatars or other private-session context. Store `raw_capture_retained: false` and a non-public local locator when a reproducible pointer is needed.

On refresh, append the new screenshot-derived observation. Never overwrite an older value. If later per-record evidence becomes available, append the stronger evidence, link it to the earlier aggregate and explain whether it confirms, narrows or contradicts the earlier scenario.

## Common mistakes

| Mistake | Correct treatment |
|---|---|
| Calling a platform “成交均价” a government transaction price | Keep the platform label and grade C until underlying records are verified |
| Multiplying area by the aggregate and calling it fair value | Call it an area-equivalent scenario |
| Treating an unknown sample count as zero or one | Store `sample_count: unknown` |
| Choosing the lowest visible number as the bottom | Preserve conflicts and apply the evidence gate |
| Publishing the supplied screenshot | Store minimized facts; keep raw private-session material local |
| Counting two dependent platforms as confirmation | Deduplicate and disclose structural dependence |
