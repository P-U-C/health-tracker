# Health App Public Brief: From Dashboard to iOS Companion

Date: 2026-09-22
Last updated: 2026-09-23 - Food/macros, meal photo, and voice capture slice shipped.
Owner: Chad / zoz
Repo: public GitHub repo `P-U-C/health-tracker` — https://github.com/P-U-C/health-tracker
Local path: `/home/ubuntu/health`
Public audit note: https://github.com/P-U-C/health-tracker/blob/master/docs/public_audit_note.md
Public dashboard surface: `https://health.permanentupperclass.com/dashboard`
Public read-only JSON surface: `https://health.permanentupperclass.com/api/dashboard/overview`
Public mobile Today endpoint: `https://health.permanentupperclass.com/api/mobile/today`
Installable phone web app: `https://health.permanentupperclass.com/app`
Public Claude/ChatGPT context endpoint: `https://health.permanentupperclass.com/api/mobile/context`
Authenticated mobile capture endpoint: `POST https://health.permanentupperclass.com/api/mobile/capture`
Authenticated project-link endpoint: `GET https://health.permanentupperclass.com/api/mobile/links`
Mobile session endpoint: `POST https://health.permanentupperclass.com/api/mobile/session`
Mobile API contract: https://github.com/P-U-C/health-tracker/blob/master/docs/mobile_app_contract.md
SwiftUI scaffold: https://github.com/P-U-C/health-tracker/tree/master/ios/HealthCompanion

This is a public, sanitized design brief. It intentionally excludes secrets, raw DEXA reports, BodyStats session cookies, raw Apple Health exports, Claude/ChatGPT transcripts, and private medical details.

## 1. Product Thesis

The current health dashboard has the right data foundation but the wrong product shape. It exposes too much of the operating system at once. The next surface should be a native iOS app that answers one practical question:

> What should I do, notice, or avoid today to stay on protocol?

The app should feel like a focused blend of Apple Fitness, Apple Health, Eufy, and BodyStats, but with Chad's own health protocol and Claude-style reasoning on top. It should not be a generic wellness dashboard, and it should not bury the user in raw metrics.

The core loop should be:

1. Show actual progress against the current phase.
2. Show what was not done today.
3. Show any deterministic tripwire that fired.
4. Offer one next action.
5. Let Chad speak naturally, the way he already talks to the Claude health project, and turn that into structured logs or protocol decisions.

## 2. What Already Exists

### Data and Backend

- Local repo: `/home/ubuntu/health`
- GitHub repo: `P-U-C/health-tracker` (public)
- FastAPI service: local `127.0.0.1:8026`
- Public read-only routes:
  - `/status`
  - `/dashboard`
  - `/api/dashboard/overview`
  - `/api/mobile/today`
  - `/api/mobile/context`
  - `/app` and supporting PWA assets
- Authenticated write/config routes:
  - `POST /ingest/hae` protected by `HEALTH_INGEST_TOKEN`
  - `POST /api/mobile/session` creates a signed phone session from dashboard credentials or app token
  - `POST /api/mobile/capture` protected by phone session or bearer token
  - `GET /api/mobile/links` protected by phone session or bearer token
- Primary database:
  - `/home/ubuntu/health/data/health.duckdb`
- Public dashboard implementation:
  - `/home/ubuntu/health/api/dashboard_view.py`
  - `/home/ubuntu/health/core/dashboard.py`

### Sources Already Integrated or Staged

- Health Auto Export live ingest: `ingest/hae_rest.py`
- Apple Health XML backfill: `ingest/apple_export_xml.py`
- Apple Health normalized CSV contracts: `data/apple_health/`
- Canonical DEXA tables: `data/dexa/dexa_scans.csv`, `data/dexa/dexa_regional.csv`
- BodyStats staged artifacts: `data/imports/dexa/bodystats_2026-09-16/`
- Labs template: `data/templates/labs_template.csv`
- Strength log template: `data/templates/strength_log_template.csv`
- Events/manual readings templates: `data/templates/events_template.csv`, `data/templates/readings_template.csv`
- Meal-level nutrition logs: `nutrition_logs` table, with local ignored meal photos under `data/imports/nutrition/photos/`

