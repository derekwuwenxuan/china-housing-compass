# China housing data sources

Research current data because prices, policies, rates, inventories and project status change.

## Source hierarchy and evidence grades

- **A — primary official:** government housing/transaction platform, planning approval, land registry/auction, statistics bureau, court/credit/penalty registry, official policy, permit and regulated disclosure.
- **B — attributable professional/primary commercial:** developer corporate filing, listed-company disclosure, bank/recognized research with documented method, signed or independently verifiable transaction/rent evidence.
- **C — field and platform observation:** dated user site visit, developer quote, saved intermediary listing/rent page, map/travel-time observation. Useful but not equivalent to a completed transaction.
- **D — unverified claim:** salesperson urgency, forum/social comment, anonymous anecdote, uncited aggregate. Use as a research lead only.

Evidence grade measures source strength, not whether the number favors buying. “Official” is not self-authenticating: when only a user's paraphrase is available and the underlying official page/document cannot be inspected, use grade C pending verification or state “claimed A, unverified.” Upgrade only after matching exact source, identity, scope and date.

## Official-first collection checklist

For new homes collect official project identity, permit, buildings/units released, sold/unsold, filing/recorded prices, escrow, delivery/acceptance filings, land parcel, transaction consideration, area/FAR and planning/infrastructure approvals.

For parcel history and environmental legacy, collect cadastral and land-transfer records, historical planning maps, environmental-impact documents, official contaminated-land lists, remediation and acceptance reports, industrial-enterprise records, government gazetteers, historical maps or aerial imagery, and official flood/drainage records. Match every finding to an explicit geographic scope. Read [parcel-history-and-cultural-acceptance.md](parcel-history-and-cultural-acceptance.md) before applying these sources.

For the city/submarket collect up to five years of:

- official new-home and resale indices;
- transaction units/area and, when lawfully available, prices;
- new permits, supply, remaining comparable inventory and absorption;
- resale listings, price cuts, days on market and transaction volume;
- comparable asking/contract rents and rental supply;
- land supply, floor land price, failed/withdrawn auctions;
- population inflow/outflow, age/household formation, income and employment;
- mortgage/LPR conditions, purchase restrictions, tax and housing policy;
- operating, building and approved infrastructure.
- distinct judicial-auction assets, re-auctions, successful/failed/withdrawn outcomes and price evidence.

If a project has less history, use its available history plus mature comparable communities and the submarket/city series. Never reconstruct missing years from a two-point trend.

## Resale and rental acquisition ladder

For full due diligence, use the following order and preserve every attempt:

1. Use official or independently verifiable records for completed transactions when lawfully available.
2. Attempt both Lianjia and Beike as the primary intermediary sources for resale listings, platform transaction leads, asking/contract rents, price cuts, days on market and visible stock.
3. Use Fang, Anjuke, 58 and other intermediaries as corroborating sources or to fill a named coverage gap. Never silently substitute an easier-to-crawl source for an unattempted or inaccessible Lianjia/Beike source.
4. Use AnySearch for public-web discovery, relevant vertical-domain search and URL extraction. Treat snippets as leads unless the underlying record is inspectable; never place private or sensitive user data in a search query.
5. Use an available browser capability or Computer Use for a normally visible dynamic page. When access depends on the user's already logged-in session, request explicit authorization first. Read only content the user can normally view. Never collect credentials, automate login, bypass a challenge/platform control or access private content.
6. If a source remains unavailable, store the attempted method, date and exact coverage gap. Do not manufacture or relabel replacement evidence.

Label the exact platform and record type. A platform “成交” field still requires method/scope review and should not be called government data. Separate listing, platform-reported transaction, independently verified transaction, asking rent and contract rent. Deduplicate copied/cross-posted listings using available community, area, floor, layout, price, photos/description and listing identifiers before calculating counts or distributions.

For both Lianjia and Beike, capture the **asking-price distribution** and the **platform-reported transaction distribution** separately. When the underlying comparable sample is adequate, report mean, median and lower quantile, sample count, inclusion window and matching rules. Do not substitute a platform's unlabeled community headline average for an inspectable sample, and do not average mismatched area, age, floor, fit-out, tenure or transaction periods.

When the user supplies an intermediary screenshot, follow [platform-screenshot-evidence.md](platform-screenshot-evidence.md). Use grade C and `user_supplied_screenshot` unless the underlying records are independently verified. Preserve an undisclosed sample count as unknown, keep asking and transaction aggregates separate, and request item-level records before using a conflicting aggregate as a comparable anchor.

## Platform coverage and confidence

Full due diligence must include a platform coverage matrix with: platform, metric/record type, access mode, attempted/obtained status, raw and deduplicated sample counts, observed/retrieved dates, freshness and caveat/failure. Medium or high platform confidence requires usable, metric-matched evidence from at least two independent intermediary platforms unless a stronger official or independently verified dataset replaces that exact metric. Two brand names backed by the same copied listing are not independent evidence.

## Judicial-auction and bank-appraisal evidence

Use official court disclosures and the court-designated auction page as the primary judicial-auction sources. At project/community and submarket level, count **distinct assets** as well as auction events, because one asset can be listed repeatedly. Record appraisal price, opening bid, winning bid, successful/failed/withdrawn outcome, re-auction sequence, dates, building area and match quality. Report the failed-auction rate only with an explicit denominator and time window.

Before using a judicial-auction discount, check occupancy and eviction, title/share, lease, mortgage/seizure, tax/fee/arrears, condition, viewing access, payment deadline and other special terms. Compare the winning unit price with a matched ordinary-market transaction or credible comparable range; a low winning bid caused by legal or possession defects is not the ordinary resale floor. Do not treat an opening bid or stale appraisal as a completed sale.

Treat a **bank appraisal** as its own price type. Record lender, qualified appraiser when shown, valuation purpose, effective date, inspection status, building/land area basis, assumptions, restrictions and report identifier. A current inspectable report or independently verifiable lender valuation may be grade B; a salesperson's or borrower's oral “bank value” is grade C/D and must not be promoted. Bank appraisal is collateral/risk evidence, not a guaranteed loan amount, transaction price or price floor. Keep personal appraisal reports and borrower information private.

Treat Xiaohongshu, Douyin, Weibo, Zhihu, Bilibili, forums and comparable social sources as attributed samples. Use them to discover verification questions and marketability concerns, not to establish official violations, transactions, contamination or a representative consensus. Follow the access, sampling, privacy and grade rules in [social-media-and-comments.md](social-media-and-comments.md).

## China-first outlook inputs

Use official policy text and implementation evidence rather than slogans. For a one-to-three-year outlook, collect national/local housing, credit, tax, urban-renewal and land-supply policy; GDP, employment, income and confidence indicators; rates and mortgage availability; population, births, marriage, household formation, ageing and youth tenure preferences; price-to-income and household leverage; new-home releases, delivery waves, unsold completed stock, resale listings/transactions, absorption and land; local-government finance; and funded/approved/operating infrastructure. Preserve the forecast date and publication horizon of every outlook input.

Treat Kondratiev or other long-wave cycle claims as low-weight contextual narratives, not grade-A forecasts or standalone price evidence. Do not let them override current Chinese policy, demographics, affordability, supply, transactions, cash flow or project-specific evidence.

## Freshness and conflict

Store observed_on and retrieved_on separately. Prefer a newer record only when its scope and metric match. Show conflicts rather than silently selecting the convenient number. If a page is blocked or its structure changes, retain old evidence as stale and report the refresh failure.
