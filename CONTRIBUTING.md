# Contributing to China Housing Compass

Thank you for improving evidence-based Chinese housing research.

## Before opening a change

Open an issue or describe the problem, city and intended evidence type. Keep changes focused. Add a failing test before implementation, then run the complete test suite.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

## Adding a city provider

A city provider should parse caller-supplied public material or use a lawful, documented interface. It must not execute untrusted embedded scripts or rely on unrestricted scraping. Return normalized `EvidenceRecord` rows with exact metric type, value/unit, observed and retrieval dates, source identity, grade, scope and metadata.

Include minimized fixtures that retain only the structure required for testing. Tests must cover normal extraction, project/building identity, inconsistent totals and changed-page failure. A parser must fail clearly instead of reusing stale values as fresh evidence.

## Fixture provenance

Document fixture provenance in the test or adjacent README/comment:

- public source title and URL;
- observation/retrieval date;
- what was minimized or synthetically replaced;
- reuse or licensing boundary;
- whether values are official facts, platform records, field observations or assumptions.

Do not call platform listings government transactions. Do not upgrade a paraphrased “official” claim to grade A without an inspectable primary record.

For social, comment, parcel-history and environmental fixtures, use synthetic records by default. If a real public item is necessary, keep only the minimum permitted excerpt or structure needed for the test and document the platform/source, stable locator or URL, observed/retrieved dates, access mode, minimization, license or reuse boundary, and any synthetic replacement. Never commit a copied post collection, complete comment thread or unexplained screenshot.

Keep synthetic records visibly labeled so they cannot be mistaken for observed owners, residents, transactions or environmental findings. Preserve positive, negative and dissenting fixture cases without inventing a platform consensus.

## Platform access boundaries

Use content available on the public web first. An interactive assessment may request user-authorized access to visible public content in an already logged-in browser, but contributors and fixtures must never collect credentials, automate login, bypass CAPTCHA or anti-bot controls, access private content, or serialize cookies, tokens and browser/session state. Preserve blocked-source attempts and zero-comment outcomes as testable states.

## Privacy and security

Never commit private databases, personal contact details, usernames, precise private visit metadata, raw social captures, raw credentials, browser/session data, unpublished contracts, restricted downloaded pages or generated personal dashboards/reports. Public examples and test fixtures must be explicitly synthetic. Do not anonymize a real buyer's case and publish it as an example: replace the city, project, entities, dates, prices, inventory, rents, observations, sources and conclusions with visibly fictional data. Use the reserved `example.test` domain for synthetic source URLs, and mark synthetic payloads and source metadata explicitly.

Review `git diff --cached` before every public commit. Check filenames, fixture payloads, excerpts, metadata and generated artifacts for personal data, restricted content, credentials and browser state. If private content was accidentally staged, stop and remove it from the commit before pushing; do not merely add it to `.gitignore` after publication.

## Skill contributions

Changes to `skills/china-housing-compass` require baseline or forward-test evidence for any behavioral rule. Keep `SKILL.md` under 500 lines, use imperative instructions and route detailed methodology to the relevant reference. Run the official skill validator before submitting.

## Pull requests

Describe the user-visible outcome, evidence/source implications, tests run and privacy review. By contributing, you agree that your contribution is licensed under the MIT License.