### Product and Protocol Documents

- Build brief: `PROMPT.md`
- Analysis programme: `PLAN.md`
- Product architecture: `docs/product_architecture.md`
- Current dashboard contract: `docs/dashboard_spec.md`
- Mobile app contract: `docs/mobile_app_contract.md`
- Public audit note: `docs/public_audit_note.md`
- SwiftUI scaffold: `ios/HealthCompanion/`
- Life dashboard widget contract: `docs/life_dashboard_widget.md`
- Data schema: `schema/schema.sql`
- Integration registry: `config/components.yaml`

### Health Protocol / Agent Material

- Principles: `playbook/00_principles.md`
- Protocol state: `playbook/01_protocol_state.md`
- Data dictionary: `playbook/02_data_dictionary.md`
- Analysis methods: `playbook/03_analysis_methods.md`
- Training and nutrition: `playbook/04_training_nutrition.md`
- Genomics/labs plan: `playbook/05_genomics_and_labs.md`
- Runtime analyst prompt: `playbook/06_agent_system_prompt.md`
- Training programme reference: `reference/training_program_posture_density.md`

### Ops Surface

- Life dashboard snapshot writer: `jobs/widget_snapshot.py`
- Snapshot path: `~/.local/state/health-tracker-widget.json`
- Console adapter: `ops/console/health.py`
- Systemd units: `ops/systemd/`

## Current Build Slices (2026-09-23)

The app-oriented backend, installable phone web app, and SwiftUI scaffold are now implemented and public:

- `GET /app` serves an installable iPhone web app/PWA for immediate phone use. The current phone shell has Today, Body, Food, Capture, and Context tabs.
- `/app/manifest.webmanifest`, `/app/service-worker.js`, and `/app/icon.svg` support home-screen install and offline shell caching. The worker is registered as `/app/service-worker.js?v=4` and served with `Cache-Control: no-store, max-age=0` to avoid stale phone shells.
- `POST /api/mobile/session` creates a signed, HTTP-only phone session cookie from dashboard credentials or an app token.
- `core/mobile.py` builds the compact Today contract and Claude/ChatGPT context packet from the existing deterministic dashboard model.
- `GET /api/mobile/today` returns the mobile-first state: overall verdict, phase, progress, BodyStats/DEXA body-composition block, Food/macros summary, not-done list, active tripwire, next action, capture affordance, recent captures, and review links.
- `GET /api/mobile/context` returns Markdown intended for Claude/ChatGPT handoff, now including the latest DEXA/body-composition and nutrition/macro summary.
- `POST /api/mobile/capture` logs phone captures into the existing `strength_sets`, `events`, `readings`, and `overrides` tables, plus the new `nutrition_logs` table for meals/macros, behind bearer auth.
- `GET /api/mobile/links` returns configured Claude/ChatGPT project links behind bearer auth; the public Today route does not expose private chat URLs.
- `ios/HealthCompanion/` contains a SwiftUI scaffold with Today, Progress, Tripwires, Capture, and Context tabs.
- The PWA Body tab now shows a BodyStats-style DEXA hero, body-fat sparkline, fat/lean/VAT tiles, DEXA anchors, estimate tiles, and prior-scan deltas.
- The PWA Food tab now shows today's protein, calories, carbs, fat, recent meals, 14-day macro history, and pending macro-estimate count.
- The PWA Capture tab now keeps intent selection, text entry, and Log button above the fold with a compact intent grid; examples are tucked behind a Quick fill drawer.
- The PWA Capture tab now supports meal photo attachment through the phone camera/file picker and progressive voice dictation; photo/freeform meals are stored as `pending_estimate` rather than inventing macros.
- The native Capture tab scaffold has token entry, intent picker, submit state, examples, and recent-capture rendering.
- The Context tab now has share support and locally stored Claude/ChatGPT project/chat links.
- `ReminderScheduler.swift` adds the local notification scaffold for not-done items and tripwire reviews.
- Production tunnel routing has been opened for `/app`, `/api/mobile/today`, `/api/mobile/context`, `/api/mobile/capture`, `/api/mobile/links`, and `/api/mobile/session`.

