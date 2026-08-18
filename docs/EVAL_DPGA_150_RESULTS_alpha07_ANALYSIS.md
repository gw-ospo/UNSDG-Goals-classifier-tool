# UNSDG Classifier — Alpha 0.7 vs Alpha 0.3 Evaluation Comparison

**Same dataset, different ensemble weight.** Both runs evaluate the identical
**118 of 141 labeled DPGs** (per-SDG positive counts `n+` match exactly across
all 17 goals; 282 total positive SDG-instances), so every number below is a
clean apples-to-apples comparison of the two ensemble operating points:

- **Old run** (`docs/EVAL_DPGA_150_RESULTS.md`): `DEV_ALPHA = 0.3`
  → `score = 0.3·zero_shot + 0.7·embedding_cosine`
- **New run** (this analysis): `DEV_ALPHA = 0.7`
  → `score = 0.7·zero_shot + 0.3·embedding_cosine`
  (this is what production `embedding_url.py` already applies)

---

## 1. Executive summary

1. **The report's headline prediction is now empirically confirmed.** The old
   report (§4) projected the joint optimum at **alpha≈0.7, threshold≈0.55 →
   micro-F1 0.520**. The new run measures exactly that: **micro-F1 = 0.520 at
   threshold 0.55**. Production is already at the optimal *alpha* — only the
   threshold (0.7 → 0.55) is left on the table.
2. **At the dev threshold 0.7, the pipeline got *better* on F1 but swung from
   over-prediction to under-prediction.** micro-F1 0.421 → **0.452**
   (precision 0.361 → **0.660**), but recall 0.504 → **0.344** and
   predictions/project 3.33 → **1.25** (ground truth 2.39).
3. **The global F1-optimum threshold moved and improved.** Old best: 0.444 @
   0.80. New best: **0.520 @ 0.55** (+0.076 micro-F1), with avg 2.04
   predictions/project — close to the 2.39 ground truth. This is the most
   actionable single change.
4. **The shipped `PER_SDG_THRESHOLDS` are now stale and actively harmful.**
   Derived at alpha 0.3, they applied to the alpha-0.7 scores give micro-F1
   **0.434** — *worse than a plain global 0.7 (0.452)* — and over-predict at
   4.02 SDGs/project. They must be re-derived at alpha 0.7.
5. **The per-SDG threshold spread collapsed.** Optimal gates went from
   **0.04–0.90** (alpha 0.3) to **0.17–0.76** (alpha 0.7). The "no single
   threshold fits all 17 SDGs" story weakens: at alpha 0.7 a single 0.55 gate
   captures most of the value, though re-derived per-SDG gates still add macro-F1
   (~0.54 vs 0.464).
6. **Ranking quality improved broadly.** Most AUCs rose (SDG 3: 0.907→0.953,
   SDG 2: 0.852→0.873, SDG 13: 0.907→0.926, SDG 1: 0.793→0.806); **SDG 9
   stopped being random** (0.501 → 0.567), though it remains the worst.
7. **SDG 6 (Clean Water & Sanitation) collapsed.** 5 TP → **0 TP** at 0.7
   (F1 0.250 → 0.000). Even its fresh optimal gate (0.38) only reaches F1 0.273.
   It is the new priority failure case.
8. **Calibration: better at the top, marginally worse overall.** High bins now
   track reality much better (0.70–0.80 bin empirical TPR 18.7% → **41.4%**;
   0.80–0.90 → **61.0%**), but ECE rose 0.131 → **0.140** because far more
   instances now sit in the poorly-calibrated 0.10–0.30 range (n≈1001).

---

## 2. Headline numbers

| Metric | Alpha 0.3 (old) | Alpha 0.7 (new) | Δ |
|---|---|---|---|
| micro-F1 @ 0.7 | 0.421 | **0.452** | +0.031 |
| micro-Precision @ 0.7 | 0.361 | **0.660** | +0.299 |
| micro-Recall @ 0.7 | 0.504 | 0.344 | −0.160 |
| macro-F1 @ 0.7 | 0.394 | 0.393 | ~0 |
| avg predictions/project @ 0.7 | 3.33 | **1.25** | −2.08 |
| Best global micro-F1 (threshold) | 0.444 (0.80) | **0.520 (0.55)** | +0.076 |
| Best global macro-F1 (threshold) | 0.408 (0.80) | **0.464 (0.55)** | +0.056 |
| Total TP / FP / FN @ 0.7 | 142 / 251 / 140 | 97 / **50** / 185 | FP −80% |
| Per-SDG optimal-gate spread | 0.04 – 0.90 | **0.17 – 0.76** | narrowed |
| ECE | 0.131 | 0.140 | +0.009 |
| mean score (positives / negatives) | 0.568 / 0.226 | 0.555 / 0.235 | ~same |

