# 03 — Analysis methods

Implementable definitions. Every derived metric here maps to a column in `derived_daily` or a function in the analysis module. Windows are anchored to the **dataset max date**, never the system clock (the two diverge whenever the pipe stalls).

## A. Body composition (Tier 1 anchor: DEXA)

**A1. Scan series with error bars.** Plot fat mass, lean+BMC, BF %, ALMI, VAT with ± LSC. LSC = 2.77 × precision SD. Until a personal precision study exists (two scans within 7 days, or the December scan plus a repeat), use Hologic whole-body published precision: fat mass CV ≈ 2 % (≈ 0.25 kg), lean CV ≈ 1 % (≈ 0.6 kg), BF % SD ≈ 0.5 pp, VAT SD ≈ 40–60 g. Subject's observed scan-to-scan noise on BF %: ±0.5–1.0 pp.

**A2. Phase partitioning.** For each labeled phase with a scan at both ends: ΔFM, ΔLM (lean+BMC), P-ratio = ΔLM / (ΔLM + ΔFM). Implied mean daily energy balance (Hall): `EB = (ΔFM × 9,400 + ΔLM × 1,800) kcal / days`. Compare with the Eufy-trend-implied balance (A3) → calibration of the scale-derived estimate. Report both with propagated LSC error.

**A3. Scale trend and energy balance.** Eufy weight: 7-day rolling mean (centred where possible, trailing for the live edge), plus a 14-day slope via Theil–Sen (robust to spikes). Daily implied balance ≈ slope(kg/day) × 7,700 kcal/kg during fat-dominant phases; use the phase P-ratio from A2 when available. Never report a single weigh-in as a change.

**A4. Eufy → DEXA calibration.** At each scan date, pair the Eufy 7-day means (weight, BF %) with the DEXA values. Fit `DEXA_BF = a + b × Eufy_BF` across all scans (currently n = 9 possible once backfilled). Report offset with 95 % CI; recalibrate every scan; alert if the residual for a new scan exceeds 2 × residual SD (hydration state or scale drift). Historical offset: Eufy +0.8–1.0 pp above DEXA; +0.3 pp on 2026-07-09.

**A5. Band monitor.** For each band marker: value, edge distance, edge distance in LSC units, 3-scan linear trend and its extrapolation to the next scan date. Status ∈ {in-band, at-edge (< 1 LSC), out}. Composite verdict per scan: hold / drift / breach. Drift = ≥ 2 markers at-edge with trend toward the edge.

**A6. Deficit planner.** Inputs: current FM (DEXA + Eufy-calibrated drift), band floor. Fat runway = FM − FM_at_floor. Alpert ceiling = 31 kcal × FM(kg) per day of fat oxidation. Weekly cap = min(Alpert, 0.5 % BW/week × 7,700 kcal). Deficit → expected weeks to floor; if runway < 1 LSC of fat mass, the deficit is unverifiable → block. Extended fast: model 0.5–0.7 kg fat per 72 h, plus 2–3 kg water/glycogen that returns within ~10 days.

**A7. Regional.** ALMI trajectory vs YN/AM percentiles; appendicular lean by limb; leg lean asymmetry (R−L)/L — subject's range 3–8 % across scans, treat < 8 % as positioning noise; trunk fat and VAT (mass, area) trajectory; android/gynoid ratio. Bone: total BMD, T/Z (currently +0.4); annual review only.

## B. Recovery (Tier 2, Apple Watch)

**B1. HRV.** Daily value = mean of SDNN samples per calendar day (also compute the 00:00–07:00 subset as `hrv_night`). Transform: ln(HRV). Baseline = trailing 28-day mean and SD of ln(HRV) with tag-outs removed. SWC = 0.5 × SD. State: `hrv_7d` vs baseline: **normal** (within ± SWC), **low** (below −SWC), **high** (above +SWC). Weekly HRV CV (SD/mean over 7 days) as a strain indicator (rising CV = accumulating strain even if the mean holds). Upgrade path: chest-strap morning rMSSD (Polar H10 via an app that writes to Apple Health) becomes the primary HRV stream when present; SDNN becomes secondary.

**B2. RHR.** Same baseline logic on raw bpm (28-day mean/SD, SWC = 0.5 × SD). Joint state matrix with HRV: normal/normal = ready; HRV low & RHR high = strain (no intensity); HRV high & RHR high = possible parasympathetic saturation or illness onset — check resp rate; HRV low & RHR normal = watch.

**B3. Sleep.** Night key = `start − 6 h` date. Asleep minutes = Σ(AsleepCore + AsleepDeep + AsleepREM + AsleepUnspecified) with Watch-source precedence. Metrics: duration, deep min, REM min, efficiency = asleep / in-bed, midpoint, **sleep regularity** = SD of midpoint over 7 nights, sleep debt = Σ max(0, 7 h − duration) over 14 nights. Targets: median ≥ 7 h, regularity SD < 45 min. Sleep is the current binding constraint; report it first in every weekly review.

