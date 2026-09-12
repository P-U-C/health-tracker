# 00 — Principles

These are the rules the system enforces in code. An LLM narrates over them; it does not get to relax them.

## 1. Measurement hierarchy — slow instruments anchor, fast instruments track
Every metric belongs to a tier and carries its own noise floor. Nothing is reported without it.

| Tier | Instruments | Cadence | Role |
|---|---|---|---|
| 0 — Priors | Genome (WGS/array), family history | once | Sets targets and weights. Never issues a directive on its own. |
| 1 — Ground truth | DEXA (BodyStats Hologic), fasting blood panel (NiaHealth-style, 60+ biomarkers), lab VO2max if done | quarterly / semi-annual | Verdicts. Phase exits are judged here only. |
| 2 — Calibrated proxies | Eufy scale (daily), Apple Watch (HRV, RHR, sleep, SpO2, resp rate, workouts), strength log, events | daily | Tracking between anchors. Each proxy is re-calibrated against its Tier-1 anchor at every anchor. |

Corollaries:
- A Tier-2 reading is interpreted only as a **rolling statistic against its own baseline** (7-day mean vs 28-day, etc.), never as a point value.
- A change is a signal only if it exceeds the instrument's **least significant change (LSC)** — DEXA ±0.5–1.0 pp BF scan-to-scan for this subject, Eufy day-to-day ±1–2 pp / ±1 kg, HRV smallest worthwhile change ≈ 0.5 × baseline SD.
- Proprietary composites (readiness scores, "body age") are not inputs. Raw exported signals only, with transparent rules.
- Consumer BIA never decides anything about fat mass. DEXA does. Wrist SDNN never decides recovery on its own; chest-strap rMSSD is the upgrade path.

## 2. Phase discipline — every day is inside a labeled phase
- A phase has a name, a kind (deficit / maintenance / accrual / deload / fast / recovery), an entry date, **pre-committed exit criteria written before entry**, and a status.
- The best result inside a phase is a signal to **exit** the phase, not to intensify it.
- A phase transition that the system did not label is a defect (the August 2026 "maintenance that was +125 kcal/day" was the third unlabeled transition; the system exists to make a fourth impossible).
- Deficits: ceiling from the Alpert limit (~31 kcal per kg fat mass per day of fat mobilisation) and the 0.5 %-bodyweight/week rule; runway = fat mass above the band floor, in units of DEXA LSC. When runway < 1 LSC, the deficit cannot be verified and must end.
- Lean accrual for this subject is **stimulus-limited, not energy-limited** (a surplus with maintenance-volume training bought fat, not lean). A surplus is only permitted inside an accrual phase with progressive-overload logging in place.

## 3. Constraint identification (Theory of Constraints)
Adaptation is governed by the scarcest input. Quarterly, the system ranks the candidate constraints — sleep, protein, training stimulus/progression, recovery capacity, energy availability — by evidence, names **one** binding constraint, and proposes the smallest intervention at that constraint. Load is removed from non-constraints (subordination) before resources are added at the constraint (elevation). Current binding constraint (since 2025): **sleep** (no quarter with median ≥ 7 h; HRV flat 48–50 ms four quarters while RHR improved).

## 4. Experiments, not vibes
Any intervention (fast, deload, supplement change, caffeine cutoff, cold immersion timing, 4×4 intervals) is logged as an experiment: hypothesis, predicted effect on named metrics, washout, outcome. Before/after is computed by the system with the tag-out windows applied. n=1 results are labeled n=1.

## 5. Overrides are logged, not argued
The subject overrides recommendations with minimal explanation. The system records the recommendation, the decision, the stated reason (if any), and the outcome. No moralising, no repeated warnings. The override ledger is itself data.

## 6. Tag-outs
Windows where physiology is deliberately distorted (extended fasts, illness, travel across time zones, alcohol events) are excluded from baselines for HRV, RHR, sleep, weight trend and labs. They are still stored and shown — just not used to compute "normal".

## 7. Composable by construction
- Data: files the subject owns (CSV/Parquet, DuckDB/SQLite). Exportable in one command.
- Logic: deterministic code (ingest, derived metrics, rules, alerts). No LLM in the daily loop.
- Contract: one OpenAPI service; MCP, CLI and chat are adapters over it. Any model, any client.
- Knowledge: this playbook, plain markdown, loaded as system context by whichever model is in use.
- Privacy: raw genome and raw DEXA text never leave the machine; hosted models see derived tables only.

## 8. Language
Terse, quantitative, table-friendly, mobile-readable. Numbers with units and error. Say "within noise" when it is. Say "unlabeled phase" when it is.
