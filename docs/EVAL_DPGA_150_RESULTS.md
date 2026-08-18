# Evaluation Report — UNSDG Classifier on Real DPG Ground Truth

Run with `backend/tests/eval_dpga_150.py` against the 141 labeled DPGs in
`dpgs.csv.xlsx` (multi-label SDG ground truth) plus a 150-project aux sample from
`OpenSustain.tech-Projects (1).csv.xlsx`. Full per-project predictions and the raw
metrics are in `backend/.eval_cache/report_<timestamp>.json` and
`predictions_<timestamp>.csv`.

- Evaluated set: **118 of 141** labeled DPGs classified successfully (83.7% coverage; 23 dropped — see [Limitations](#limitations)).
- Task: **multi-label** classification — a project may belong to several SDGs. Ground-truth density ≈ 2.39 SDGs/project.
- Production config tested: `main()` threshold **0.7**, `top_k=10`, ensemble `alpha=0.3`
  (30% GE-Lab zero-shot + 70% embedding-cosine), `COSINE_LOW/HIGH = 0.27/0.34`.
  `app.py` additionally filters predictions `> 0.4` (redundant — `main()` already gates at 0.7).

---

## 1. Executive summary

1. **The pipeline is wired correctly.** `classify_repo` feeds the **LLM summary** (not raw
   README) into the classifier in **118/118** projects — the pipeline-integrity check passed
   for every project.
2. **Overall accuracy is modest.** Micro **F1 = 0.421** (P=0.361, R=0.504) at the current
   0.7 threshold. The model over-predicts: **3.33 SDGs/project** predicted vs 2.39 true.
3. **The embedding component is overweighted.** The developer's `alpha=0.3` (70% weight on
   the raw cosine-embedding signal) is suboptimal. **Pure zero-shot (`alpha=1.0`) beats it**
   (micro-F1@0.7 = 0.498 vs 0.421), and jointly-optimal `alpha≈0.7–0.9` reaches **~0.50–0.52**
   micro-F1. This is the single most actionable improvement.
4. **The global threshold is near-optimal but poorly matched to individual SDGs.** Global
   F1-optimal threshold is **0.80** (micro-F1 0.444), close to the dev 0.7 — but per-SDG
   optima range from **0.04 (SDG 9) to 0.90 (SDG 14)**. A single threshold can never serve
   all 17 SDGs; several common, important SDGs are systematically under-scored and missed.
5. **Confidence scores are not probabilities.** Calibration ECE = 0.13; a "70–90%" score has
   only ~18–36% true positive rate. Scores are good for **ranking** (AUCs mostly 0.7–0.9) but
   their absolute magnitude is inflated.
6. **The LLM summaries are structurally conformant but imperfect.** Word/sentence counts are
   within spec and there are **zero** SDG-number leaks, but **61/118 summaries still contain
   technical noise** (python/react/docker/api) and ~22 summary words per project are not found
   in the source README (paraphrase or possible hallucination).

**Bottom line:** the ranking signal (AUC) is decent, but the current operating point leaves
real accuracy on the table. Rebalancing the ensemble toward the zero-shot model and using
per-SDG thresholds (or at least a higher global threshold) are the highest-impact changes.

---

## 2. Per-SDG metrics @ dev threshold 0.7 (top_k 10)

| SDG | n+ | TP | FP | FN | Prec | Rec | F1 | AUC |
|-----|----|----|----|----|------|-----|----|-----|
| SDG 1 (No Poverty) | 14 | 8 | 13 | 6 | 0.381 | 0.571 | 0.457 | 0.793 |
| SDG 2 (Zero Hunger) | 11 | 9 | 23 | 2 | 0.281 | 0.818 | 0.419 | 0.852 |
| SDG 3 (Good Health) | 42 | 29 | 13 | 13 | 0.690 | 0.690 | 0.690 | 0.907 |
| SDG 4 (Quality Education) | 25 | 9 | 11 | 16 | 0.450 | 0.360 | 0.400 | 0.677 |
| SDG 5 (Gender Equality) | 12 | 3 | 5 | 9 | 0.375 | 0.250 | 0.300 | 0.697 |
| SDG 6 (Clean Water & Sanitation) | 8 | 5 | 27 | 3 | 0.156 | 0.625 | 0.250 | 0.751 |
| SDG 7 (Affordable Clean Energy) | 3 | 2 | 10 | 1 | 0.167 | 0.667 | 0.267 | 0.872 |
| SDG 8 (Decent Work & Growth) | 15 | 6 | 20 | 9 | 0.231 | 0.400 | 0.293 | 0.717 |
| SDG 9 (Industry & Innovation) | 35 | 13 | 33 | 22 | 0.283 | 0.371 | 0.321 | 0.501 |
| SDG 10 (Reduced Inequalities) | 17 | 5 | 20 | 12 | 0.200 | 0.294 | 0.238 | 0.634 |
| SDG 11 (Sustainable Cities) | 17 | 10 | 20 | 7 | 0.333 | 0.588 | 0.426 | 0.819 |
| SDG 12 (Responsible Consumption) | 9 | 6 | 14 | 3 | 0.300 | 0.667 | 0.414 | 0.890 |
| SDG 13 (Climate Action) | 16 | 12 | 11 | 4 | 0.522 | 0.750 | 0.615 | 0.907 |
| SDG 14 (Life Below Water) | 2 | 2 | 5 | 0 | 0.286 | 1.000 | 0.444 | 0.978 |
| SDG 15 (Life on Land) | 5 | 2 | 8 | 3 | 0.200 | 0.400 | 0.267 | 0.935 |
| SDG 16 (Peace & Institutions) | 30 | 15 | 5 | 15 | 0.750 | 0.500 | 0.600 | 0.805 |
| SDG 17 (Partnerships) | 21 | 6 | 13 | 15 | 0.316 | 0.286 | 0.300 | 0.671 |
| **Micro** | | | | | **0.361** | **0.504** | **0.421** | |
| **Macro** | | | | | **0.348** | **0.543** | **0.394** | |

### Interpretation

- **Strong SDGs:** SDG 3 (F1 0.69), SDG 13 (0.62), SDG 16 (0.60). These have clear,
  specific domain vocabulary and the model separates them well (AUC 0.90+).
- **Weak SDGs (high recall, awful precision):** SDG 6 (P 0.156), SDG 7 (0.167), SDG 8 (0.231),
  SDG 2 (0.281), SDG 9 (0.283). These are predicted far too liberally — most flagged projects
  are false positives. SDG 6 (Water/Sanitation) has the worst precision (0.156): 27 FPs.
- **Weak SDGs (both low):** SDG 10 (P 0.20, R 0.29), SDG 17 (P 0.32, R 0.29), SDG 5 (R 0.25),
  SDG 4 (R 0.36). These are **under-predicted** (low recall) — genuinely relevant projects are
  missed.
- **AUC tells a different story than F1.** SDG 9 has **AUC ≈ 0.50 (random)** — the model cannot
  rank SDG 9 at all despite a healthy count of positives (35). This "Industry, Innovation &
  Infrastructure" SDG is the hardest. High AUCs on SDG 14/15/7/13 are on very small positive
  samples and should be read with caution.

---

## 3. Threshold analysis (ensemble alpha = 0.3)

| thr | microP | microR | microF1 | macroF1 | avgPreds |
|-----|--------|--------|---------|---------|----------|
| 0.00 | 0.141 | 1.000 | 0.246 | 0.236 | 17.00 |
| 0.10 | 0.254 | 0.826 | 0.389 | 0.353 | 7.77 |
| 0.20 | 0.288 | 0.745 | 0.416 | 0.379 | 6.17 |
| 0.30 | 0.296 | 0.649 | 0.407 | 0.374 | 5.24 |
| **0.40** (app filter) | 0.307 | 0.614 | 0.409 | 0.377 | 4.77 |
| **0.50** (classify default) | 0.320 | 0.571 | 0.410 | 0.377 | 4.26 |
| 0.60 | 0.338 | 0.546 | 0.417 | 0.387 | 3.86 |
| **0.70** (main) | 0.361 | 0.503 | 0.421 | 0.394 | 3.33 |
| **0.80** (optimal micro & macro) | 0.595 | 0.355 | **0.444** | **0.408** | 1.42 |
| 0.90 | 0.729 | 0.277 | 0.401 | 0.364 | 0.91 |
| 1.00 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 |

### Interpretation

- **The dev threshold 0.7 is close to but not exactly the F1 optimum.** Both micro- and
  macro-F1 peak at **0.80** (0.444 / 0.408 vs 0.421 / 0.394 at 0.7). The gain is modest
  (+0.023 micro-F1).
- **The F1 optimum is not necessarily a good operating point.** Raising to 0.80 drops recall
  from 0.503 to 0.355 and predictions from 3.33 to **1.42 SDGs/project** — far below the 2.39
  ground-truth average. That trade-off only makes sense if the app prefers very few, high-precision
  suggestions over completeness. For a "surface candidate SDGs for human review" tool, **recall
  matters more**, so 0.7 (or even 0.6) is a defensible choice despite being slightly below the
  F1 peak.
- **App filter `> 0.4` is a no-op** in the real flow: `main()` already drops everything below
  0.7, so the 0.4 gate in `app.py` never re-adds anything. It only matters if the threshold in
  `classify_repo` is lowered below 0.4.
- **Over-prediction is structural.** Even at 0.7 the model emits 3.33 predictions vs 2.39 true
  labels; precision (0.36) is the weak leg. To improve precision you must raise the threshold
  substantially (0.75–0.85), accepting a recall penalty.

### Per-SDG optimal thresholds (1% grid)

| SDG | n+ | best_t | F1@best | |
|-----|----|--------|---------|---|
| SDG 9 (Industry & Innovation) | 35 | **0.04** | 0.467 | |
| SDG 10 (Reduced Inequalities) | 17 | **0.13** | 0.361 | |
| SDG 8 (Decent Work) | 15 | **0.22** | 0.400 | |
| SDG 3 (Good Health) | 42 | **0.26** | 0.757 | |
| SDG 17 (Partnerships) | 21 | **0.30** | 0.431 | |
| SDG 6 (Clean Water) | 8 | 0.53 | 0.255 | |
| SDG 5 (Gender Equality) | 12 | 0.62 | 0.348 | |
| SDG 13 (Climate Action) | 16 | 0.71 | 0.649 | |
| SDG 12 (Consumption) | 9 | 0.73 | 0.476 | |
| SDG 16 (Peace & Institutions) | 30 | 0.74 | 0.612 | |
| SDG 4 (Quality Education) | 25 | 0.77 | 0.514 | |
| SDG 7 (Clean Energy) | 3 | 0.77 | 0.400 | |
| SDG 11 (Sustainable Cities) | 17 | 0.78 | 0.581 | |
| SDG 1 (No Poverty) | 14 | 0.82 | 0.609 | |
| SDG 15 (Life on Land) | 5 | 0.83 | 0.500 | |
| SDG 2 (Zero Hunger) | 11 | 0.81–0.90 | 0.526 | |
| SDG 14 (Life Below Water) | 2 | **0.90** | 0.667 | |

The spread (0.04 → 0.90) is the key insight: **no single threshold fits all SDGs.** The common
"broad" SDGs (3, 8, 9, 10, 17) are best captured at very low thresholds (0.04–0.30), meaning the
classifier consistently **under-scores** them — a single 0.7 gate silently kills most of these.
The narrow/environmental SDGs (14, 15, 1) only fire at high scores. **Recommended:** per-SDG
thresholds, or at minimum a per-SDG score normalization before applying a common cut.

---

## 4. Ensemble / alpha analysis (threshold fixed at 0.7)

`score = alpha * zero_shot + (1 - alpha) * embedding_cosine`

| alpha | microF1@0.7 | macroF1@0.7 | bestMicroF1 | bestT |
|-------|-------------|-------------|-------------|-------|
| 0.0 (pure embedding) | 0.410 | 0.376 | 0.418 | 0.95 |
| 0.2 | 0.410 | 0.379 | 0.448 | 0.85 |
| **0.3 (dev)** | 0.421 | 0.394 | 0.444 | 0.80 |
| 0.5 | 0.459 | 0.418 | 0.459 | 0.70 |
| 0.7 | 0.452 | 0.393 | **0.520** | 0.55 |
| 0.8 | 0.489 | 0.421 | 0.517 | 0.60 |
| 0.9 | **0.504** | **0.443** | 0.510 | 0.60 |
| 1.0 (pure zero-shot) | 0.498 | 0.443 | 0.504 | 0.45 |

### Interpretation

- **The developer under-weights the better model.** At the dev `alpha=0.3`, the raw cosine
  embedding similarity gets a 70% weight — yet it is clearly the weaker of the two signals.
  **`alpha=1.0` (pure GE-Lab zero-shot) already outperforms the dev ensemble** at the same 0.7
  threshold: 0.498 vs 0.421 micro-F1 (+18% relative).
- **Jointly-optimal: `alpha≈0.7`, threshold ≈ 0.55 → micro-F1 0.520.** That is ~0.10 higher than
  the current 0.421 — the largest single lever in this report.
- **Recommendation:** raise `alpha` to **0.7–0.9** (and, if you want the joint optimum, lower
  the threshold toward 0.55–0.60). The embedding signal is still marginally useful as a tie-breaker
  (best = 0.52 at alpha 0.7 vs 0.50 pure), but it should not dominate.

---

## 5. Calibration & reliability

- **ECE = 0.131** (13%). For a binary/multi-label decision the model is **over-confident**:
  scores in 0.5–0.9 predict far more true positives than actually occur.

| score bin | n | predicted | empirical | gap |
|-----------|----|-----------|-----------|-----|
| 0.00–0.10 | 1089 | 0.05 | 0.045 | 0.005 |
| 0.10–0.20 | 189 | 0.15 | 0.122 | 0.028 |
| 0.20–0.30 | 110 | 0.25 | 0.245 | 0.004 |
| 0.30–0.40 | 55 | 0.35 | 0.182 | 0.168 |
| 0.40–0.50 | 60 | 0.45 | 0.200 | 0.250 |
| 0.50–0.60 | 47 | 0.55 | 0.149 | 0.401 |
| 0.60–0.70 | 63 | 0.65 | 0.191 | 0.460 |
| 0.70–0.80 | 225 | 0.75 | 0.187 | 0.563 |
| 0.80–0.90 | 61 | 0.85 | 0.361 | 0.489 |
| 0.90–1.00 | 107 | 0.95 | 0.729 | 0.221 |

- A predicted 0.70–0.80 has only an **18.7%** true-positive rate; even 0.90–1.00 is only ~73%.
  Only scores ≥0.95 are reasonably trustworthy.
- **Reliability:** mean score on true positives = **0.568** vs negatives = **0.226** — clear
  separation on average, but the score distributions overlap heavily (which is why precision is
  low despite decent AUCs). Avg predictions/project = 3.33 vs 2.39 true.
- **AUC summary:** ranking quality is decent (most 0.7–0.9), excellent for the small-sample
  SDGs 14/15/7, and **random for SDG 9 (0.501)**. Ranking (argmax / top-k) is a much more
  defensible use of these scores than reading them as calibrated probabilities.

---

## 6. Pipeline integrity — does the pipeline use the LLM summary?

**118/118 projects** — `classify_repo`'s output scores match, bit-for-bit, scores re-derived
from the cached LLM summary through the same zero-shot + embedding path. This proves:

- The summary produced by `summarize_for_sdg` is the text actually fed to the GE-Lab classifier
  (not the raw README).
- The description-priority, truncation, and ensemble arithmetic are wired as intended.

No wiring defect found. (An earlier design concern — that the raw README might bypass the LLM —
is ruled out.)

---

## 7. LLM summary quality & hallucination risk (n = 118)

| metric | value | spec / concern |
|--------|-------|----------------|
| avg word count | 94.3 | in 80–160 target |
| avg sentence count | 5.7 | in 4–6 target |
| avg word overlap with source | 0.550 | 45% of summary words not in README |
| avg relevance cosine (summary vs README) | 0.545 | moderate semantic similarity |
| avg out-of-vocabulary words / project | 22.3 | paraphrase or possible hallucination |
| projects with SDG-number leak | 0 | prompt respected |
| projects with technical noise | **61** | prompt not followed (python/react/docker/api…) |
| projects with numeric claims not in source | 7 | potential hallucination of numbers |
| NO_SDG_SIGNAL emitted | 0 | none flagged non-relevant |
| Insufficient-documentation fallback | 0 | none triggered |

### Interpretation

- **Structurally conformant:** length and sentence counts are inside spec, and the LLM never
  leaks SDG numbers (the "never mention SDG" instruction holds).
- **Moderate faithfulness:** only ~55% of summary content words appear in the source README and
  semantic relevance is ~0.55. Some of this is legitimate rephrasing (the prompt asks for a
  distilled, non-technical rewrite), but **~22 out-of-vocabulary words/project is the hall/toxic
  paraphrase signal** worth manual spot-checking.
- **Technical-noise instruction is frequently violated (61/118).** Even though the prompt says to
  ignore programming languages/frameworks/CI, over half the summaries still contain them. This
  dilutes the SDG signal for generic tech projects and inflates false positives on broad SDGs
  like 9.
- **7 summaries contain numeric claims not present in the source** — a classic hallucination
  signature. These are flagged in the report (`flags`) for manual review.

---

## 8. Recommendations (priority order)

1. **Rebalance the ensemble — raise `alpha` to ~0.7–0.9** in `classify_repo`'s
   `ensemble_scores(zs, es, alpha=0.3)` call. Expected micro-F1 gain ≈ +0.08–0.10 at the same
   threshold. This is the single highest-value change and is a one-line edit.
2. **Move to per-SDG thresholds.** The global 0.7 misses most of SDGs 3, 8, 9, 10, 17 (optimal
   thresholds 0.04–0.30). Either add a per-SDG threshold vector or per-SDG normalize scores.
   Without this, a single gate cannot be right for all 17 goals.
3. **If a single threshold must be kept:** 0.70 is reasonable for a recall-oriented UI (F1 0.421);
   raise to **0.80** only if the app wants high-precision, few-suggestion output (F1 0.444, but
   only 1.42 SDGs/project). Do **not** rely on `app.py`'s `> 0.4` filter — it's redundant.
4. **Treat scores as rankings, not probabilities.** Surface top-k (e.g., top-3) suggestions and
   hide/calibrate absolute confidence, since ECE ≈ 0.13 and mid-range scores are over-confident.
5. **Fix the summariser prompt adherence:** 61/118 summaries still contain technical noise.
   Add a post-hoc filter on the summary (strip the `_TECH_NOISE` vocabulary) or reinforce the
   instruction; this should improve precision on broad SDGs (esp. SDG 9).
6. **Manually audit the 7 numeric-claim summaries** and any with word-overlap < 0.6
   (recorded in `report["flags"]`) before trusting summaries for downstream claims.
7. **Investigate SDG 9 separately** — AUC ≈ 0.50 (random). Its SDG_DESCS/label text may need
   reworking, or it may need to be dropped/split.

---

## 9. Limitations

- **Coverage:** 118/141 labeled DPGs (83.7%). The 23 dropped projects (fetch failures / rate
  limits / renamed or private repos) are not included; their exclusion may bias the metrics,
  especially if failures correlate with repo age/size.
- **Small positive samples:** SDG 14 (2), SDG 7 (3), SDG 15 (5), SDG 6 (8), SDG 2 (11), SDG 5 (12)
  have few positives; their P/R/F1 and AUC (0.978, 0.935, 0.872) are noisy and shouldn't be
  over-interpreted.
- **Ground-truth source:** DPGA registry flags are the reference labels; they are expert-tagged
  but not exhaustive, and may under/over-count SDGs for a given project.
- **Live dependencies:** results depend on the GE-Lab microservice, live repo fetches, and Groq
  summaries at run time. Reproduce with `python backend/tests/eval_dpga_150.py --offline`
  after the first cached run.
- **Multi-label nuance:** F1 here is computed per-SDG (micro/macro over SDG-instances), so a
  project correctly contributing to 2 SDGs counts twice. This is the correct frame for a
  multi-label tool but differs from "top-1 hit rate".