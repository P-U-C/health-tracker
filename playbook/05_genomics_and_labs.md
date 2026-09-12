# 05 — Genomics and labs: the slow tiers

The system's differentiator: DNA sets **priors** (Tier 0), blood panels and DEXA are **ground truth** (Tier 1), and daily wearables are **calibrated proxies** (Tier 2). Each new Tier-1 result recalibrates Tier 2 and tests a Tier-0 prior. Nothing in Tier 0 issues a directive by itself.

---

## Part 1 — Blood panels (NiaHealth-style, semi-annual)

NiaHealth's membership structure (Canada): a 60+ biomarker panel drawn in month 1 and again at month 6, accredited labs (Dynacare/LifeLabs), a clinician review, optional add-ons (hormone panel, omega-3 index, advanced thyroid, DEXA, VO2max, CGM, microbiome). The system treats each draw as a Tier-1 anchor and ingests it via `data/templates/labs_template.csv` (manual entry from the dashboard or PDF parse — NiaHealth's own dashboard is not the system of record; the DB is).

### 1.1 Draw protocol (enforced as a checklist the day before)
- Morning 08:00–10:00, 10–12 h fasted, water only; usual sleep the night before.
- **No training for 48 h** (CK, AST/ALT, hs-CRP, ferritin, creatinine, WBC are exercise-sensitive); no extended fast within 14 days; no alcohol 72 h; stop biotin-containing supplements 72 h (immunoassay interference).
- Creatine stays on — expect creatinine +10–20 %; interpret kidney function on **cystatin C eGFR**.
- Same lab, same time of day, every draw. Schedule 1–2 weeks after the quarterly DEXA inside the same clean window.
- Record: fasting hours, sleep last night, days since last hard session, days since last fast, current phase.

### 1.2 Core panel — what to track, SI units as Canadian labs report them, and the optimization target the system scores against
Targets are the ranges commonly used in preventive/longevity practice for a healthy 41-year-old male, **not clinical thresholds**. The lab's reference interval and the clinician's judgement prevail for any medical decision; the system only computes "distance to target" and "change vs last draw".

| domain | analyte | unit | target (optimisation) | notes |
|---|---|---|---|---|
| Lipids / CVD | ApoB | g/L | < 0.80 (aggressive < 0.60) | primary lipid marker; tighten if APOE ε4 or high CAD PRS |
| | LDL-C, non-HDL-C, total-C, HDL-C | mmol/L | LDL < 2.0, non-HDL < 2.6, HDL > 1.0 | |
| | Triglycerides (fasting) | mmol/L | < 1.1 | links to VAT, insulin, GCKR/APOA5 |
| | Lp(a) | nmol/L | < 75 | **once**; genetic, changes CVD prior permanently |
| Inflammation | hs-CRP | mg/L | < 1.0 | exercise/illness sensitive — check the 48 h rule |
| Glucose / insulin | HbA1c | % | < 5.4 | |
| | fasting glucose | mmol/L | < 5.3 | |
| | fasting insulin → HOMA-IR | pmol/L | insulin < 60 (≈ 10 µIU/mL); HOMA-IR < 1.5 | HOMA-IR = glucose(mmol/L) × insulin(µIU/mL) / 22.5 |
| Liver | ALT, AST, GGT, ALP, bilirubin | U/L, µmol/L | ALT < 25, GGT < 25 | ALT/GGT track VAT; bilirubin ↑ benign if UGT1A1*28 |
| Kidney | creatinine, cystatin C, eGFR, urea, uric acid | µmol/L, mg/L | cystatin-C eGFR > 90; uric acid < 360 µmol/L | creatinine inflated by creatine |
| Thyroid | TSH, free T4, free T3 | mIU/L, pmol/L | TSH 0.5–2.5; fT3 mid-range | low fT3 = deficit signature |
| Hormones (add-on) | total testosterone, SHBG, free T (calc), estradiol, cortisol AM, DHEA-S | nmol/L, pmol/L | T upper half of range for age; SHBG 20–50 | deficit signature: ↓T, ↑SHBG, ↓fT3 |
| Iron / blood | ferritin, iron, TIBC/transferrin sat, CBC (Hb, MCV, RDW, WBC, platelets) | µg/L, % | ferritin 50–150; sat 25–45 % | HFE status changes interpretation |
| Vitamins / minerals | 25-OH vitamin D, B12, folate, magnesium (serum; RBC if offered), zinc | nmol/L, pmol/L | D 75–125; B12 > 400 | serum Mg is a poor status marker |
| Metabolic | homocysteine, omega-3 index (add-on), apoA1 | µmol/L, % | homocysteine < 10; omega-3 index > 8 % | MTHFR/FADS1 priors apply |
| Muscle | CK, albumin | U/L, g/L | CK inside ref. when rested | the post-fast symptom panel (2026-09) belongs here |

