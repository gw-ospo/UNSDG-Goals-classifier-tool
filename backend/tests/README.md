# test_per_sdg_thresholds.py — Run Analysis & Insights

Reference run: **25 tests, 25 passed, 0 failed** on
`win32 / Python 3.11.7 / pytest 9.1.1`, collected from
`backend/tests/test_per_sdg_thresholds.py`.

```
python -m pytest tests/test_per_sdg_thresholds.py -v
```

## What this suite covers

The suite is a fully offline, mocked unit test for the **per-SDG threshold**
feature — the idea (from `docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md` §6)
that each of the 17 SDGs gets its own F1-optimal prediction gate instead of one
global threshold. Every layer of the feature is exercised, from constants to the
running Flask route filter:

| Test class | # tests | Layer under test |
|---|---|---|
| `TestSdgNumberFromName` | 4 | `sdg_constants.sdg_number_from_name` (label → SDG number parsing) |
| `TestPerSdgThresholdsMap` | 3 | `sdg_constants.PER_SDG_THRESHOLDS` documented map |
| `TestPassesThreshold` | 6 | `embedding_url.passes_threshold` gating logic |
| `TestClassifyRepoPerSdg` | 3 | `embedding_url.classify_repo` applying the gates |
| `TestMainWiresPerSdgThresholds` | 1 | `main()` wiring the map into `classify_repo` |
| `TestAppStPredFilter` | 3 | `app.py` ST-URL prediction filter (`_st_pred_passes`) |
| `TestRealDpgaProjects` | 5 | data-driven checks over 100 real labelled DPG projects |

## Insights drawn from the run

### 1. The per-SDG map is complete and matches the eval report bit-for-bit
`PER_SDG_THRESHOLDS` covers all 17 SDGs, and every value equals the alpha-0.7
derivation table (`test_values_match_eval_report_section_3`). The documented
gates are the gates the code ships — nothing drifted between the eval run and
the constants.

### 2. No single global threshold is optimal for all 17 goals
The map's spread at alpha 0.7 is tighter than the old alpha-0.3 derivation, but
still meaningful:
- min gate = **0.17 (SDG 9)** — the broad "Industry, Innovation & Infrastructure"
  goal is consistently under-scored, so low scores must still fire.
- max gate = **0.76 (SDG 14)** — the narrow "Life Below Water" goal only fires at
  high confidence.

The 6 `TestPassesThreshold` tests pin this down explicitly: SDG 9's 0.20 score
passes *despite* a global 0.7, and SDG 1's 0.50 fails *despite* a global 0.4.

### 3. Boundary behaviour is inclusive and intentional
`test_boundary_inclusive` proves a score exactly equal to the gate (SDG 16 at
0.55 vs gate 0.55) is kept. This is a deliberate, documented `>=` comparison —
important for reproducibility of the eval sweep that derived these gates.

### 4. Fallback behaviour is preserved everywhere
Three distinct fallback paths are verified, all of which keep historical
behaviour intact:
- unknown / unparseable SDG label → global threshold (`test_unknown_sdg_falls_back_to_global`),
- SDG missing from a *partial* map → global threshold (`test_sdg_missing_from_partial_map_falls_back_to_global`),
- no map at all → plain threshold, no behaviour change (`test_no_map_behaves_like_plain_threshold`).

The same fallback is re-verified at the `classify_repo` level
(`test_unknown_labels_fall_back_to_global`) and at the `app.py` filter level
(`test_unparseable_sdg_falls_back_to_global_04`). So the feature is purely
additive: it only changes outcomes for SDGs that actually have a tuned gate.

### 5. The feature is wired end-to-end, not just in one function
`TestMainWiresPerSdgThresholds` confirms `main()` passes the real
`sdg_constants.PER_SDG_THRESHOLDS` map into `classify_repo`, and
`TestAppStPredFilter` confirms the live `/api/classify_st_url` filter uses the
same gates. The full chain *constants → gating → classifier → CLI entrypoint →
Flask route* is covered, so the feature can't silently deactivate at any layer.

