# Local database and refresh workflow

China Housing Compass uses a local SQLite database with append-only evidence snapshots and self-contained offline HTML.

## Common commands

```bash
china-housing-compass init housing-research
china-housing-compass import housing-research snapshot.json
china-housing-compass status housing-research
china-housing-compass dashboard housing-research
china-housing-compass valuate housing-research PROPERTY_ID --risk-adjusted-max-price RMB_AMOUNT
china-housing-compass refresh housing-research PROPERTY_ID --provider CATEGORY=snapshot.json
```

Use `python3 -m china_housing_compass.cli` if the console entry point is unavailable. Check `--help` for current options.

## Snapshot rules

Each normalized JSON snapshot has schema version, unique snapshot ID, exact property identity, source registry and evidence rows. Each evidence row keeps metric type, value/unit, observed/retrieved dates, source ID, grade, scope and metadata. Re-importing the same snapshot is a no-op; a later dated snapshot appends history.

For resale and rent collection, source/evidence metadata should also keep exact provider/platform, record type, URL or stable locator, access mode, attempted/obtained result, raw and deduplicated sample count, listing fingerprint/deduplication key when available, freshness and caveat/failure. Store separate Lianjia/Beike asking-price and platform-reported transaction distributions, including reconstructible mean/median/lower-quantile inputs where available. Store the platform coverage matrix as dated evidence or run metadata so later refreshes can distinguish “not attempted,” “blocked,” “zero results” and “success.” Attempt both Lianjia and Beike during full due diligence; medium or high platform confidence requires at least two independent intermediary platforms with usable metric-matched evidence unless a stronger official or independently verified dataset replaces that exact metric.

For a user-supplied intermediary screenshot, use `user_supplied_screenshot`, store each visible asking or platform-transaction aggregate as its own evidence row, and store `sample_count: unknown` when it is not disclosed. Keep only minimized metric, value/unit, label, scope, dates, identity confidence, inspectability and caveat fields. Do not serialize the raw screenshot, account UI, notifications, agent/user names, avatar or contact details into the public-safe database. Follow [platform-screenshot-evidence.md](platform-screenshot-evidence.md) for conflict and refresh handling.

For judicial auctions, store court/auction locator, distinct-asset key, event/re-auction sequence, outcome, appraisal/opening/winning prices, area, dates and material occupancy/title/lease/tax/arrears/condition caveats. Keep project/community and submarket counts separately. For bank appraisal, store only minimized non-personal provenance and valuation fields; the report and borrower details remain private local material.

Allowed acquisition descriptions include official/public web, Lianjia/Beike intermediary observation, corroborating intermediary, AnySearch discovery/extraction, public dynamic browser/Computer Use, authorized logged-in browser/Computer Use, `user_supplied_screenshot`, user supplied and unavailable. Never silently substitute another provider: keep the failed primary attempt and the replacement source as separate records. Deduplicate cross-platform copies before aggregate calculations. Never store search queries containing private user data or serialize browser credentials, cookies, tokens or session state.

Never overwrite an older market value in the property master record. Do not erase old official inventory because a rent or web refresh fails.

Use schema version 1 for the original evidence-only format. Use schema version 2 when importing any of these source-linked `research_layers`:

- `social_research_runs` — queries, platform coverage, requested/obtained counts, access mode and failures;
- `social_items` — post-level locator, author/content classification, stance, engagement, commercial markers and summary;
- `social_comments` — parent item, stance, themes, engagement, limited summary and privacy flags;
- `parcel_history_findings` — scoped historical use, active dates, distance/direction and finding state;
- `environmental_findings` — scoped hazard, finding state, remediation/acceptance, residual uncertainty and valuation treatment;
- `cultural_factors` — observable feature, buyer sensitivity, objective counterpart and liquidity treatment.

Register every layer record to a source and stable key. Use only `public_web`, `indexed_snippet`, `authorized_browser`, `user_supplied` or `unavailable` for social access modes. Keep version 1 imports compatible. Append version 2 records by snapshot ID; do not overwrite an earlier observation when content changes or disappears.

## Refresh semantics

- success: all requested providers produced and committed fresh evidence;
- partial: at least one succeeded and one failed;
- failed: none succeeded.

On failure, retain prior evidence and research-layer rows, mark the category stale, store the attempted source/access mode and exact error, and show the last successful timestamp. Preserve unavailable, blocked, deleted and structurally changed source attempts rather than replacing them with guessed content. Rebuild the dashboard only after successful rows and refresh status are committed.

## Privacy and open source

Public repository: code, skill, schemas, synthetic fixtures, minimized permitted excerpts, aggregate examples and provenance documentation.

Keep local/private: `housing.sqlite`, raw social captures, usernames, personal field notes, phone/name/contact data, precise visit metadata, downloaded pages subject to restrictions, snapshots with private content, authorized-browser state, credentials/session tokens, generated reports and dashboards. Never serialize credentials or browser state into a snapshot. The project `.gitignore` must exclude these. Review the staged diff before any public push.
