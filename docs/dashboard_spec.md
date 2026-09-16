# Health Optimization Dashboard Specification

Status: MVP product definition
Primary data available: Apple Health, Eufy smart scale, DEXA scans
Planned data: nutrition, bloodwork, DNA

## Product Purpose

This is a personal optimization system, not a general wellness dashboard. The overview should answer five questions:

1. What is the current body composition and physical capacity?
2. Is progress tracking toward explicit goals at the intended rate?
3. What has materially changed?
4. Has a predefined tripwire been crossed?
5. What action should be taken now, and did the intervention work?

The interface prioritizes trajectories, decisions, exceptions, and provenance. Raw measurements remain accessible, but they should not dominate the overview.

## Product Principles

- Trajectory over snapshots: daily readings are noisy; rolling trends drive decisions.
- Source honesty: Eufy BIA and DEXA are never presented as interchangeable measurements.
- Tripwires over vague insights: alerts have explicit rules, severity, evidence, and action.
- Targets over norms: user objectives are shown separately from clinical reference ranges.
- One recommended action: the overview identifies the highest-value current intervention.
- Evidence and confidence: every derived metric exposes source, calculation, recency, and confidence.
- Closed feedback loops: interventions are recorded and later reviewed against outcomes.
- Medical restraint: the product can identify patterns and prompt follow-up, but must not diagnose disease or overstate causality.

## Information Architecture

Primary navigation:

- Overview: current trajectory, active tripwires, today's action
- Body: weight, fat, lean mass, regional composition, DEXA history
- Performance: cardio, strength, activity, training load, recovery
- Nutrition: intake, macros, adherence, correlations
- Bloodwork: biomarkers, reference and target ranges, follow-ups
- Genetics: variants, evidence strength, actionable context
- Experiments: interventions, hypotheses, outcomes, confidence
- Data & Rules: integrations, source priority, goals, tripwire configuration

Future modules must display `Add source` rather than fictional values.

## Overview Requirements

The overview has these regions:

- Global status header: On track, Watch, Action required, or Insufficient data, plus current goal, remaining time or next anchor, data freshness, and range selector.
- Body trajectory hero: smoothed weight, target range, current and intended change rate, projected target date, latest DEXA fat/lean values, DEXA-anchored estimates, and deltas since goal start and last DEXA.
- Today's intervention: one prioritized recommendation generated from the highest-severity actionable tripwire, with why, supporting measurements, confidence, accept/dismiss/modify affordances, and review date.
- Body composition card: weight trend, DEXA body-fat percent, estimated current body-fat range, total lean mass, appendicular lean mass, VAT, android/gynoid ratio, bone mineral density, and waist when available.
- Performance card: weekly exercise minutes, running/walking distance, Zone 2 volume, comparable-HR pace, VO2 max, resting HR, HRR when available, strength sessions/progression, and training load when data supports it.
- Tripwire rail: only items requiring attention or recently resolved, with rule, value, source, recency, action, trigger/review dates, and resolution condition.
- Cause-and-effect timeline: synchronized events and outcomes. Events include running, strength, other exercise, sleep, nutrition, alcohol, sauna/cold exposure, illness, fasting, blood draws, DEXA scans, and user-created interventions. Outcomes include weight/body composition, RHR/HRV, VO2 max, training performance, and biomarkers.

Associations are described as correlations unless the experiment design supports a stronger conclusion.

## Eufy And DEXA Reconciliation

Non-negotiable rule: do not merge Eufy BIA body-fat readings and DEXA body-fat readings into one raw series.

Maintain three distinct values:

- DEXA measured value: sparse higher-authority anchor points.
- Eufy measured value: frequent lower-confidence trend signal.
- DEXA-anchored estimate: calculated current estimate between DEXA scans.

Initial MVP estimation:

- `offset_at_scan = DEXA_body_fat_percent - median_Eufy_body_fat_percent_near_scan`
- The nearby window is initially +/- 3 days.
- `estimated_body_fat = smoothed_Eufy_body_fat + current_calibration_offset`
- Hold the most recent offset until another DEXA scan is available.
- Display a range, not false decimal precision.
- `estimated_fat_mass = smoothed_weight * estimated_body_fat_fraction`
- `estimated_lean_plus_bone_mass = smoothed_weight - estimated_fat_mass`

