# Independent review and local verification

Status: completed October 12, 2026. The reviewer rechecked remediations and reported no remaining local blockers.

## Findings addressed

- Known differing part numbers and persistent reject decisions constrain whole clusters, including pairs omitted by candidate generation.
- Null parts remain unknown; manufacturer/source/region are validated and numeric load indices are canonical integers.
- All duplicate source identities quarantine; bounded batches/buckets prevent unbounded comparisons.
- Revision CAS, stable canonical IDs, consistent master/crosswalk versioning and idempotent publication are tested.
- Cloud staging limits collection before transfer, deterministically selects latest steward revisions and rejects conflicting ties.
- Publication bootstrap and diagram labels match the globally unique source-key contract.

## Verification evidence

- Aggregate suite: 104 Python tests passed; one opt-in live Snowflake test skipped.
- Eight JavaScript tests passed. Aggregate backend statement coverage: 96.69% against a 90% minimum.
- Ruff lint/format, strict mypy, ESLint and Prettier passed.
- Existing architecture invariants and all four new local/reference graphs passed endpoint/node-clearance checks. Ten new native SVG files parse and match their builders.
- Native HTTP smoke exercised all three apps, master publication, beauty quality/metrics, tire refinement/scope and all 71 evidence downloads.
- Both source ZIPs were separately extracted and run with hashed runtime dependencies and a non-editable wheel in a fresh Python environment. No Docker, Node or cloud account was needed for that runtime verification.
- Browser checks covered steward approval, clean publication, beauty SQL answers and citations, selected-node arrows, desktop layouts and a 390px mobile viewport.
- Captioned two-minute rendered walkthroughs use actual synthetic evaluation outputs. Their posters and captions were visually checked.
- Pre-commit/pre-push hooks and CI include the two new engines, evidence checks and native startup. CI remains prepared rather than remotely executed.

## Boundaries

This is an independent demonstration with synthetic records. No original client code, dataset or internal slide image is distributed. Local identities simulate roles rather than production authentication. Snowflake/Azure/Databricks cloud scaffolds have not been executed; learned embeddings and cloud model serving are reference replacements. Original client outcomes are user-provided facts and are separate from local evaluation. Production shared state, regional entitlements, source connectors, scale and cloud costs require separate implementation/verification.

One non-blocking Starlette/HTTPX test-client deprecation warning remains; the locked versions pass the suite.

## Standalone repository verification

The split was verified on October 12, 2026 using a fresh non-editable Python install and npm ci. 25 Python tests passed with 98.29% coverage; the optional live tire cloud test remains skipped. Formatting, lint, strict types, JavaScript architecture tests, scoped source/archive checks, regenerated API/evaluation fingerprints and native HTTP startup/download checks passed. GitHub Actions results are reported separately after pushing.
