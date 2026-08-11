---
name: china-housing-compass
description: Use when analyzing a Chinese housing market or evaluating a residential purchase with current, source-graded evidence, including city or submarket trends, new-home or resale prices, presale delivery, affordability, supply and demand, developer or social reputation, public comments, parcel and land-use history, environmental legacy, Chinese cultural or feng-shui acceptance, conditional forecasts, exact identity checks, or a local SQLite/HTML housing tracker. Trigger for market outlook, fair value, negotiation ceilings, delivery downside, or buy, wait, and walk-away decisions.
---

# China Housing Compass

Produce Chinese housing-market analysis and home-purchase advice as a reproducible evidence assessment, not a guaranteed bottom-price prediction. Separate what is known now, what is claimed, what is assumed, and what could happen at delivery.

## Choose the workflow

Infer or ask for one mode when it materially changes the work:

1. **Quick valuation** — estimate ranges from supplied evidence and list the evidence still needed.
2. **Full due diligence** — research identity, price, rent, supply, five-year history, a China-first one-to-three-year outlook, developer, delivery, social evidence, parcel history, environment, cultural acceptance, policy and facilities.
3. **Create tracking** — initialize a local database and offline dashboard for a property, submarket and city.
4. **Refresh tracking** — append new snapshots, preserve failed-source history, rebuild the dashboard and explain what changed.

Record the purchase objective: owner occupation, capital preservation, rental income, resale/liquidity, or retirement. Apply stricter liquidity and cash-flow requirements to investment/resale objectives; do not hide affordability risk for owner occupation.

## Required workflow

### 1. Resolve identity before valuation

Confirm the exact city, district, submarket, project/community, phase, building, unit, area basis and property status. For a new home, separately identify developer brand, legal project company, contractor, official project ID, parcel, presale permit and regulated escrow account. Never transfer a parent-brand complaint or penalty to a project company without evidence linking the entities and conduct.

Read [developer-project-risk.md](references/developer-project-risk.md) for entity and red-flag checks.

### 2. Build current evidence

Research current, time-sensitive information when tools are available. Prefer government and official registries for new-home filing, permits, inventory, land, policies, population, income, supply and infrastructure. For resale and rent, attempt both Lianjia and Beike as the first-line intermediary sources in full due diligence. Seek actual transaction records and actual comparable rents separately; never relabel a platform listing or platform-reported transaction as government data or independently verified closing evidence.

Follow this acquisition ladder: official source; Lianjia and Beike; corroborating intermediary; AnySearch public discovery/extraction; then browser or Computer Use for normally visible dynamic pages. Request explicit authorization before using the user's already logged-in session. Never silently substitute Fang, Anjuke, 58 or another easier-to-crawl site for an unattempted or inaccessible primary intermediary. Never send private user data in a search query, request credentials, automate login, defeat a challenge or access private content. Record each attempted source, access mode, result, dates, sample counts and gap in a platform coverage matrix. Medium or high platform confidence requires usable metric-matched evidence from at least two independent intermediary platforms, unless stronger official or independently verified evidence replaces that metric. Deduplicate cross-posted listings before counting them.

For Lianjia and Beike, collect the asking-price distribution and platform-reported transaction distribution separately, including mean, median and lower quantile when sample size permits. Also research project/submarket judicial-auction prices, distinct-asset counts and outcomes, plus any inspectable bank appraisal. Keep platform transactions, court-auction results, appraisals and ordinary verified transactions as different price types with their special conditions disclosed.

For every material input store or show: metric, value and RMB unit, price type, observed date, retrieval date, scope, source URL/title, source grade A–D, and caveat. A user summary that calls a source “official” is not grade A until the actual official page/document, exact identity and date are inspectable; label it grade C pending verification or “claimed A, unverified.” Never blend official filing price, developer quote, listing price, transaction price, appraisal price and rent.

Read [china-data-sources.md](references/china-data-sources.md) before web research or source selection.

When a user supplies a Lianjia, Beike or other intermediary screenshot, read [platform-screenshot-evidence.md](references/platform-screenshot-evidence.md) before extracting, storing or valuing it. Keep asking and platform-reported transaction aggregates separate, record an undisclosed sample count as unknown, minimize private UI data and never promote an aggregate-only screenshot to an exact unit value or price floor.

### 3. Research social, parcel and cultural evidence

For full due diligence, read both [social-media-and-comments.md](references/social-media-and-comments.md) and [parcel-history-and-cultural-acceptance.md](references/parcel-history-and-cultural-acceptance.md). Also read both references before answering any question about social reputation, posts, comments, land history, environmental legacy, contamination, burial or industrial history, cultural acceptance or feng shui.

Follow the social access ladder. When decisive visible public content requires a normal login, request authorized browser access to an already logged-in browser if that capability is available; never assume access. Never request credentials, automate login, bypass a challenge or platform control, or access private content. If comments remain inaccessible, report zero captured comments and the coverage gap; do not invent themes or consensus.