Do not label the second derived value as DEXA lean mass. DEXA distinguishes fat, lean soft tissue, and bone mineral content.

Quality guidance for Eufy readings:

- Similar time of day
- Post-bathroom
- Before food, heavy exercise, or sauna
- Similar hydration state
- Same hard surface
- Store raw readings and display a 7-day rolling median or robust smoothing by default.

Source labels:

- DEXA measured
- Eufy measured
- Estimated from DEXA + Eufy trend
- User entered

Clicking a source label reveals date, device/provider, raw value, transformation, and confidence.

## Canonical Data Model

The durable model is source-agnostic and preserves the provenance chain:

`raw observation -> normalized observation -> derived metric -> dashboard insight`

Core entities:

- User profile: user ID, DOB, algorithm sex, height, time zone, units, goals, context.
- Observation: metric code, value, unit, observed/start/end timestamps, source system, device/provider, source record ID, acquisition method, raw/normalized/derived status, confidence, import timestamp, metadata.
- Event: workout, meal, fast, sauna, illness, intervention, scan, blood draw, start/end, intensity/dose, source, notes/tags.
- Goal: metric/outcome, start value/date, target range/date, intended rate, priority, status.
- Tripwire rule: versioned metric rules, windows, baselines, thresholds, persistence, severity, freshness, action template, resolution, enabled/muted state.
- Tripwire occurrence: evidence snapshot, state, acknowledgement, intervention, review, resolution.
- Intervention/experiment: hypothesis, action, dates, outcome, confounders, adherence, result, confidence.

Raw source records are never overwritten by normalized or corrected values.

## Initial Metric Catalogue

Body composition:

- Body mass
- BMI, low emphasis
- Eufy body-fat percentage
- DEXA body-fat percentage
- Estimated current body-fat range
- DEXA fat mass
- DEXA lean mass
- Regional lean/fat mass
- Visceral adipose tissue
- Bone mineral content/density
- Weight rate of change
- Lean-mass change between DEXA scans

Activity and performance:

- Steps and walking/running distance
- Active energy
- Exercise minutes
- Workout type, duration, energy
- Heart-rate zones
- Zone 2 minutes and pace
- Resting heart rate
- HRV with exact Apple metric/method
- VO2 max/cardio fitness estimate
- Heart-rate recovery when available
- Running pace, power, cadence, vertical oscillation when available
- Weekly training frequency
- Strength volume and estimated 1RM when available

Recovery:

- Sleep duration and consistency
- Resting-heart-rate deviation
- HRV deviation
- Training load
- Subjective energy, soreness, pain
- Illness indicators entered by the user

## Tripwire Engine

Tripwires are deterministic and editable. AI can explain or prioritize them, but must not silently invent thresholds.

Starter rules:

- Weight-loss rate: above configured target or safety ceiling until back in range.
- Weight plateau: below expected change for the configured period until trend resumes.
- Lean mass: directional decline or meaningful DEXA decline until stable or improved.
- Training load: weekly increase above watch or ceiling until planned range returns.
- HRV: below personal baseline for configured duration until baseline band returns.
- Resting HR: elevated versus baseline until baseline band returns.
- Sleep: below target average or severe deficit until restored.
- Strength: comparable lift stall or decline until prior range returns or plan changes.
- Bloodwork: approaching or outside configured range until reviewed or repeated in range.
- Data quality: required source stale or missing until sync restores.

Use personal baselines for high-variance signals. Initial approach: rolling 28-day median with exclusions for illness, travel, or anomalous periods.

Alert fatigue controls: persistence before triggering, cooldowns after acknowledgement, grouping related signals, one overview action, short resolved visibility, mute/snooze/threshold adjustment.

## Nutrition, Bloodwork, DNA, And Experiments

Nutrition supports manual, barcode/database, photo-assisted later, tracker import, recipes, recurring meals, and supplements. Display ranges, logged versus inferred intake, missing days, adherence, and comparisons against body composition, performance, and bloodwork.