### 6. Data-driven validation on 100 real labelled projects
The `TestRealDpgaProjects` class (new) runs the gating logic against the first
100 labelled DPGs from the repo-root `dpgs.csv.xlsx` (141 total), using real
project metadata and real ground-truth SDG vectors:
- Dataset sanity: exactly 100 projects load, every project has ≥1 ground-truth
  SDG, and **all 17 SDGs appear as positives** in the sample (positive counts
  range from 2 for SDGs 14/15 up to 42 for SDG 3; average ≈ 2.7 SDGs/project).
  So every single gate is exercised by real labels.
- Wiring at scale: for all 100 projects, `classify_repo`'s prediction set is
  identical to a hand-computed per-SDG gating of the same scores
  (`test_classify_repo_matches_manual_gating_over_100_projects`).
- Real directional behaviour: the per-SDG gates **both loosen and tighten**
  selection vs the global F1-optimal 0.55 gate
  (`test_per_sdg_gates_change_selection_versus_global_threshold`):
  - *loosened*: broad SDGs (9, 10, 17, 8, 3) recovered at low scores that a global 0.55 drops;
  - *tightened*: narrow SDGs (1, 12, 14) suppressed at mid scores that a global 0.55 keeps.
- Low-gate SDGs dominate the per-SDG keeps
  (`test_low_gate_sdgs_account_for_most_per_sdg_keeps`), matching the alpha-0.7
  eval finding that the broad, common goals still need the lowest gates.

### 7. The scores used in the 100-project tests are synthetic by design
`TestRealDpgaProjects` deliberately uses **deterministic synthetic scores**
(ground-truth SDGs → 0.50–0.90, non-ground-truth → 0.02–0.32, seeded per repo
URL), because this is a unit suite: no network, no model, no Groq, no
microservice. It therefore validates the **gating/wiring** of the per-SDG
feature at scale — *not* the model's predictive accuracy. Accuracy against the
same ground truth is the job of the live, excluded script
`backend/tests/eval_dpga_150.py` (`--boot-models --dpgs 141 --opensustain 150`),
which is listed in `conftest.py`'s `collect_ignore` and must be run directly.

### 8. Float precision is handled explicitly
`classify_repo` applies the ensemble `0.7*zs + 0.3*es`; with `es == zs` (as
mocked) that reproduces `zs` mathematically but not bit-for-bit in binary
floating point (e.g. `0.8840000000000001` vs `0.884`). The
`test_classify_repo_matches_manual_gating_over_100_projects` comparison therefore
asserts exact equality on the selected SDG **names/order** and uses
`pytest.approx` for the **scores**. This also keeps the test robust if the
ensemble formula or alpha is ever changed.

## Environment

- Platform: `win32`, Python 3.11.7, pytest 9.1.1, pluggy 1.6.0, anyio 4.13.0.
- Rootdir: repo `backend/` (so `sdg_constants`, `embedding_url`, and `app`
  import cleanly via `conftest.py`'s `sys.path` setup).
- Run time: effectively instant — every layer is mocked, no network/model I/O.

## Conventions worth keeping

- Keep `TestRealDpgaProjects` offline: it reads `dpgs.csv.xlsx` (a repo file)
  and never hits GitHub/Groq/the microservice. If the xlsx is missing, the class
  auto-skips (`pytest.mark.skipif`) rather than failing the whole suite.
- The `dpgs.csv.xlsx` loader mirrors `eval_dpga_150.py::load_dpgs` column layout
  (`name`, `url`, `description`, `act_sdg1..17` starting at column index 3).
- Any change to `PER_SDG_THRESHOLDS` must keep
  `test_values_match_eval_report_section_3` and `TestPerSdgThresholdsMap` green
  — they are the contract between the eval report and the code.
