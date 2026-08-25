"""
Unit tests for the per-SDG threshold feature.

Covers:
  - sdg_constants.sdg_number_from_name / PER_SDG_THRESHOLDS values from
    docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md §6 (alpha-0.7 derivation).
  - embedding_url.passes_threshold (per-SDG wins, global fallback).
  - classify_repo with and without per_sdg_thresholds.
  - main() wiring per_sdg_thresholds into classify_repo.
  - app.py's ST-URL filter using per-SDG thresholds.
  - the first 100 labelled projects of backend/data/dpgs.xlsx, exercising
    the gates against a real-world label distribution.

No real network access, no real model/embedder — everything heavy is mocked.
The project metadata and ground-truth SDG vectors in the last section are real
(the dpgs.xlsx dataset), but fetching/scoring stay mocked and deterministic.
"""

from unittest.mock import MagicMock

import hashlib
import random
from pathlib import Path

import numpy as np
import pytest

import sdg_constants
import embedding_url
from embedding_url import ProviderError


def _make_zs_details(scores):
    return {
        "labels": sdg_constants.SDG_NAMES,
        "scores": list(scores),
        "sequence": "irrelevant",
    }


def _zs_with(by_index):
    """A 17-length zero-shot vector with the given {index: score} pairs set."""
    zs = np.zeros(17)
    for idx, sc in by_index.items():
        zs[idx] = sc
    return zs


# ─────────────────────────── sdg_number_from_name ─────────────────────────────

class TestSdgNumberFromName:
    def test_extracts_number_from_sdg_names_format(self):
        assert sdg_constants.sdg_number_from_name(
            "SDG 3: Ensure healthy lives and promote well-being for all at all ages"
        ) == "3"

    def test_extracts_double_digit_number(self):
        assert sdg_constants.sdg_number_from_name(
            "SDG 10: Reduce inequality within and among countries"
        ) == "10"

    def test_extracts_goal_style_label(self):
        assert sdg_constants.sdg_number_from_name("Goal 1 calls for an end to poverty") == "1"

    def test_none_for_non_sdg_label(self):
        assert sdg_constants.sdg_number_from_name("Some random label") is None
        assert sdg_constants.sdg_number_from_name("") is None


# ─────────────────────── PER_SDG_THRESHOLDS documented map ───────────────────

class TestPerSdgThresholdsMap:
    def test_covers_all_17_sdgs(self):
        assert len(sdg_constants.PER_SDG_THRESHOLDS) == 17

    def test_values_match_eval_report_section_3(self):
        # From docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md §6 (1% grid, alpha=0.7).
        expected = {
            "1": 0.58, "2": 0.54, "3": 0.50, "4": 0.46, "5": 0.53, "6": 0.38,
            "7": 0.45, "8": 0.30, "9": 0.17, "10": 0.50, "11": 0.43, "12": 0.70,
            "13": 0.32, "14": 0.76, "15": 0.61, "16": 0.55, "17": 0.46,
        }
        assert sdg_constants.PER_SDG_THRESHOLDS == expected

    def test_spread_confirms_no_single_global_threshold(self):
        thresholds = sdg_constants.PER_SDG_THRESHOLDS.values()
        assert min(thresholds) == pytest.approx(0.17)   # SDG 9
        assert max(thresholds) == pytest.approx(0.76)   # SDG 14


# ─────────────────────────── passes_threshold ─────────────────────────────────

class TestPassesThreshold:
    def test_per_sdg_threshold_wins_over_global_high(self):
        # SDG 9's optimum is 0.17: a 0.2 score must pass despite global 0.7.
        assert embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[8], 0.20, threshold=0.7,
            per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
        )

    def test_per_sdg_threshold_wins_over_global_low(self):
        # SDG 1's optimum is 0.58: a 0.5 score must fail despite global 0.4.
        assert not embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[0], 0.50, threshold=0.4,
            per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
        )

    def test_boundary_inclusive(self):
        # SDG 16 optimum is exactly 0.55 — a score of 0.55 passes.
        assert embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[15], 0.55, threshold=0.7,
            per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
        )

    def test_unknown_sdg_falls_back_to_global(self):
        assert embedding_url.passes_threshold("No SDG number here", 0.5, threshold=0.5)
        assert not embedding_url.passes_threshold("No SDG number here", 0.4, threshold=0.5)

    def test_sdg_missing_from_partial_map_falls_back_to_global(self):
        partial = {"9": 0.04}
        # SDG 1 not in the partial map -> global 0.5 applies.
        assert embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[0], 0.5, threshold=0.5, per_sdg_thresholds=partial,
        )
        assert not embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[0], 0.49, threshold=0.5, per_sdg_thresholds=partial,
        )

    def test_no_map_behaves_like_plain_threshold(self):
        assert embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[8], 0.1, threshold=0.7,
        ) is False
        assert embedding_url.passes_threshold(
            sdg_constants.SDG_NAMES[8], 0.9, threshold=0.7,
        ) is True


