# 01 — Protocol state (as of 2026-09-12)

This file is the seed for the `phases`, `bands`, `tripwires`, `tagouts`, `overrides` and `experiments` tables. Once the system is live, the tables are canonical and this file is regenerated from them.

## Maintenance band (adopted 2026-08-17, first applied to scan #9 on 2026-08-31)

| marker | band | scan #9 (2026-08-31) | position |
|---|---|---|---|
| Body fat % (DEXA) | 15.0–17.0 | 16.7 | top of band |
| Lean + BMC (kg) | ≥ 59.0 | 60.27 | in band |
| ALMI (kg/m²) | ≥ 9.0 | 9.39 | in band, best ever |
| Body weight (kg, DEXA total) | 70.0–72.5 | 72.38 | top of band |
| VAT mass (g) | < 350 | 310 | in band |

Verdict on scan #9: all five in band, three at the top edge → **drift, not a clean hold**. Jul 9 → Aug 31: fat +0.84 kg, lean+BMC +0.15 kg (flat). The "maintenance" between those scans ran ≈ +125 kcal/day and bought no lean tissue.

Band edges are compared in units of DEXA LSC (assume 0.5 kg fat mass / 0.6 kg lean / 1.0 pp BF until a personal LSC is computed). Margin < 1 LSC = "at edge".

## Scan cadence
- Two consecutive in-band quarterly scans (Jul 9, Aug 31) unlocked the **quarterly** cadence.
- Next anchor: **December 2026** — the accrual verdict. September scan cancelled.
- Semi-annual cadence is a candidate after two more consecutive in-band scans.
- Scan conditions: morning, fasted, post-void, no training 24 h, no extended fast within 14 days, same machine/operator (BodyStats, Hologic Horizon W).
- Scan history: 2025-05-27, 07-31, 09-02, 2026-01-30, 02-26, 04-24, 06-04, 07-09, 08-31 (see `data/dexa/dexa_scans.csv`).

## Current phase (status unconfirmed — confirm on first run)

**Phase: "post-fast 5-week stint"** — kind: mild deficit — entered 2026-09-04 (after refeed).
- Deficit: −150 kcal/day pre-committed; recommended revision on 2026-09-06 was either shorten to ~3 weeks (exit ≈ 2026-09-25) or cut to −100 kcal/day, with preference for the shorter stint. **Which was chosen is not recorded.**
- Original exit: ≈ 2026-10-08.
- Exit criteria: Eufy 7-day rolling mean inside the tripwire, or date reached, or band floor approached (fat runway ≈ 1.0 kg above the 15 % floor after the fast; thinner than DEXA precision, hence the shorten recommendation).
- Rules inside phase: protein ≥ 1.9 g/kg; no load progression in week 1 post-fast; hold lifts at current loads (maintenance since 2026-08-17).
- Eufy readings uninterpretable until ≈ 2026-09-12; 7-day mean clean from ≈ 2026-09-18 (post-fast glycogen/water refill).

**Preceding events**
- 2026-08-31 18:00 → 2026-09-03 12:00: extended fast, ~66 h (target 72 h), exited early per pre-committed rule (wrecked sleep night 2 + persistent headache/soreness). Fat mobilised est. 0.4–0.6 kg; scale drop 2–3 kg.
- 2026-09-03 evening: refeed (lamb + sweet potato, endorsed) then whole pizza → rebound hyperphagia, next-day GI distress. Logged as n=1 refeed data: no consecutive high-fat meals after a >48 h fast.
- 2026-09-08: symptom cluster (fatigue, heat, bloating, weakness under load after lifting through soreness) → labs recommended (CK, Na/K/Mg/phosphate, creatinine/eGFR, CBC); advised no lifting/swimming/fasting until results. **Status unknown.**

## Tripwires (active)
| name | metric | rule | action |
|---|---|---|---|
| stint weight floor/ceiling | Eufy weight, 7-day rolling mean | outside 70.5–71.5 kg | review deficit; stop if below floor |
| latent-strength rebound | strength log | > 5 % jump across lifts in one session | flag as expression, hold loads 2–3 sessions at RPE ≤ 8 |
| long-session recovery | workouts | single day > 120 min | expect next-day HRV/RHR dip; do not stack |
| HRV strain | HRV 7d mean vs 28d baseline | below baseline − SWC for 3 consecutive days | no intensity; deload check |
| illness detector | resp rate + RHR + HRV | resp +1 brpm & RHR +5 bpm & HRV below SWC, same night | tag-out candidate; no training |

## Tag-outs (excluded from baselines)
| window | streams | reason |
|---|---|---|
| 2026-08-31 → 2026-09-02 | HRV, RHR, sleep, weight | extended fast |
| 2026-09-03 → 2026-09-07 (proposed) | weight | refeed refill; HRV/RHR included but flagged |

## Fasting protocol (as agreed 2026-09-05)
- Monthly 36 h: defensible with rules — electrolytes (Na 2–3 g/day, K 1–1.5 g/day, Mg glycinate as usual), creatine continued, Zone-1 walking only, exit on objectively wrecked sleep or persistent symptoms.
- Quarterly 72 h: **demoted** from scheduled ritual to trigger-based (band breach or scan overshoot only).
- No DEXA or blood draw within ~14 days after an extended fast.

## Overrides ledger (seed)
| date | recommendation | decision | outcome |
|---|---|---|---|
| 2026-08-31 | no further deficit after in-band scan | 3-day fast + 5-week stint | fast exited early at 66 h; symptom cluster day 5 |
| 2026-09-02 | exit fast (pre-committed rule) | continued briefly, then exited | headache/soreness/poor sleep |
| 2026-09-08 | no lifting until labs | (unknown) | (unknown) |

## Open items to resolve on first run
1. Which stint variant was chosen (3-week / −100 kcal) and whether it is still running.
2. Post-fast labs: done? results? → first `labs` rows.
3. "June test" (mentioned 2026-08-31): undefined; if it requires a leaner state than the band, revise the band deliberately now.
4. Start the strength log (never kept). Seed exercises from `reference/training_program_posture_density.md`.
5. Backfill Apple Health from a fresh export (CSVs end 2026-01-30).
6. Book the December DEXA and a blood draw 1–2 weeks after it, both inside one clean window (no fast 14 d, no hard training 48 h).