**Interpretation of the totals:** the FP flood at alpha 0.3 (251 FPs, e.g. SDG 6
= 27 FP, SDG 9 = 33 FP, SDG 2 = 23 FP) is essentially gone at alpha 0.7 (50 FPs
total). The embedding-cosine signal — inflated by its `COSINE_LOW/HIGH` remap to
0–1 — was the driver of false positives. The cost is lost recall: 97 vs 142 TPs.

---

## 3. Threshold sweep — the optimum moved and improved

| | Alpha 0.3 (old) | Alpha 0.7 (new) |
|---|---|---|
| Best micro-F1 | 0.444 @ 0.80 | **0.520 @ 0.55** |
| Best macro-F1 | 0.408 @ 0.80 | **0.464 @ 0.55** |
| P/R at optimum | 0.595 / 0.355 | 0.564 / 0.482 |
| avg preds at optimum | 1.42 | **2.04** |
| dev 0.7 row | F1 0.421, 3.33 preds | F1 0.452, 1.25 preds |

Key rows of the new sweep (alpha 0.7):

| thr | microF1 | avgPreds | note |
|---|---|---|---|
| 0.40 | 0.466 | 4.01 | app filter gate |
| 0.45 | 0.505 | 3.11 | |
| 0.50 | 0.509 | 2.48 | classify default |
| **0.55** | **0.520** | 2.04 | **global optimum** |
| 0.60 | 0.515 | 1.82 | |
| 0.70 | 0.452 | 1.25 | current `main()` |

**Insight:** at alpha 0.7 the F1 curve is flat-topped over 0.45–0.60
(F1 ≥ 0.505) — the operating point is forgiving. 0.55 sits at the top and
balances predictions (2.04) almost exactly against the 2.39 ground-truth density.
This is the recommended global setting for the alpha-0.7 pipeline.

---

## 4. Alpha sweep — production already sits at the joint optimum