Verification:

2026-09-22 baseline:

- `uv run pytest tests/test_mobile_app_contract.py -q` -> 8 passed.
- `uv run pytest -q` -> 20 passed.
- `python3 -m compileall -q core api tests` -> passed.
- SwiftUI files received static reference checks on Linux; simulator/device compile still requires Xcode.

2026-09-23 Body/Capture phone pass:

- `uv run pytest tests/test_mobile_app_contract.py -q` -> 8 passed.
- `uv run pytest -q` -> 20 passed.
- `python3 -m compileall -q core api tests` -> passed.
- Live `/api/mobile/today` returned latest DEXA `2026-08-31`, body fat `16.7`, and 9 canonical scans.
- Live `/api/mobile/context` includes `## Body Composition`, DEXA body fat, and VAT lines.
- Parallel live Today/Context requests succeeded after making mobile read helpers use read-only DuckDB connections.
- Live `/app` returned 200 and includes the Body tab, `renderBody`, the compact capture intent grid, and `service-worker.js?v=3`.
- Live `/app/service-worker.js?v=3` returned 200 with `health-companion-v3`, `Cache-Control: no-store, max-age=0`, and Cloudflare `cf-cache-status: BYPASS`.
- Chromium 390x844 screenshots reviewed after deployment for Body and Capture.

2026-09-23 Food/Macros phone pass:

- `uv run pytest tests/test_mobile_app_contract.py -q` -> 9 passed.
- `uv run pytest -q` -> 21 passed.
- `python3 -m compileall -q core api tests` -> passed.
- `nutrition_logs` added as the meal-level history table; `nutrition_daily` remains legacy aggregate/import surface.
- Meal captures with explicit calories/protein/carbs/fat write structured macros immediately.
- Photo/freeform meal captures save locally ignored photo references and enter `pending_estimate` for LLM or human review.
- Live `/app` includes the Food tab, camera capture input, voice dictation button, and `service-worker.js?v=4`.

## 3. What Is Not Working

The data system is strong. The user experience is not.

Current failure modes:

- Too much information appears at once.
- The dashboard is organized like a data console, not a daily companion.
- The most important question, "what did I fail to do today?", is not first-class.
- Tripwires exist, but they need to feel like clear state changes, not another list.
- The current dashboard is public/read-only web; the intended daily surface should be private, native, fast, and interruptible on iPhone.
- The existing Claude health-project style is captured in the playbook prompt, but not yet turned into an app interaction model.

The product should compress the whole system into a calm daily summary and let the deeper material remain one tap away.

## 4. Recommended Product Shape

Build a native iOS app first, with the current backend as the state engine.

The app should have five main surfaces:

### A. Today

The first screen. No dashboard sprawl.

It should show:

- Current phase and day count.
- Overall state: On track / Watch / Action required / Insufficient data.
- One progress visual for the current phase.
- Today's not-done list.
- Active tripwire, if any.
- One recommended action.
- One capture button: speak or type a health note.

Design reference: Apple Fitness summary simplicity, but with fewer rings and more protocol language.

### B. Progress

A calm trend view, not a wall of metrics.

Sections:

- Body composition: DEXA anchors, Eufy trend, DEXA-anchored estimate.
- Training: sessions, load, strength log completeness, aerobic work.
- Recovery: sleep, HRV/RHR baseline state, illness/tag-out windows.
- Anchors: next DEXA, next lab, last calibration.

Design reference: Apple Health trend cards plus BodyStats scan comparison.

### C. Tripwires

A deterministic rules screen.

Each tripwire should show:

- Rule name.
- Status: clear / watch / fired / resolved.
- Evidence snapshot.
- Action.
- Review date.
- Resolution condition.
- Mute/snooze/edit affordance.

No AI-created thresholds. AI may explain and prioritize rules, but the rule must be visible and editable.

### D. Capture

A fast voice/text intake surface that matches how Chad speaks to his Claude health project.

Examples:

- "Logged a 36-hour fast, stopped early because sleep was wrecked."
- "KB press 24, 3x8, RPE 8."
- "I skipped swim today, felt heat and bloating."
- "Whole pizza after refeed, bad idea."

