# Mobile App Contract

Date: 2026-09-22

This document defines the first iOS-facing contract for the Health Companion app. It is intentionally narrower than the public dashboard: the app opens to a daily decision surface, not a metrics board.

## Routes

### `GET /api/mobile/today`

Returns the shape needed for the first screen of the iOS app.

Top-level fields:

- `generated_at`: UTC generation timestamp.
- `overall`: state/tone/phrase from deterministic dashboard rules.
- `phase`: current phase title, status, day count, next anchor, and open decision.
- `progress`: the primary phase progress metric, target band, rate, DEXA snapshot, and current DEXA-anchored estimate summary.
- `not_done_today`: a short list of open adherence/reminder items.
- `tripwire`: the highest-priority active tripwire, or `null`.
- `next_action`: one prioritized action derived from deterministic tripwires.
- `capture`: voice/text capture affordance contract.
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

This packet is designed to paste or share into Claude or ChatGPT. It includes current phase, progress, not-done list, active tripwire, next action, and analyst rules. It is a curated packet, not a raw health-data export.

## Current Capture Boundary

The first slice is read-only. Capture examples and intents are exposed in the API, but write endpoints are still planned.

Planned intents:

- `strength_set`
- `event`
- `manual_reading`
- `override`
- `symptom`
- `phase_decision`

## Design Rule

The mobile app should lead with one daily verdict and one action. Full dashboard data remains available behind review links, but not on first open.