### 1.3 Analysis on every draw
1. **Reference change value (RCV)** per analyte: RCV = √2 × 1.96 × √(CVa² + CVi²), CVi from the EFLM biological variation database, CVa from the lab. A delta is a signal only when |Δ| > RCV. Report every delta in RCV units.
2. **Distance to target** in units of RCV; ranked.
3. **Personal reference interval** after three draws.
4. **Context join**: phase at draw, 7-day training load, 30-day sleep median, days since fast, weight trend, current supplements — stored with the draw so a change is never read without its context.
5. **Cross-link tests** (computed, reported with effect size): VAT/trunk fat ↔ TG, insulin, ALT, GGT · training load ↔ CK, AST, hs-CRP, ferritin · sleep ↔ cortisol, hs-CRP, HbA1c · deficit phases ↔ fT3, SHBG, testosterone.
6. **Prior update**: each result tests the relevant Tier-0 prior (e.g. an APOE ε4 prior is "confirmed relevant" if ApoB is above target on a normal diet; "dormant" if not).

### 1.4 Cadence (annual calendar)
| test | cadence | anchor |
|---|---|---|
| Core panel + hormones | every 6 months | 1–2 weeks after the Mar/Sep DEXA (or Dec/Jun) |
| Lp(a) | once | first draw |
| Omega-3 index | annually | with a core panel |
| Lab VO2max (gas exchange) | annually | calibrates the Apple estimator |
| CGM, 14 days | once; repeat only on a flag | during a maintenance phase, normal diet |
| DEXA | quarterly (BodyStats Hologic) | do **not** mix in another provider's machine (Hologic vs GE Lunar differ systematically) |
| Blood pressure | monthly, home cuff, seated, 3 readings | stored as a Tier-2 stream |

---

## Part 2 — Genome (once, then reused forever)

### 2.1 Input and handling
- Preferred: 30× WGS → VCF (+ CRAM). Acceptable: genotyping array raw file (23andMe/Ancestry-style TSV) — far fewer variants, no rare-variant calls.
- Storage: encrypted at rest (age/gpg), outside the DB. Only the derived tables (`genomics_variants`, `genomics_prs`, `genomics_priors`) enter the DB. **Raw genome never enters an LLM context, hosted or local.**
- Pipeline: `bcftools norm` → extract the curated panel below (`bcftools view -i ID=@panel.txt` or position lookup) → PRS via `pgsc_calc` (PGS Catalog, ancestry-matched reference for percentiles) → `genomics_priors.csv`.

### 2.2 Curated panel — what to look up and what it changes
Evidence grade: **A** = clinical/PGx guideline (CPIC/ACMG) or monogenic; **B** = replicated large-GWAS association with meaningful effect; **C** = candidate-gene, small or inconsistent effect. Only A/B priors adjust targets. C priors may only spawn n=1 experiments.