# ─────────────────────────── classify_repo per-SDG ────────────────────────────

class TestClassifyRepoPerSdg:
    def _patch_fetch(self, monkeypatch, text="some extracted text"):
        monkeypatch.setattr(
            embedding_url, "fetch_repo_text",
            lambda url, project_description="": {
                "owner": "owner",
                "repo": "repo",
                "text": text,
                "meta": {"name": "n", "description": "d", "topics": [], "homepage": ""},
            },
        )

    def _patch_scores(self, monkeypatch, zs):
        monkeypatch.setattr(
            embedding_url, "zero_shot_scores",
            lambda text, labels: (zs, _make_zs_details(zs)),
        )
        # Embedding scores equal to the zero-shot scores, so the ensemble
        # (any alpha, code uses 0.7) reproduces the zero-shot values exactly.
        monkeypatch.setattr(
            embedding_url, "embedding_similarity_scores",
            lambda text, label_texts: zs,
        )

    def test_per_sdg_thresholds_applied_in_classify_repo(self, monkeypatch):
        self._patch_fetch(monkeypatch)
        # SDG 9 (idx 8) score 0.20 -> passes its 0.17 gate.
        # SDG 1 (idx 0) score 0.50 -> fails its 0.58 gate.
        # SDG 16 (idx 15) score 0.55 -> passes its 0.55 gate (boundary).
        zs = _zs_with({8: 0.20, 0: 0.50, 15: 0.55})
        self._patch_scores(monkeypatch, zs)

        result = embedding_url.classify_repo(
            "https://github.com/o/r",
            threshold=0.7,
            per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
        )

        names = [n for n, _ in result["predictions"]]
        assert sdg_constants.SDG_NAMES[8] in names   # SDG 9 kept despite 0.20
        assert sdg_constants.SDG_NAMES[15] in names  # SDG 16 boundary kept
        assert sdg_constants.SDG_NAMES[0] not in names  # SDG 1 dropped despite 0.50

    def test_no_per_sdg_map_uses_global_threshold(self, monkeypatch):
        self._patch_fetch(monkeypatch)
        zs = _zs_with({0: 0.5, 8: 0.1})
        self._patch_scores(monkeypatch, zs)

        result = embedding_url.classify_repo(
            "https://github.com/o/r", threshold=0.7,
        )

        names = [n for n, _ in result["predictions"]]
        assert names == []

    def test_unknown_labels_fall_back_to_global(self, monkeypatch):
        self._patch_fetch(monkeypatch)
        zs = _zs_with({0: 0.5})
        self._patch_scores(monkeypatch, zs)

        # A partial map that doesn't mention SDG 1 -> global 0.4 applies.
        result = embedding_url.classify_repo(
            "https://github.com/o/r", threshold=0.4, per_sdg_thresholds={"9": 0.04},
        )

        names = [n for n, _ in result["predictions"]]
        assert sdg_constants.SDG_NAMES[0] in names


# ─────────────────────────── main() wiring ────────────────────────────────────

class TestMainWiresPerSdgThresholds:
    def test_main_passes_per_sdg_thresholds_to_classify_repo(self, monkeypatch):
        captured = {}

        def fake_classify_repo(url, threshold, use_ensemble, proj_desc, per_sdg_thresholds):
            captured.update({
                "threshold": threshold,
                "use_ensemble": use_ensemble,
                "proj_desc": proj_desc,
                "per_sdg_thresholds": per_sdg_thresholds,
            })
            return {
                "repo": "owner/repo",
                "predictions": [
                    ("SDG 9: Build resilient infrastructure, promote inclusive "
                     "and sustainable industrialization and foster innovation", 0.123456),
                ],
            }

        monkeypatch.setattr(embedding_url, "classify_repo", fake_classify_repo)

        result = embedding_url.main("https://github.com/o/r", project_description="pd")

        assert captured["per_sdg_thresholds"] is sdg_constants.PER_SDG_THRESHOLDS
        assert result["project_name"] == "owner/repo"


