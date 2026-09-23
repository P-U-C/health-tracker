# Mobile App Contract

Date: 2026-09-23

This document defines the first iOS-facing contract for the Health Companion app. It is intentionally narrower than the public dashboard: the app opens to a daily decision surface, not a metrics board.

## Phone App Surface

### `GET /app`

Returns the installable phone web app shell. It is designed for iPhone Safari and can be added to the home screen. The shell uses the same mobile API contract as the SwiftUI scaffold, with Today, Body, Capture, and Context tabs.

Supporting install routes:

- `GET /app/manifest.webmanifest`
- `GET /app/service-worker.js`
- `GET /app/icon.svg`

## Routes

### `GET /api/mobile/today`

Returns the shape needed for the first screen of the iOS app.

Top-level fields:

- `generated_at`: UTC generation timestamp.
- `overall`: state/tone/phrase from deterministic dashboard rules.
- `phase`: current phase title, status, day count, next anchor, and open decision.
- `progress`: the primary phase progress metric, target band, rate, DEXA snapshot, and current DEXA-anchored estimate summary.
- `body`: BodyStats/DEXA-oriented composition payload with latest scan summary, selected metrics, DEXA anchors, body-fat chart points, and prior-scan deltas.
- `not_done_today`: a short list of open adherence/reminder items.
- `tripwire`: the highest-priority active tripwire, or `null`.
- `next_action`: one prioritized action derived from deterministic tripwires.
- `capture`: voice/text capture affordance contract and write endpoint metadata.
- `recent_capture`: recent app/manual captures across events, overrides, readings, and strength sets.
- `review_links`: links back to the dashboard, overview JSON, and context packet.

The `not_done_today` list is intentionally not a physiology alert list. It contains adherence and capture debt items such as restoring HAE sync, confirming the phase variant, logging strength/rest, and logging events or overrides.

### `GET /api/mobile/context`

Returns:

```json
{
  "format": "markdown",
  "markdown": "# Health Context Packet\n..."
}
```

This packet is designed to paste or share into Claude or ChatGPT. It includes current phase, progress, body composition, not-done list, active tripwire, next action, and analyst rules. It is a curated packet, not a raw health-data export.

### `POST /api/mobile/capture`

Authenticated write route for phone capture. It requires `Authorization: Bearer <HEALTH_APP_TOKEN>`; if a separate app token is not configured, the service can fall back to the existing ingest token.

Request shape:

```json
{
  "intent": "strength_set",
  "text": "KB press 24 kg 3x8 RPE 8",
  "occurred_at": "2026-09-22T10:00:00",
  "source": "ios",
  "fields": {}
}
```

Supported intents:

- `strength_set` -> `strength_sets`, or `events` for rest-day capture.
- `event` -> `events`.
- `manual_reading` -> `readings`.
- `override` -> `overrides`.
- `symptom` -> `events`.
- `phase_decision` -> `events`.

Response shape:

```json
{
  "ok": true,
  "intent": "strength_set",
  "stored_as": "strength_sets",
  "records_written": 3,
  "ids": ["..."],
  "needs_review": false,
  "summary": "Logged 3x8 KB press at 24 kg"
}
```

If the app cannot parse required fields, the route returns `ok: false`, `needs_review: true`, `missing_fields`, and no database write.

### `POST /api/mobile/session`

Creates a signed, HTTP-only phone session cookie. The route accepts either the app token or the configured dashboard username/password. The phone web app uses this route so capture does not require storing a bearer token in browser local storage.

Related routes:

- `GET /api/mobile/session` returns `{ "authenticated": true|false }`.
- `DELETE /api/mobile/session` clears the phone session cookie.

### `GET /api/mobile/links`

Authenticated route for configured Claude/ChatGPT project links. The public Today route does not expose these links.

## Current Capture Boundary

Capture writes are enabled for the first practical app path. The parser is intentionally narrow and deterministic; ambiguous notes should ask for one missing field rather than inventing structure.

## Design Rule

The mobile app should lead with one daily verdict and one action. Body composition is the one exception that deserves its own phone tab because DEXA anchors are the core progress measure; deeper dashboard data remains available behind review links.