| domain | gene / variant | grade | what it changes in the system |
|---|---|---|---|
| Lipids / CVD | APOE ε2/ε3/ε4 (rs429358, rs7412) | B | ε4: ApoB target → aggressive; saturated-fat sensitivity prior; add a diet experiment |
| | LPA rs10455872, rs3798220 | B | flags likely high Lp(a) — measure directly (the measurement wins) |
| | PCSK9 rs11591147 (R46L), LDLR/APOB rare variants (ClinVar pathogenic → FH) | A | FH variant → clinical referral flag, ApoB target aggressive |
| | 9p21 rs1333049; CAD PRS (PGS Catalog) | B | high PRS → tighten ApoB/LDL targets, earlier CAC discussion with clinician |
| | APOA5 rs662799, GCKR rs1260326 | B | TG interpretation; carb-sensitivity prior |
| Glucose | TCF7L2 rs7903146; T2D PRS | B | tighten HbA1c/insulin targets; promote the CGM trial |
| Liver / VAT | PNPLA3 rs738409 | B | ALT/GGT and VAT weighted more; alcohol prior |
| Appetite / weight | FTO rs9939609, MC4R rs17782313 | B/C | appetite-regulation prior → protein/fibre emphasis; n=1 satiety experiment |
| Caffeine / sleep | CYP1A2 rs762551 (AA fast; C carrier slow) | B | slow → caffeine cutoff experiment (sleep is the constraint: this is the highest-value link) |
| | ADORA2A rs5751876, CLOCK rs1801260, COMT rs4680 | C | sleep-timing / caffeine-sensitivity experiments only |
| Iron | HFE rs1800562 (C282Y), rs1799945 (H63D); TMPRSS6 rs855791 | A / B | HFE: ferritin interpretation + iron supplement prohibition; TMPRSS6: iron-deficiency tendency |
| Bilirubin | UGT1A1*28 (tag rs887829) | A | Gilbert's → elevated bilirubin is benign, do not chase |
| Nutrients | MTHFR rs1801133/rs1801131; FADS1 rs174546; LCT rs4988235; GC rs2282679, CYP2R1 rs10741657; FUT2 rs601338, TCN2 rs1801198 | B/C | folate form, homocysteine weighting; omega-3 conversion (favours EPA/DHA direct); lactase; vitamin D dose prior; B12 target |
| Celiac risk | HLA-DQ2.5 (rs2187668), DQ8 (rs7454108) | B | only if GI symptoms; absent haplotypes ≈ rules out |
| Pharmacogenomics | SLCO1B1 rs4149056 (statin myopathy), CYP2C19 *2/*17, CYP2D6 (needs CNV-aware caller), VKORC1 rs9923231, HLA-B*57:01 | A | stored for clinician conversations; SLCO1B1 matters if ApoB ever needs a statin |
| Muscle / performance | ACTN3 rs1815739, ACE I/D (tag rs4341), PPARGC1A rs8192678 | C | fibre-type prior only; may bias which rep-scheme rotation to test first; never changes the program |
| Longevity | FOXO3 rs2802292 | C | recorded, not used |

Honest framing: nutrigenomics and "fitness genes" are weak. The actionable value of sequencing for this system is (1) pharmacogenomics and monogenic lipid/iron findings, (2) polygenic risk that tightens lab targets, (3) the caffeine-metabolism × sleep-constraint link. Everything else is an experiment generator.

### 2.3 `genomics_priors` — the table the rest of the system reads
`domain, gene, rsid, genotype, effect, evidence_grade, applies_to (analyte | metric | experiment), adjustment (e.g. "apob_target: 0.60"), status (dormant | active | confirmed | refuted), tested_by (lab draw id / experiment id)`.

Rules: a prior becomes **active** only when a Tier-1 measurement is consistent with it; **refuted** when two consecutive measurements contradict it; C-grade priors never leave *dormant* except to create an experiment.

---

## Part 3 — How the tiers loop together (the analysis that is actually different)
1. **Genome → targets**: priors adjust the per-analyte targets in 1.2 and the weights in the constraint scan.
2. **Labs → calibration**: fT3/SHBG/testosterone confirm or deny that a "maintenance" phase was a deficit; CK/hs-CRP/ferritin test whether training load is being recovered from; TG/insulin/ALT test whether VAT reduction is metabolically real.
3. **DEXA → scale**: every scan recalibrates the Eufy offset and the Watch energy-expenditure correction.
4. **Scale/Watch → phase**: tripwires and band margins drive the only daily decisions.
5. **Everything → constraint**: quarterly, the binding constraint is re-identified with all tiers as evidence.
6. **Experiments close the loop**: each prior and each intervention has a named metric and a date; the ledger records whether the prediction held.