# ─────────────────────────── app.py ST-URL filter ─────────────────────────────

class TestAppStPredFilter:
    def test_low_scored_broad_sdg_kept(self):
        # SDG 9 (broad, optimum 0.17) with a 0.20 score is kept by the ST-URL filter.
        from app import _st_pred_passes
        assert _st_pred_passes({
            "sdg": "SDG 9: Build resilient infrastructure, promote inclusive "
                   "and sustainable industrialization and foster innovation",
            "prediction": 0.20,
        })

    def test_high_threshold_sdg_dropped(self):
        # SDG 1 (narrow, optimum 0.58) with 0.50 is dropped.
        from app import _st_pred_passes
        assert not _st_pred_passes({
            "sdg": "SDG 1: End poverty in all its forms everywhere",
            "prediction": 0.50,
        })

    def test_unparseable_sdg_falls_back_to_global_04(self):
        from app import _st_pred_passes
        assert _st_pred_passes({"sdg": "weird label", "prediction": 0.5})
        assert not _st_pred_passes({"sdg": "weird label", "prediction": 0.4})


# ─────────────── real DPG projects from data/dpgs.xlsx ───────────────────────

# Data-driven tests. The fetching and scoring layers stay mocked (no network, no
# real model — this is a unit suite), but the project metadata and ground-truth
# SDG vectors come from the first 100 labelled DPGs in
# backend/data/dpgs.xlsx (141 DPGs total), so the per-SDG gates are exercised
# against a real-world label distribution instead of three hand-picked cases.
# Scores are synthetic but deterministic per URL, keeping the suite offline and
# stable.

_DPGA_XLSX = Path(__file__).resolve().parents[1] / "data" / "dpgs.xlsx"
_DPGA_SAMPLE_SIZE = 100
_N_SDGS = 17
_DPGA_AVAILABLE = _DPGA_XLSX.exists()


