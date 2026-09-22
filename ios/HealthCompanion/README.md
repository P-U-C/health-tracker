# HealthCompanion iOS Scaffold

This is the first native iOS app scaffold for the health-tracker review direction.

It is intentionally small:

- `TodayView`: phase, progress, not-done list, active tripwire, one next action.
- `HealthProgressView`: simplified body/progress summary.
- `TripwiresView`: deterministic rules state.
- `CaptureView`: token-gated voice/text capture UI for events, readings, overrides, symptoms, phase decisions, and strength sets.
- `ContextView`: Claude/ChatGPT context packet share surface plus locally stored project/chat links.
- `ReminderScheduler`: local notification scaffold for not-done items and tripwire reviews.

## Backend

Default API base URL in `HealthAPI.swift`:

```swift
https://health.permanentupperclass.com
```

Routes used:

- `GET /api/mobile/today`
- `GET /api/mobile/context`
- `POST /api/mobile/capture`
- `GET /api/mobile/links`

## How to turn this into an Xcode app

1. Create a new iOS SwiftUI App project named `HealthCompanion`.
2. Copy the Swift files from `Sources/HealthCompanion/` into the app target.
3. Set deployment target to iOS 17 or newer.
4. Run on device or simulator.
5. Review the notification permission prompt copy when wiring reminders into a signed target.
6. Add HealthKit permissions only when direct on-device reads are implemented. This scaffold consumes the server contract first.
7. Store the mobile bearer token in Keychain before production use; `@AppStorage` is a prototype convenience.

## Privacy Boundary

The scaffold does not include secrets, tokens, raw Apple Health exports, raw DEXA files, BodyStats cookies, raw genome files, or Claude/ChatGPT transcripts.
