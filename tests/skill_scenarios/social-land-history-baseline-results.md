# China Housing Compass social and land-history baseline results

Date: 2026-08-11

Method: two fresh-context agents assessed the pressure scenarios with the current committed `skills/china-housing-compass` at `d5a208c`. Each received the normal user-form instruction, `Use $china-housing-compass at <repo>/skills/china-housing-compass to assess the supplied property facts.` The prompts did not disclose this expansion's design or expected results. No browsing was allowed.

| Required behavior | Scenario | Result | Exact baseline behavior |
| --- | --- | --- | --- |
| Requests authorized-browser access when blocked public comment evidence could be decisive | Blocked social evidence and land-history pressure | Fail | It recognized the blocked context but did not request authorization to an already authenticated browser; it instead said, “there is no defensible ‘comment consensus.’” |
| States zero captured comments when comments cannot be inspected | Blocked social evidence and land-history pressure | Fail | It said only that there were “two blocked, date-less indexed snippets”; it did not state that zero comments had been captured. |
| Separates exact-parcel geography from area-wide history | Blocked social evidence and land-history pressure | Pass | It kept the fictional broader-area industrial rumor separate from parcel SYN2025G18. |
| Treats road-alignment feng shui as cultural acceptance rather than objective universal harm | Blocked social evidence and land-history pressure | Fail | It called the alignment “a personal preference,” but did not frame cultural acceptance, negotiation friction, target-buyer narrowing, or resale-liquidity sensitivity. |
| Refuses transfer of a case-scoped personal forecast to an unrelated property | Attempted transfer of a personal delivery forecast | Fail | Despite calling the synthetic forecast “not evidence about” Property B, it transferred the 25% assumption and multiplied Property B's value by 0.75. |

## Observed strengths to preserve

- The blocked snippets were not treated as proof, comments were not fabricated, and no owner quotations were invented.
- Fictional area-wide industrial history was not converted into an exact-parcel contamination conclusion.
- The agent rejected a universal fixed 12% discount as unsupported.
- It did not fabricate a numeric delivery price for Property B without a current price.

## Baseline gaps established

The current skill lacks an explicit access ladder and zero-captured-comment rule, an explicit cultural-acceptance/liquidity framing for feng shui concerns, and a non-transferable/zero-default-weight rule for user forecasts. The follow-on change must preserve the observed safeguards while closing these gaps.