The app should parse this into structured events, workouts, overrides, meals, symptoms, or open questions. If a required field is missing, ask one question only.

### E. Context / Coach

This is not a generic chatbot tab. It is a controlled protocol narrator.

It should:

- Read current state from the backend.
- Use the playbook as standing context.
- Give terse verdicts.
- Log overrides without arguing.
- Explain tripwires and progress.
- Export/update a Claude project brief or ChatGPT context packet.

It should not:

- Diagnose disease.
- Invent thresholds.
- Read raw health data into an external model without explicit consent.
- Replace deterministic rules with vibes.

## 5. Claude and ChatGPT Linking Guidance

The desired feeling is: the iOS app knows the health protocol, and Claude/ChatGPT can discuss it in the same language.

The implementation should not depend on scraping consumer chat UIs.

Recommended architecture:

### Phase 1: Curated Context Export

The app/backend generates a small Markdown context packet:

- Current phase.
- Current progress.
- Not-done-today list.
- Active tripwires.
- Recent overrides.
- Open questions.
- Links to the private source material.

Chad can attach or paste that packet into a Claude project or ChatGPT chat. This is boring but reliable and reviewable.

### Phase 2: Share Sheet and Deep Links

The iOS app should expose:

- Share current status to Claude.
- Share current status to ChatGPT.
- Copy context packet.
- Open a configured Claude project/chat link.
- Open a configured ChatGPT project/chat link.

This gives the right workflow even before formal chat-sync APIs are available.

### Phase 3: Authorized Chat/Project Sync

Use official APIs only where available:

- Claude Enterprise has a Compliance API that can retrieve chats, messages, files, artifacts, projects, and project attachments, but it is enterprise-scoped and compliance-key gated: https://platform.claude.com/docs/en/manage-claude/compliance-content-data
- Claude iOS can read Apple Health data in beta for Pro/Max US users, but it cannot write or modify Apple Health entries: https://support.claude.com/en/articles/11869619-use-claude-with-ios-apps
- ChatGPT supports data export from eligible accounts/workspaces, but exported conversations are not a live product API and Business/Enterprise self-service export is restricted: https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data
- ChatGPT shared links can expose conversation snapshots, but they are sharing artifacts, not a reliable sync API: https://help.openai.com/en/articles/7925741-sharing-conversations-and-scheduled-tasks-in-chatgpt

So the design should assume curated export/import first, official API sync later.

## 6. iOS Technical Guidance

Recommended stack:

- SwiftUI native iOS app.
- HealthKit read access for Apple Health data.
- Local notifications for daily not-done reminders and tripwire reviews.
- App Intents / Shortcuts for quick capture and Siri/Action Button flows.
- Backend sync to the existing FastAPI health service.
- Keep deterministic calculations server-side initially; mirror only selected rules locally.

Apple platform notes:

- HealthKit is the central Apple repository for health/fitness data, and apps need user permission to read/write relevant data: https://developer.apple.com/health-fitness/
- Apple explicitly emphasizes privacy, minimal data collection, clear purpose strings, no sale/use for advertising, and on-device or end-to-end encrypted processing where possible: https://developer.apple.com/health-fitness/
- WidgetKit and Live Activities can show glanceable health status, but sensitive information should be summarized innocuously until the user opens the app: https://developer.apple.com/health-fitness/

## 7. Information Architecture for Designers

Bottom nav recommendation:

1. Today
2. Progress
3. Tripwires
4. Capture
5. Context

Today screen hierarchy:

1. Header: phase + state.
2. Progress card: one primary metric/phase visual.
3. Not Done Today: checklist of missed commitments.
4. Tripwire: only if clear state change exists.
5. Next Action: one action, one reason, one review date.
6. Capture button.

The app should avoid:

- Dense dashboards on first open.
- Multiple competing scores.
- Decorative gauges.
- Moralizing streak mechanics.
- Raw metric walls.
- AI-generated advice that cannot be traced to a rule or measurement.

Visual tone:

