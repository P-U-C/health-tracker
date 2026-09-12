# PLAN — prospective analysis programme

Sequenced so that each block answers a question the next block depends on. Methods (formulas, windows, thresholds) are in `playbook/03_analysis_methods.md`; this file says *what to run, when, and what it decides*.

## 0. Why this is different
Consumer dashboards show yesterday. Clinical reports show one draw. This programme runs a **three-tier measurement system with explicit noise floors**: the genome sets priors once; DEXA and blood panels deliver quarterly/semi-annual verdicts; the Watch and scale track daily *only after being calibrated to those verdicts*. Every decision happens inside a labeled phase with exit criteria written before entry. Interventions are experiments with predictions. The output is not a score — it is one binding constraint, one intervention, one metric, one date.

## 1. Immediately after backfill (one-off retrospective, ~2 weeks of compute-once work)

| # | analysis | question it answers | decides |
|---|---|---|---|
| 1.1 | DEXA series with LSC bands (A1) + phase partitioning (A2) for the six labeled/unlabeled phases May 2025 → Aug 2026 | how much of each phase's Δ was fat vs lean, and what the implied energy balance really was | whether "maintenance" phases were maintenance; the true P-ratio for this subject |
| 1.2 | Eufy→DEXA calibration across all 9 scans (A4) | the scale's bias and its CI | the tripwire bands in DEXA-equivalent units |
| 1.3 | Watch energy-expenditure correction (D) | how far Watch kcal over-reads vs DEXA-implied balance | the TDEE used for all future deficit planning |
| 1.4 | HRV/RHR baselines and states rebuilt with tag-outs (B1, B2); sleep rebuilt with the 6 am rule (B3) | is the "flat HRV four quarters" real once night-only samples and tag-outs are applied? | whether wrist SDNN is usable or the chest strap is mandatory |
| 1.5 | Training dose–response (C3): lag-1..3 HRV/RHR response to load and duration | the actual session-length threshold (prior: 120 min) and the per-session recovery cost | the daily load ceiling rule |
| 1.6 | VO2max volume-adjustment (C5) | how much of the 48.3 peak was running volume | the fitness metric that will judge a future 4×4 block |
| 1.7 | Sleep vs everything: regularity, debt, next-day HRV, week-level strength (once the log exists) | is sleep the binding constraint by the data, not by assertion? | the first quarterly constraint verdict |
| 1.8 | Gait/aging panel (walk speed, double support, asymmetry, stair speeds) monthly means since 2023 | is there a trend worth watching at 41? | whether these go in the weekly review or the quarterly one |

Deliverable: `reports/retrospective_2025-2026.md` — 15 months in one document with error bars, ending in the constraint verdict and the December scan plan.

## 2. The daily/weekly loop (deterministic, from Phase 3 of the build)
- **Daily**: weight 7d mean vs tripwire; HRV/RHR state; sleep last night + debt; load/ACWR; illness detector; phase day-count; alerts only when something fires.
- **Weekly**: trends; strength log summary (tonnage, e1RM per lift, RPE drift, rebound detector); sleep regularity; experiment check-ins; override ledger.
- **Capture debt**: the strength log and the events ledger start the day the pipe is live. They are the two datasets this programme has never had.

## 3. The quarterly anchor loop (DEXA-driven)
1. Pre-scan checklist (conditions, no fast 14 d, no training 24 h).
2. Scan ingested → A1–A7, band verdict (hold / drift / breach), Eufy and kcal recalibration.
3. Phase decision proposed with pre-committed exit criteria; the subject accepts or overrides (logged).
4. Constraint scan (F) with all tiers as evidence → one constraint, one intervention, one metric, one date.
5. Cadence decision (quarterly vs semi-annual) by the two-consecutive-in-band rule.

December 2026 is the first anchor the system runs end-to-end: the accrual verdict for the July → December period, the first automated scan report, and the first constraint scan with a strength log behind it.

## 4. Blood panels (semi-annual, NiaHealth-style — starts at the next draw)
- Draw 1 (first available clean window; ideally 1–2 weeks after the December DEXA): full core panel + hormones + Lp(a) once + omega-3 index. Establishes the personal baseline and tests the first priors (if the genome is back).
- Every draw: RCV deltas, target distances, cross-link tests (VAT↔TG/insulin/ALT; load↔CK/CRP/ferritin; sleep↔cortisol/CRP/HbA1c; deficit↔fT3/SHBG/T).
- Draw 3 onward: personal reference intervals replace population ranges for trend detection.
- Add-ons by trigger: CGM 14-day once (or when HbA1c/insulin/T2D-PRS flags); lab VO2max annually to calibrate Apple; advanced thyroid only if TSH/fT3 pattern is odd across two draws.
- Output per draw: `reports/labs_<date>.md` — ranked deltas in RCV units, target distances, which priors moved status, what the next draw should re-test.

## 5. Genome (once; the priors then live forever)
1. Sequence (30× WGS preferred). Encrypt raw. Run `ingest/genome/`.
2. Populate `genomics_variants` (curated panel in `playbook/05 §2.2`), `genomics_prs` (CAD, T2D, BMI/adiposity, lipids; ancestry-matched percentiles), `genomics_priors` with evidence grades.
3. Apply A/B priors to targets: ApoB/LDL (APOE, CAD PRS, FH variants), HbA1c/insulin (TCF7L2, T2D PRS), ferritin rules (HFE), bilirubin (UGT1A1), folate/homocysteine (MTHFR), omega-3 strategy (FADS1), vitamin D dose prior (GC/CYP2R1). PGx stored for clinicians.
4. Generate experiments from B/C priors, highest value first: **caffeine cutoff time (CYP1A2/ADORA2A) against the sleep constraint**, then satiety strategy (FTO/MC4R), then rep-scheme rotation order (ACTN3/ACE — weak, last).
5. Each prior's status (dormant/active/confirmed/refuted) is updated by every later lab draw and experiment. A prior that never gets confirmed gets demoted; the file tells you which of your genes actually mattered.

## 6. Experiments already queued (from the ledger)
| experiment | metric | prediction | status |
|---|---|---|---|
| Monthly 36 h fast with electrolytes | weight 7d, HRV/RHR (tagged), CK on next draw | no HRV penalty beyond 48 h; no lean loss on next DEXA | rule-based, ready |
| Cold-immersion timing vs lift sessions | strength log e1RM, HRV next day | ≥ 4–6 h separation preserves progression | needs strength log |
| Norwegian 4×4 block | vo2max_volume_adj, aerobic efficiency, sleep | blocked until sleep median ≥ 7 h and HRV state normal ≥ 70 % of days | gated |
| Calorie cycling toward lift days | weight trend, session RPE | flat weight, lower lift-day RPE | running, unmeasured |
| Caffeine cutoff (pending genome) | sleep duration, deep min, regularity | +20–30 min asleep if slow metaboliser | pending |

## 7. What the system reports, by cadence
Daily push (≤ 8 lines, silent by default) · weekly review · per-scan report · per-draw report · quarterly constraint verdict · annual: calibration history, prior scorecard, cadence review, and a one-page "what changed this year" with the DEXA table.

## 8. Success criteria for the programme (12 months)
- Zero unlabeled phase transitions.
- Data lag < 24 h for ≥ 95 % of days; strength log ≥ 90 % of sessions.
- Every scan and draw produces its report without manual work.
- The binding constraint has been named and relieved at least once, with the metric showing it (sleep median ≥ 7 h is the obvious first target).
- Band held or deliberately revised — never drifted.