def _load_dpga_projects(n=_DPGA_SAMPLE_SIZE):
    """Load up to n labelled projects from data/dpgs.xlsx (name, url, desc, gt)."""
    if not _DPGA_XLSX.exists():
        pytest.skip("backend/data/dpgs.xlsx not found")
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl is required to read backend/data/dpgs.xlsx")
    wb = openpyxl.load_workbook(_DPGA_XLSX, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    projects = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r or not r[0]:
            continue
        url = str(r[1] or "").strip()
        if not url:
            continue
        gt = [int(r[3 + i] or 0) for i in range(_N_SDGS)]
        projects.append({
            "name": str(r[0]).strip(),
            "url": url,
            "desc": str(r[2] or "").strip(),
            "gt": gt,
        })
    return projects[:n]


def _synthetic_scores(proj):
    """Deterministic per-project 17-vector for offline, reproducible tests.

    Ground-truth SDGs score in [0.50, 0.90), non-ground-truth in [0.02, 0.32),
    seeded from the repo URL so every run sees the same scores.
    """
    seed = int.from_bytes(hashlib.sha256(proj["url"].encode()).digest()[:8], "little")
    rng = random.Random(seed)
    scores = []
    for i in range(_N_SDGS):
        u = rng.random()
        if proj["gt"][i]:
            scores.append(round(0.50 + 0.40 * u, 4))
        else:
            scores.append(round(0.02 + 0.30 * u, 4))
    return np.array(scores, dtype=float)


def _manual_predictions(scores, threshold, per_sdg_thresholds, top_k=17):
    """Replicate classify_repo's selection so the two can be compared."""
    ranked = sorted(
        ((sdg_constants.SDG_NAMES[i], float(scores[i])) for i in range(_N_SDGS)),
        key=lambda kv: kv[1],
        reverse=True,
    )
    selected = [
        (name, sc) for (name, sc) in ranked
        if embedding_url.passes_threshold(name, sc, threshold, per_sdg_thresholds)
    ]
    return selected[:top_k]


@pytest.mark.skipif(not _DPGA_AVAILABLE, reason="backend/data/dpgs.xlsx missing")
class TestRealDpgaProjects:
    """Per-SDG thresholds over the first 100 real labelled DPG projects."""

    def _projects(self):
        return _load_dpga_projects()

    def test_loads_exactly_100_real_projects(self):
        projects = self._projects()
        assert len(projects) == 100
        for p in projects:
            assert p["name"]
            assert p["url"].startswith("http")
            assert len(p["gt"]) == 17
            assert set(p["gt"]) <= {0, 1}
            assert sum(p["gt"]) >= 1

    def test_ground_truth_positive_counts(self):
        projects = self._projects()
        gt = np.array([p["gt"] for p in projects], dtype=int)
        positives = gt.sum(axis=0)
        assert (positives > 0).all(), (
            f"every SDG must have >=1 positive in the sample: {positives}"
        )
        assert int(gt.sum()) >= 2 * len(projects)

    def test_classify_repo_matches_manual_gating_over_100_projects(self, monkeypatch):
        projects = self._projects()
        for proj in projects:
            scores = _synthetic_scores(proj)
            text = proj["desc"] or proj["name"]

            monkeypatch.setattr(
                embedding_url, "fetch_repo_text",
                lambda url, project_description="", proj=proj, text=text: {
                    "owner": "owner",
                    "repo": "repo",
                    "text": text,
                    "meta": {
                        "name": proj["name"],
                        "description": proj["desc"],
                        "topics": [],
                        "homepage": "",
                    },
                },
            )
            monkeypatch.setattr(
                embedding_url, "zero_shot_scores",
                lambda text, labels, scores=scores: (
                    scores,
                    {"labels": labels, "scores": list(scores), "sequence": text[:500]},
                ),
            )
            monkeypatch.setattr(
                embedding_url, "embedding_similarity_scores",
                lambda text, label_texts, scores=scores: scores,
            )

            expected = _manual_predictions(
                scores, threshold=0.7,
                per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
            )
            result = embedding_url.classify_repo(
                proj["url"], threshold=0.7, top_k=17,
                per_sdg_thresholds=sdg_constants.PER_SDG_THRESHOLDS,
            )
            assert [n for n, _ in result["predictions"]] == [n for n, _ in expected], proj["url"]
            assert len(result["predictions"]) == len(expected)
            for (n1, s1), (n2, s2) in zip(result["predictions"], expected):
                assert n1 == n2, proj["url"]
                # classify_repo applies the ensemble (0.7*zs + 0.3*es) which
                # reproduces zs up to float rounding, so compare with tolerance.
                assert s1 == pytest.approx(s2), proj["url"]

    def test_per_sdg_gates_change_selection_versus_global_threshold(self):
        # The alpha-0.7 gates cluster tightly, so compare against the global
        # F1-optimal threshold 0.55 (docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md
        # §3), not the old 0.7: fresh gates still both loosen (recover broad SDGs
        # like SDG 9) and tighten (suppress narrow SDGs like SDG 1/12/14).
        projects = self._projects()
        loosened = 0  # kept by per-SDG, dropped by global 0.55
        tightened = 0  # kept by global 0.55, dropped by per-SDG
        for proj in projects:
            scores = _synthetic_scores(proj)
            per_sdg = {
                sdg_constants.SDG_NAMES[i]
                for i in range(_N_SDGS)
                if embedding_url.passes_threshold(
                    sdg_constants.SDG_NAMES[i], scores[i], 0.55,
                    sdg_constants.PER_SDG_THRESHOLDS,
                )
            }
            global_055 = {
                sdg_constants.SDG_NAMES[i]
                for i in range(_N_SDGS)
                if scores[i] >= 0.55
            }
            loosened += len(per_sdg - global_055)
            tightened += len(global_055 - per_sdg)
        assert loosened > 0, (
            "per-SDG gates must recover low-scored broad SDGs (e.g. SDG 9)"
        )
        assert tightened > 0, (
            "per-SDG gates must suppress mid-scored narrow SDGs (e.g. SDG 1/14)"
        )

    def test_low_gate_sdgs_account_for_most_per_sdg_keeps(self):
        # docs/EVAL_DPGA_150_RESULTS_alpha07_ANALYSIS.md §6: the broad SDGs
        # 3/8/9/10/17 still need the lowest gates (0.17-0.50). On the real
        # sample the per-SDG operating point keeps far more of them than the
        # recommended global 0.55 gate.
        low_gate_idx = [2, 7, 8, 9, 16]  # SDG 3, 8, 9, 10, 17
        per_sdg_kept = 0
        global_kept = 0
        for proj in self._projects():
            scores = _synthetic_scores(proj)
            for i in low_gate_idx:
                if embedding_url.passes_threshold(
                    sdg_constants.SDG_NAMES[i], scores[i], 0.55,
                    sdg_constants.PER_SDG_THRESHOLDS,
                ):
                    per_sdg_kept += 1
                if scores[i] >= 0.55:
                    global_kept += 1
        assert per_sdg_kept > global_kept