- Native iOS, calm, high trust.
- Large numerals, small explanatory labels.
- Semantic colors only: green/on track, amber/watch, coral/action, blue/data.
- Confidence bands and source labels when showing estimates.
- Apple Fitness clarity, Apple Health provenance, BodyStats anchor comparisons, Eufy day-to-day trend familiarity.

## 8. Tripwire and Reminder Model

A reminder is about adherence:

- You did not log strength today.
- You did not hit sleep target.
- Health Auto Export is stale.
- You have not confirmed the current phase variant.
- You have not booked the next DEXA/lab anchor.

A tripwire is about risk or protocol breach:

- Weight trend outside configured band.
- HRV strain vs personal baseline.
- Resting HR strain vs personal baseline.
- Training load increase above ceiling.
- Illness detector fired.
- Data source stale long enough to invalidate tracking.

The app should keep these visually separate. Missing a log is not the same as physiological strain.

## 9. Data Privacy Boundary

Public/safe to discuss:

- Product architecture.
- File and module locations.
- Non-sensitive endpoint names.
- Data-source types.
- Design principles.
- Protocol concepts such as phases, tripwires, and tag-outs.

Private/do not publish:

- `.env` values.
- Health ingest token.
- Raw DuckDB contents.
- Raw Apple Health export.
- Raw DEXA PDFs/text.
- BodyStats cookies/session artifacts.
- Raw Claude/ChatGPT health conversations.
- Raw meal photos and unreviewed meal descriptions.
- Genetic raw files.
- Exact private medical values unless Chad explicitly chooses to publish them.

## 10. Recommended Next Build

Do not redesign the web dashboard first. Use the installable `/app` phone surface now, while the native iOS track continues toward TestFlight.

Already done in the backend/app slices:

1. Installable phone web app at `/app` with Today / Body / Food / Capture / Context tabs.
2. Signed phone session cookie flow via `/api/mobile/session`; no raw token has to live in browser storage.
3. SwiftUI shell with Today / Progress / Tripwires / Capture / Context tabs.
4. Explicit `/api/mobile/today` endpoint that returns only what the app needs.
5. `/api/mobile/context` endpoint that produces Claude/ChatGPT-ready Markdown.
6. Authenticated `/api/mobile/capture` writes for events, sets, overrides, readings, symptoms, phase decisions, and meals/macros.
7. Local notification scheduler scaffold for Not Done Today and tripwire review dates.
8. Share/deep-link scaffolding for Claude and ChatGPT using the context packet.
9. Food/Macros tab backed by `nutrition_logs`, text/voice/photo meal capture, and pending estimate queue.
10. Public tunnel routing and tests for the mobile contract.

Next build:

1. Use the PWA for one real day and tighten what feels noisy or missing.
2. Turn the SwiftUI scaffold into a real Xcode project with bundle id, signing settings, and simulator/device verification.
3. Move the native mobile bearer token from `@AppStorage` to Keychain.
4. Add HealthKit permission flow and read a minimal metric set: steps, workouts, sleep, heart rate, resting HR, HRV, weight, body-fat if available.
5. Improve capture parsing for multi-set workouts, meals/refeeds, fast windows, symptoms, and phase decisions that need one clarifying question.
6. Add source/provenance detail sheet for any metric shown.

## 11. Reviewer Questions

For designers:

- Can the Today screen be understood in 10 seconds?
- Does the app separate progress, reminders, and tripwires clearly?
- Does it feel native to iOS rather than like a web dashboard wrapped in an app?
- Is there one obvious action, or does the user need to interpret a board of metrics?
- Can a voice/text capture flow handle the user's terse health language?

For third-party review:

- Are HealthKit permissions minimal and honestly explained?
- Are AI model boundaries explicit enough?
- Are deterministic rules separated from AI interpretation?
- Is sensitive health data protected by default?
- Is the app avoiding medical-device or diagnostic claims?
- Can every recommendation be traced to a rule, source measurement, and review date?

## 12. North Star

The app wins if Chad opens it once in the morning and once at night and instantly knows:

- whether he is on protocol,
- what he missed today,
- whether anything is materially off,
- and what one thing to do next.

Everything else belongs behind a tap.
