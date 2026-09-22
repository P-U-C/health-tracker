# Public Audit Note

Date: 2026-09-22

This repository has been opened for external product/design/security review of the health-tracker architecture and iOS app direction.

## What Auditors Can Review

- Product direction and iOS companion brief: `docs/ios_app_public_brief.md`
- Existing dashboard specification: `docs/dashboard_spec.md`
- Product architecture: `docs/product_architecture.md`
- Data normalization and ingestion design: `docs/phase1_normalization.md`, `docs/phase2_pipe.md`
- Protocol/playbook logic: `playbook/`
- API/backend implementation: `api/`, `core/`, `ingest/`, `jobs/`
- Schema and source contracts: `schema/schema.sql`, `data/templates/`, `config/`

## What Is Intentionally Not In Git

The repository is public for architecture review, not as a dump of private raw health material. The following are intentionally ignored or local-only:

- `.env` and runtime secrets
- `data/health.duckdb`
- raw DEXA report text/PDFs under `data/dexa/raw/`
- BodyStats session artifacts under `data/imports/`
- generated exports under `data/exports/`
- raw genome files
- raw Claude/ChatGPT health conversations

The checked-in CSVs and playbooks are the sanitized development package used to build the health-tracker system. Reviewers should treat the project as sensitive health-adjacent software even though raw private artifacts are not published.

## Current Product Guidance

The current web dashboard is too information-dense for daily use. The recommended direction is a native iOS companion focused on:

1. Today: phase, progress, not-done list, active tripwire, one next action.
2. Progress: calm trend views with source/provenance.
3. Tripwires: deterministic rules with evidence, action, and resolution condition.
4. Capture: voice/text logging in the user's natural terse health language.
5. Context: Claude/ChatGPT-ready context packet export before any live chat-sync integration.

See `docs/ios_app_public_brief.md` for the full public brief.