The alpha-sweep numbers are **identical** between runs (they are computed over
the same cached `zs`/`es` matrices and don't depend on `DEV_ALPHA`); only the
`<- dev` marker moved from alpha 0.3 to alpha 0.7.

| alpha | microF1@0.7 | best microF1 (bestT) |
|---|---|---|
| 0.3 (old dev) | 0.421 | 0.444 (0.80) |
| **0.7 (current dev)** | **0.452** | **0.520 (0.55)** |
| 0.8 | 0.489 | 0.517 (0.60) |
| 0.9 | 0.504 | 0.510 (0.60) |
| 1.0 (pure zero-shot) | 0.498 | 0.504 (0.45) |

**Insight:** alpha 0.7 is the joint optimum (best micro-F1 0.520), beating pure
zero-shot (0.504) — the embedding signal still adds value as a tie-breaker, but
must not dominate. The old report's recommendation #1 (raise alpha to 0.7–0.9)
was *already implemented* in `embedding_url.py`; the eval config was simply
lagging. **No further alpha change is needed — only the threshold.**

---

## 5. Per-SDG @ dev threshold 0.7 — precision up, recall down

| SDG | n+ | F1 old → new | Δ | TP old → new | FP old → new |
|---|---|---|---|---|---|
| 1 | 14 | 0.457 → 0.545 | +0.088 | 8 → 6 | 13 → 2 |
| 2 | 11 | 0.419 → 0.421 | +0.002 | 9 → 4 | 23 → 4 |
| 3 | 42 | 0.690 → **0.789** | +0.098 | 29 → 28 | 13 → 1 |
| 4 | 25 | 0.400 → 0.375 | −0.025 | 9 → 6 | 11 → 1 |
| 5 | 12 | 0.300 → 0.286 | −0.014 | 3 → 2 | 5 → 0 |
| 6 | 8 | 0.250 → **0.000** | −0.250 | 5 → **0** | 27 → 0 |
| 7 | 3 | 0.267 → 0.250 | −0.017 | 2 → 1 | 10 → 4 |
| 8 | 15 | 0.293 → 0.182 | −0.111 | 6 → 2 | 20 → 5 |
| 9 | 35 | 0.321 → 0.298 | −0.023 | 13 → 7 | 33 → 5 |
| 10 | 17 | 0.238 → 0.231 | −0.007 | 5 → 3 | 20 → 6 |
| 11 | 17 | 0.426 → 0.381 | −0.045 | 10 → 4 | 20 → 0 |
| 12 | 9 | 0.414 → 0.462 | +0.048 | 6 → 3 | 14 → 1 |
| 13 | 16 | 0.615 → 0.560 | −0.055 | 12 → 7 | 11 → 2 |
| 14 | 2 | 0.444 → 0.500 | +0.056 | 2 → 1 | 5 → 1 |
| 15 | 5 | 0.267 → **0.500** | +0.233 | 2 → 2 | 8 → 1 |
| 16 | 30 | 0.600 → 0.600 | 0.000 | 15 → 15 | 5 → 5 |
| 17 | 21 | 0.300 → 0.308 | +0.008 | 6 → 6 | 13 → 12 |

**Winners:** SDG 3 (0.690 → 0.789, now the strongest with precision 0.966), SDG 15
(+0.233), SDG 1 (+0.088), SDG 14 (+0.056).
**Unchanged:** SDG 16 (identical TP/FP/FN — the two signals agree perfectly here).
**Losers:** SDG 6 (to zero), SDG 8 (−0.111), SDG 13 (−0.055), SDG 11 (−0.045).

The recurring pattern: alpha 0.7 raises precision to 0.75–1.00 on most goals
(e.g. SDG 3 0.966, SDG 5 1.000, SDG 11 1.000, SDG 1 0.750) while recall drops
(SDG 8 0.133, SDG 4 0.240, SDG 9 0.200). The old run's systematic
false-positive floods (which made SDG 6/7/8/9 precision ~0.16–0.28) are gone.

**SDG 6 (Water & Sanitation) needs a dedicated look.** At alpha 0.3 it was
over-predicted (27 FP). At alpha 0.7 it is invisible (0 TP). Its scores simply
don't rise above 0.7 even on true positives — the zero-shot label text
(`SDG_DESCS[5]`) or the summariser may be the weak link. Its fresh optimal gate
(0.38, F1 0.273) is the worst achievable F1 of any goal.

---

## 6. Per-SDG optimal thresholds — the shipped gates are stale

New per-SDG F1-optimal gates (1% grid, alpha 0.7) vs the shipped
`sdg_constants.PER_SDG_THRESHOLDS` (derived at alpha 0.3):

| SDG | shipped (α0.3) | fresh (α0.7) | Δ | F1@fresh |
|---|---|---|---|---|
| 1 | 0.82 | **0.58** | −0.24 | 0.609 |
| 2 | 0.85 | **0.54** | −0.31 | 0.571 |
| 3 | 0.26 | **0.50** | +0.24 | **0.860** |
| 4 | 0.77 | **0.46** | −0.31 | 0.579 |
| 5 | 0.62 | 0.53 | −0.09 | 0.400 |
| 6 | 0.53 | 0.38 | −0.15 | 0.273 |
| 7 | 0.77 | 0.45 | −0.32 | 0.400 |
| 8 | 0.22 | 0.30 | +0.08 | 0.400 |
| 9 | 0.04 | **0.17** | +0.13 | 0.481 |
| 10 | 0.13 | **0.50** | +0.37 | 0.450 |
| 11 | 0.78 | 0.43 | −0.35 | 0.600 |
| 12 | 0.73 | 0.70 | −0.03 | 0.462 |
| 13 | 0.71 | **0.32** | −0.39 | 0.667 |
| 14 | 0.90 | 0.76 | −0.14 | 0.667 |
| 15 | 0.83 | 0.61 | −0.22 | 0.667 |
| 16 | 0.74 | **0.55** | −0.19 | 0.678 |
| 17 | 0.30 | 0.46 | +0.16 | 0.423 |

**Three observations:**

1. **The extreme gates collapsed.** The two anchors of the old story — SDG 9 at
   **0.04** and SDG 14 at **0.90** — moved to **0.17** and **0.76**. At alpha 0.7
   the fresh gates cluster in a tight 0.30–0.76 band for 14 of 17 SDGs. The
   under-scoring of broad goals (3/8/9/10/17) that justified per-SDG thresholds
   at alpha 0.3 is largely an artifact of the embedding component dragging those
   scores down; with more zero-shot weight they behave more uniformly.
2. **Applying the stale gates to the new scores is actively bad.** The eval's
   "PER-SDG METRICS @ per-SDG thresholds" table is a diagnostic of staleness, not
   a recommendation: it yields micro-F1 **0.434** (P 0.346, R 0.582) with
   **4.02 predictions/project** — *worse than the plain global 0.7 (0.452)* and
   far below the global optimum (0.520). Notable damage: SDG 9 at 0.04 floods 83
   FPs; SDG 10 at 0.13 floods 90 FPs; SDG 14 at 0.90 predicts nothing (0 TP).
3. **Fresh per-SDG gates still beat the global optimum.** Macro-F1 at the fresh
   per-SDG gates ≈ **0.54** vs 0.464 at the global optimum, and per-SDG F1@fresh
   beats F1@0.7 on 14/17 goals (SDG 3 reaches 0.860). The per-SDG approach is
   still worthwhile — but only after re-deriving the gates at alpha 0.7.

---

## 7. Calibration & reliability

| | Alpha 0.3 | Alpha 0.7 |
|---|---|---|
| ECE | 0.131 | 0.140 |
| 0.70–0.80 bin (pred 0.75) empirical TPR | 0.187 | **0.414** |
| 0.80–0.90 bin empirical TPR | 0.361 | **0.610** |
| 0.90–1.00 bin empirical TPR | 0.729 | **0.779** |
| mean score true-pos / neg | 0.568 / 0.226 | 0.555 / 0.235 |
| n in 0.10–0.30 bins | 299 | **1001** |

- The **high end is meaningfully better calibrated** — a 0.80–0.90 score now has a
  61% (was 36%) true-positive rate, so high-confidence predictions are more
  trustworthy.
- Overall ECE rose only because the score mass shifted to the 0.10–0.30 band
  (n≈1001), where empirical rates are low (2–9%) — i.e. the zero-shot-dominant
  scores are more *conservative*, not more miscalibrated in the dangerous range.
- Separation between positives (0.555) and negatives (0.235) is unchanged;
  scores remain **rankings, not probabilities** — keep surfacing top-k and
  de-emphasizing absolute confidence.

---

## 8. Recommendations (updated for the alpha-0.7 pipeline)

1. **Lower the production threshold from 0.7 to ~0.55** (`embedding_url.py`
   `main()`). Expected micro-F1 gain ≈ **+0.068** (0.452 → 0.520) while restoring
   predictions to 2.04/project. This is a one-line change and the single biggest
   remaining lever.
2. **Re-derive `PER_SDG_THRESHOLDS` at alpha 0.7** and update
   `sdg_constants` + the unit tests that pin the §3 values
   (`test_values_match_eval_report_section_3`). The shipped gates (alpha-0.3 era)
   now *hurt* (−0.018 vs global 0.7). Consider whether the smaller spread even
   justifies the added complexity — a global 0.55 captures most of the gain.
3. **Do not touch alpha.** 0.7 is the joint optimum (0.520); 0.8/0.9 are close
   but not better. Pure zero-shot (1.0) loses ~0.016.
4. **Investigate SDG 6** (now 0 TP at 0.7, worst fresh F1 0.273) and SDG 9 (AUC
   improved to 0.567 but still weakest, and its per-SDG gate at 0.17/0.30 still
   floods FPs when lowered). These two are the only remaining hard problems.
5. **Fix the stale eval label.** The printed sweep header still says "ensemble
   alpha=0.3" (hardcoded string in `eval_dpga_150.py`) though `DEV_ALPHA` is now
   0.7 — cosmetic, but confusing in reports.
6. **Keep treating scores as rankings** (calibration still imperfect); re-run
   calibration after the threshold change.

---

## 9. Caveats

- Same 118-project labeled set as the old report; no new failures were added, so
  the comparison is clean. Aux OpenSustain results were not part of this diff.
- Per-SDG optimums on small `n+` goals (SDG 6: 8, SDG 7: 3, SDG 14: 2, SDG 15: 5)
  are noisy and should not be over-read.
- The per-SDG "best F1" figures are optimistic upper bounds (fit on the same set
  they're evaluated on) — use them for *relative* comparison, not as the expected
  held-out performance.
