---
status: canonical
last_verified: 2026-03-13
---

# Documentation Frontmatter Standard

Purpose: keep new docs classifiable at a glance and avoid competing sources of truth.

## Allowed status values

- `canonical`: current source of truth
- `reference`: useful supporting document, not the first entrypoint
- `compatibility_note`: current only as an alias/transition note
- `historical`: past state, report, or worklog
- `historical_verification`: point-in-time proof or audit record
- `archived`: kept for traceability only

## Minimal template

```yaml
---
status: reference
last_verified: 2026-03-13
related_to:
  - /home/venom/analyse-financiere/docs/ops/README.md
---
```

## Supersession template

Use this when the document should no longer be read as current truth.

```yaml
---
status: historical
last_verified: 2026-03-13
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
  - /home/venom/analyse-financiere/docs/ops/ACTIVE_DOCS_INDEX.md
---
```

## Required status note under the title

After the title, add a short block with:

- what the document is for
- whether it is canonical, reference, compatibility, or historical
- which document wins if there is a conflict

## Rules

1. Any new `docs/ops/*` document must declare a `status`.
2. Dated docs should default to `historical` unless explicitly promoted by an active index.
3. Historical ops docs should be stored under `docs/ops/archive/`, not at the root of `docs/ops/`.
4. Non-core ops guides and secondary runbooks should be stored under `docs/ops/reference/`.
5. Root-level docs under `docs/` should be rare and must be linked from a hub.
6. `docs/ops/*` is the canonical citation path for current operational docs.
7. `docs/operations/*` is historical or physical storage unless a canonical doc says otherwise.
8. `docs/ops/archive/*` is for archived human-readable ops docs kept for traceability.

## Archive placement

Move a doc to `docs/ops/archive/` when at least one is true:

- it describes a past migration state
- it records a completed verification or recovery event
- it documents a replaced orchestration model
- it exists only for backward compatibility