Bloodwork supports PDF/image upload with review, structured integrations, manual entry, lab/provider metadata, fasting status, original units/reference ranges, validated conversions, personal targets, and longitudinal trends. Wording should be `outside the configured range`, not diagnosis.

DNA is relatively static context. Store provider/build, variant, genotype, association, evidence strength, population applicability, source/citation, and review date. DNA modifies context or monitoring priority; it does not create alarmist scores.

Experiments require:

- Hypothesis
- Intervention and dose
- Outcome metric
- Start/end dates
- Minimum adherence
- Known confounders
- Review point

The result screen reports what changed, expected-direction movement, adherence, confounders, confidence, and continue/stop/modify recommendation. Avoid causal language for uncontrolled observations.

## Visual Direction

- Desktop-first, responsive to mobile.
- Near-black graphite or warm light neutral theme.
- Large tabular numerals.
- Restrained semantic color: green/on track, amber/watch, coral/triggered, blue/activity/data.
- Minimal card chrome and decorative gauges.
- Lines and confidence bands for trajectories.
- Dots/markers for DEXA scans and blood draws.
- Clearly different line treatments for measured versus estimated data.
- Hover/click reveals provenance and calculation.
- Analytical, calm, decisive; not gamified and not clinical.

## MVP Scope

Phase 1:

- Authentication and profile
- Apple Health ingestion pathway
- Eufy import/integration pathway
- DEXA structured manual entry plus report upload
- Overview
- Body composition screen
- Performance screen
- Configurable goals
- Basic deterministic tripwire engine
- Source provenance and data freshness
- CSV export

Phase 2:

- Nutrition ingestion/logging
- Bloodwork upload, extraction, confirmation
- Intervention/experiment tracking
- Cause-and-effect timeline
- Notification preferences
- Improved DEXA-anchored estimation

Phase 3:

- DNA ingestion and evidence layer
- Advanced correlation analysis
- Personalized rule recommendations requiring user confirmation
- Clinician/coach sharing controls
- Automated periodic reports

## Technical And Privacy Requirements

- Encrypt health data in transit and at rest.
- Collect only required permissions and data types.
- Provide granular source connection and deletion controls.
- Keep health data separate from generic analytics.
- Record consent and permission state.
- Maintain an audit log for imports, edits, and deletions.
- Allow complete export and account deletion.
- Never send health data to an AI model without explicit product disclosure and appropriate controls.
- Treat genetic data as especially sensitive with separate consent and deletion handling.
- Keep recommendations explainable and traceable to measurements/rules.
- Require human confirmation for extracted DEXA and bloodwork values before tripwire use.

## First Build Acceptance Criteria

The MVP succeeds when the user can:

- Connect/import Apple Health, Eufy, and DEXA data.
- See source and timestamp for every important metric.
- View Eufy and DEXA separately without misleading continuity.
- See a DEXA-anchored current estimate with uncertainty range.
- Define a body-composition goal and intended rate.
- See track status and projected target date.
- Configure, trigger, acknowledge, and resolve a tripwire.
- Understand why a tripwire fired and what data supports it.
- Record an intervention and review subsequent outcome.
- Export or delete data.

## Decisions Still Required

- Native iOS, web, or both.
- Exact Apple Health ingestion architecture.
- Whether Eufy arrives directly, through Apple Health, or by export.
- First DEXA provider/report formats.
- Initial body-composition goal model.
- Strength-training source.
- Nutrition source/logging strategy.
- Bloodwork geography and laboratory formats.
- DNA providers/file formats.
- Notification channel and cadence.
- Personal-only or multi-user product.

## Suggested First Engineering Spike

Before heavy visual polish:

1. Import 60-90 days of Apple Health and Eufy data.
2. Enter at least one DEXA scan in structured form.
3. Create the canonical observation model and provenance chain.
4. Plot raw Eufy readings, smoothed Eufy trend, and DEXA anchor together.
5. Calculate a first DEXA-anchored estimate with uncertainty band.
6. Implement data freshness, weight trajectory, and training-load tripwires.
7. Validate that every displayed insight traces back to source records.