Keep exact parcel, within 500 m, within 1 km and broader-area findings separate. Separate objective physical risk from cultural acceptance and resale-liquidity sensitivity. Do not convert an area-level lead, rumor or cultural concern into parcel fact, scientific harm or a universal price discount. In particular, broader-area burial history has zero default valuation weight and cannot enter a contamination, physical-risk or price-adjustment conclusion without exact-parcel evidence and an evidenced mechanism.

### 4. Classify facilities and claims

Mark each facility as **operating**, **under construction**, **approved**, **conceptual**, or **developer-only claim**. Only operating facilities count at full current utility. Give a developer-only claim zero current realization value. Preserve the user's dated field observation as grade C evidence, without adding private identifiers.

Treat captured comments as comments. If no comments were inspected, report zero captured comments and omit comment synthesis. Do not invent comment counts, wording, themes, sentiment or consensus.

### 5. Run veto checks before price scoring

Pause deposits when official inventory conflicts materially with scarcity language, a promised product/model home cannot be inspected, key garden/area/fit-out rights are absent from the contract, or delivery evidence is inadequate. Walk away from verified off-escrow payment requests, material illegality, or absent essential contractual rights. A severe veto overrides an attractive formula result.

### 6. Calculate separate valuation lenses

Use exact Decimal arithmetic when the bundled `china_housing_compass` package is available; otherwise show all arithmetic and rounding. Apply the three-video formulas and limitations in [three-video-framework.md](references/three-video-framework.md), then the comparable, rent, affordability, supply and premium formulas in [valuation-methodology.md](references/valuation-methodology.md).

Always separate:

- comparable-market fair range;
- rent-supported value range;
- delivery-date scenario values;
- risk-adjusted maximum purchase price today;
- all-in affordability;
- downside and severe liquidity-stress bands.

Report dual-anchor alignment between the comparable-market and rent-supported ranges as **aligned**, **diverging**, or **insufficient_evidence**. Overlap strengthens an investment or negotiation anchor but does not establish a floor. Land cost measures developer cost pressure; it is not a resale floor. An assumed rent is a scenario, not rent evidence. Never call one point the exact, guaranteed or government-protected bottom.

### 7. Forecast conditionally

For presale property, model at least upside, base, downside and severe liquidity stress. Add delay and quality-dispute scenarios when warranted. Disclose city, submarket, project and product factors without double-counting; use delivery time, required return, purchase costs, financing/opportunity cost and a risk reserve. Do not assign probabilities without evidence or mechanically annualize one recent monthly change.

Read [delivery-scenario-model.md](references/delivery-scenario-model.md).

Treat every user forecast as attributed, dated, case-scoped, non-transferable, and zero-weight by default. Use it only as an explicitly labeled scenario for the same property when requested.

### 8. Apply five-year history and a China-first one-to-three-year outlook

Collect up to five years of city, submarket and comparable-community price indices, transactions, resale liquidity, listings, rents, new supply, inventory, absorption and land. If history is missing, state the missing years; do not interpolate or fabricate them. For a new project, supplement short history with mature comparables.

Then build year-1, year-2 and year-3 base, weak and stress paths when evidence permits. Give primary weight to implemented national/local policy, economic and employment outlook, rates and credit, population and household formation, income/affordability and leverage, youth consumption/tenure preferences, new and resale supply, unsold stock, absorption, land, local-government finance, developer delivery capacity and infrastructure realization. Treat Kondratiev or other long-wave cycle narratives only as low-weight context. Treat any user-supplied price or market-direction forecast as an attributed, dated, case-scoped, zero-weight hypothesis unless independent evidence supports a particular scenario; never make it the skill's universal default.

### 9. Return the fixed report

Follow [report-contract.md](references/report-contract.md). Lead with recommendation — **buy**, **negotiate**, **wait**, or **walk away** — plus confidence and decisive conditions. When confidence in the action differs from confidence in the price estimate, show both as **decision confidence** and **valuation confidence**. Include ranges rather than fake precision, all assumptions, missing evidence, source freshness and a deposit checklist.

## Local tracking workflow

Use the toolkit for append-only research and an offline `file://` dashboard when installed. It stores private work locally; never commit `housing.sqlite`, field notes, personal data, downloaded pages or generated private reports to a public repository.

Read [database-and-refresh.md](references/database-and-refresh.md) before initializing, importing or refreshing. For the built-in example only, read [synthetic-river-garden-case.md](references/synthetic-river-garden-case.md).

## Non-negotiable boundaries

- Cite current claims and distinguish observation date from retrieval date.
- State when a source is unavailable, blocked, stale or structurally changed.
- Do not manufacture transactions, rent, five-year history, infrastructure completion, developer violations, forecast probabilities or a precise bottom.
- Do not tell a buyer that land price, filing price, the developer's cost, or a salesperson's “last unit” establishes downside protection.
- Do not recommend a deposit while a decisive verification condition remains unresolved.
