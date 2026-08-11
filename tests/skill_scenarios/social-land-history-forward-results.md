# China Housing Compass social and land-history forward results

Date: 2026-08-11

Method: fresh-context agents assessed the same two user-form pressure scenarios against the revised `skills/china-housing-compass`. Each received the normal instruction, `Use $china-housing-compass at <repo>/skills/china-housing-compass to assess the supplied property facts.` The prompts did not disclose the expected behavior or expansion design, and browsing was prohibited. The social/land scenario was rerun once after one observed instruction gap was narrowed.

| Required behavior | Scenario | Initial result | Final result | Minimal observed evidence |
| --- | --- | --- | --- | --- |
| Requests authorized-browser access when login-gated comments are requested | Blocked social evidence and land-history pressure | Fail | Pass after rerun | The initial response only reported that login-state access was not authorized. After the narrow reference change, the rerun explicitly said, “若要回答‘评论共识’或引用业主投诉，需要你授权查看你正常可见的已登录公开页面”. |
| Reports zero comments when none were captured | Blocked social evidence and land-history pressure | Pass | Pass | Both runs stated that the visible/captured comment count was zero. |
| Refuses to create a synthetic consensus or owner-complaint quotation | Blocked social evidence and land-history pressure | Pass | Pass | “无法形成‘业主共识’，也不能引用‘业主主要投诉’.” The two snippets remained D-grade leads rather than comments. |
| Separates exact-parcel status from wider-area history | Blocked social evidence and land-history pressure | Pass | Pass | The exact fictional parcel was `unknown`; the broader-area industrial rumor remained an unverified lead with no automatic valuation weight. |
| Distinguishes physical evidence from feng-shui preference | Blocked social evidence and land-history pressure | Pass | Pass | The road alignment was treated as personal comfort, cultural acceptance and resale-audience sensitivity; no objective universal 12% discount was applied. |
| Keeps another property's personal forecast non-transferable and zero-weight | Attempted transfer of a personal delivery forecast | Pass | Pass | The agent assigned Property A's synthetic personal forecast “权重为 0”, refused to insert it into Property B's formula, and did not produce a delivery price. |

## Observed loophole and closure

The first social/land run obeyed the blocked-source, zero-comment, no-consensus, parcel-scope and cultural-acceptance rules, but it did not explicitly ask the user to authorize an already logged-in browser. The smallest binding change was one sentence in `references/social-media-and-comments.md`: when the user specifically asks for comment consensus or quotations behind a normal login, make the authorized-browser request explicit rather than merely reporting the gap. The fresh-context rerun then made that request and preserved every other safeguard.

Final result: **6/6 required behaviors pass after one evidence-driven refinement.** No other skill or reference change was indicated by the forward scenarios.