**B4. Illness / distortion detector.** Overnight resp rate baseline (28 d). Fire when resp ≥ baseline + 1 brpm AND RHR ≥ baseline + 5 bpm AND HRV state = low on the same night → propose tag-out, suppress intensity for 48 h. SpO2 nightly mean < 94 % or p5 < 90 % → flag.

## C. Training load (Tier 2)

**C1. Per-workout load.** If `hr_avg` present: Banister TRIMP = duration_min × ΔHR × 0.64·e^(1.92·ΔHR), ΔHR = (hr_avg − HR_rest)/(HR_max − HR_rest), with HR_rest = that day's RHR and HR_max = max observed in the last 365 days of workouts (fallback 220 − age = 179). If no HR (strength sessions logged without Watch): session RPE × duration (Foster). Store both; use TRIMP for cardio, sRPE for lifting.

**C2. Acute:chronic.** Acute = EWMA(load, τ = 7 d); chronic = EWMA(load, τ = 28 d); ACWR = acute/chronic. Monotony = mean/SD of daily load over 7 d; strain = weekly load × monotony. Flags: ACWR > 1.5, monotony > 2.0.

**C3. Dose–response.** Regress next-day (lag 1, 2, 3) HRV and RHR deltas on daily load and session duration, controlling for sleep duration. Estimate the duration threshold empirically (prior: > 120 min sessions produce a next-day dip). Report as an effect size with CI; recompute quarterly.

**C4. Fitness–fatigue (Banister).** Fit `p(t) = p0 + k1·Σ w(i)e^{−(t−i)/τ1} − k2·Σ w(i)e^{−(t−i)/τ2}` to a performance proxy (aerobic efficiency, C5). Use to time deloads and to predict the response to the planned 4×4 block before adding it.

**C5. Aerobic efficiency.** For runs with hr_avg inside Zone 2 (60–70 % HRR): speed / hr_avg, tracked over time (higher = fitter). Swim: pace per 100 m at steady HR. VO2max: regress Apple's estimate on trailing 90-day outdoor run minutes; the residual is the volume-independent fitness signal (peak 48.3 mL/kg/min was mostly volume).

**C6. Strength.** Per set: e1RM = load × (1 + reps/30) (Epley), RPE-adjusted via RIR = 10 − RPE. Per session: tonnage, top e1RM per lift, mean RPE. Trends per lift with 4-week slope. Rebound detector: > 5 % e1RM jump across ≥ 3 lifts in one session → tripwire. Deload verification: volume ≈ 50 %, load 75–80 % of the previous 4-week mean.

## D. Energy expenditure calibration
Watch `active_cal + basal_cal` vs DEXA-implied balance (A2) plus logged intake when available. Fit a correction factor per phase; expect the Watch to over-estimate. Use the corrected TDEE for deficit planning, never the raw Watch number.

## E. Labs (Tier 1) — see `05_genomics_and_labs.md` for analytes
**E1. Reference change value.** For each analyte, RCV = 2^0.5 × 1.96 × √(CVa² + CVi²) using within-subject biological variation (CVi) from the EFLM biological variation database and analytical CV (CVa) from the lab. A change between draws is a signal only if |Δ| > RCV. **E2. Personal reference interval** after ≥ 3 draws. **E3. Cross-links** (computed, not asserted): trunk fat/VAT ↔ TG, fasting insulin, ALT, GGT; 7-day training load ↔ CK, AST, hs-CRP, ferritin; 30-day sleep ↔ cortisol, hs-CRP, HbA1c; deficit phases ↔ free T3, SHBG, testosterone (deficit signature); creatine ↔ creatinine (expected; prefer cystatin-C eGFR).

## F. Constraint scan (quarterly)
Score each candidate constraint 0–3 on evidence: sleep (median < 7 h → 3), protein (logged days < 1.9 g/kg → +1 per 25 % of days), stimulus (no e1RM progression in 8 weeks on ≥ 2 primary lifts → 2), recovery (HRV low-state days > 30 % → 2), energy availability (EB < −300 kcal/day for > 4 weeks → 2). Highest score = binding constraint. Output: one constraint, one smallest intervention, one metric that will show it worked, one date to check.

## G. Reporting
- Daily (deterministic push): phase + days remaining, band position (5 markers), weight 7d mean vs tripwire, HRV/RHR state, sleep last night + 7d median + debt, load/ACWR, open experiments, next anchors. Silent unless a rule fires.
- Weekly: the above plus trends, strength log summary, overrides logged.
- Per scan: A1–A7, verdict, phase decision proposal with pre-committed exit criteria for the next phase.
- Per lab draw: E1–E3, targets vs results, changes to priors.
- Quarterly: constraint scan (F), experiment ledger review, cadence decision.
