# Testing Guide

This document inventories the testing this project needs: what exists today, what's missing, and the specific test cases each module should have. It's meant to guide contributors picking up `test/` issues, not to describe an aspirational end state — the backend now has a real `pytest` suite covering two modules (see table below), but most of the checklist is still unimplemented, and the frontend has no test runner at all.

## Current **state**

| Area | Test runner | Status |
|------|-------------|--------|
| Backend (`backend/`) | `pytest` (installed, in `requirements.txt`) | Two modules have real automated coverage: [`test_repo_fetcher.py`](../backend/tests/test_repo_fetcher.py) (72 tests) and [`test_embedding_url.py`](../backend/tests/test_embedding_url.py) (24 tests) — **all 96 passing**. `test_dpga_real_positives.py` and `test_gitlab_provider.py` remain manual, live-network scripts (excluded from collection via `conftest.py`'s `collect_ignore`) — useful as smoke tests, not part of the automated suite. `aurora_api.py`, `summariser.py`, `sdg_constants.py`, and `app.py` (§3–§6 below) still have no tests at all. |
| SDG inference (`backend/services/inference.py`, `sdg_model.py`) | covered indirectly | No direct tests — loading real weights makes naive unit testing hard (see [§7](#7-sdg-inference)). `zero_shot_scores` is tested on both branches (in-process and `MODEL_SERVICE_URL` over HTTP), and the load path is pinned by a mocked import trace. |
| Frontend (`frontend/`) | none | No Jest/Vitest/React Testing Library installed. `npm run lint` is the only check that runs today. |

Run the backend suite with `cd backend && pytest tests/` (the two manual scripts are auto-excluded). Setting up a frontend runner (`Jest` + `React Testing Library`) is still a prerequisite for most of the work in §7–§8 and is good first-issue material.



---

## 1. `backend/services/repo_fetcher.py` (Passed)

Highest priority — this module is pure logic with a deliberate exception hierarchy, and needs no ML model or live network access if `requests` is mocked.

- **`_sanitise_url`**: bytes input (valid UTF-8 and invalid), non-string types (`None`, `int`, `list`, `dict`), empty/whitespace-only string, missing scheme, non-http(s) scheme (`ftp://`, `git://`, `ssh://`), missing hostname.
- **`_rewrite_github_pages`**: root `*.github.io` (no path), `*.github.io/repo`, `*.github.io/repo/deep/path`, non-Pages URLs pass through unchanged.
- **Provider `_parse` methods**: valid `owner/repo`, missing segments, `.git` suffix stripping, invalid characters (GitHub's segment regex), nested subgroups (GitLab), `/wiki/` path detection (Bitbucket).
- **`_raise_for_status`**: 200 (no raise), 404 → `RepositoryNotFoundError`, 429 → `RateLimitError`, 403 with "rate limit" in body → `RateLimitError`, 401 → `FetchError`, other 403 → `FetchError`, other status codes → `FetchError`.
- **`fetch_readme` / `fetch_topics` / `fetch_meta`** per provider (GitHub, GitLab, Codeberg, Bitbucket), with mocked HTTP responses — including the "repo has no README" case, which must return `""`, not raise.
- **`_detect_engine`**: GitLab probe succeeds, Gitea/Forgejo probe succeeds, both fail → `None`, network exceptions during probing are swallowed rather than propagated.
- **`get_provider` factory**: known domain resolves without a network call, unknown domain triggers engine detection, unsupported host raises `UnsupportedHostError` with the expected message, token is passed through to the provider.

## 2. `backend/embedding_url.py` (Passed)

**Covered by [`backend/tests/test_embedding_url.py`](../backend/tests/test_embedding_url.py) (24 tests, all passing).** The checklist below is what that file implements; kept here for reference since it doubles as the coverage map.

- **`fetch_repo_text`**: user-supplied `project_description` takes priority over the repo's own metadata description (the documented "CHANGE 2" behavior); provider errors on `fetch_meta`/`fetch_topics`/`fetch_readme` are caught individually and don't abort the whole call.
- **`zero_shot_scores`**: score ordering matches `SDG_NAMES`; raises `KeyError` when the microservice response is missing expected keys; raises `TypeError` on an unexpected `scores` type; handles the `payload["data"]["scores"]` nested-response shape.
- **`embedding_similarity_scores`**: output is clipped to `[0, 1]` via `COSINE_LOW`/`COSINE_HIGH`.
- **`ensemble_scores`**: weighted-average arithmetic is correct for various `alpha` values.
- **`classify_repo`**: empty extracted text raises `ValueError`; predictions above `threshold` are selected; `predictions` is `[]` when nothing clears the threshold (see [known gap above](#known-gap-this-inventory-surfaced-resolved-no-threshold-match-behavior)) — no best-effort fallback.
- **`main`**: scores are formatted to 3 decimal places in the output dict.

All of the above need `requests`, `get_provider`, `summarize_for_sdg`, and `SentenceTransformer` mocked — none of these are integration tests against a live model or network.

## 3. `backend/aurora_api.py`

Table-driven tests against fixture Aurora API payloads:

- `sdg` as a dict with a `code` field → formatted as `"SDG {code}: {name}"`.
- `sdg` present but missing `code` → falls back to `name`/`label`.
- `sdg` field missing entirely → falls back to `pred.get("label")`/`pred.get("name")`/`pred.get("sdg_label")`.
- Score at or below the `0.1` cutoff is excluded from `sdg_predictions`.
- `requests.exceptions.RequestException` → returns the documented error dict, doesn't raise.
- A generic `Exception` during processing → returns the documented error dict, doesn't raise.

## 4. `backend/services/summariser.py`

- **`_prepare_for_llm`**: code fences removed, badge/shield images stripped, generic markdown images collapsed to alt text, HTML comments and tags stripped, bare URLs stripped, `max_chars` truncation applied.
- **`_validate_output`**: banned openers ("here is", "this project", "the repository", …) are stripped from the first line; output over 200 words is truncated at a sentence boundary.
- **`_fallback_summary`**: assembles from whatever combination of name/description/topics/reason is present; returns `""` when all inputs are empty.
- **`summarize_for_sdg`**:
  - No `GROQ_API_KEY` → falls back immediately, no network call.
  - Groq returns HTTP 200 with an `"error"` key in the body → falls back (this path is easy to miss since `raise_for_status()` alone won't catch it — worth its own explicit test).
  - Empty `choices` list → falls back.
  - `requests.exceptions.Timeout` / `HTTPError` / `RequestException` → falls back in each case.
  - Malformed `choices[0]["message"]` shape → falls back via the `KeyError`/`IndexError` branch.

Mock `requests.post`; no real Groq API calls in the unit suite.

## 5. `backend/sdg_constants.py`

Data-integrity checks rather than behavior:

- `len(SDG_NAMES) == len(SDG_DESCS) == len(SDG_LABELS) == 17`.
- Each entry in `SDG_NAMES` and `SDG_DESCS` starts with the correct `SDG {n}` number, in order.
- `SDG_LABELS_DICT` has exactly the keys `"1"` through `"17"`.

Cheap to write, and catches silent data-entry drift if someone edits the SDG text by hand. (Note: the trailing `SDGs = ["SDG 1", "SDG 2", "SDG 3"]` at the bottom of the file looks like dead code left over from development — worth confirming with a maintainer and removing rather than testing.)

## 6. `backend/app.py` (Flask routes)

Integration-style tests using Flask's test client (no live server needed):

- `POST /api/classify_aurora`: missing `projectDescription` → `400`; happy path filters predictions to `> 0.4`; an exception from `aurora_classify` → `500` with the documented error shape.
- `POST /api/classify_st_url`: missing `projectDescription` → `400`; missing `projectUrl` → `200` with empty `predictions` and an explanatory `message`; each of `InvalidURLError`/`UnsupportedHostError`/`ValueError` → `400`, `RepositoryNotFoundError` → `404`, `RateLimitError` → `429`, `FetchError`/`requests.exceptions.HTTPError` → `502`, anything else → `500`. This status-code mapping is exactly the kind of thing that silently breaks during a refactor if it isn't pinned down by a test.
- No `/api/classify_st_description` route exists, and no frontend code calls it anymore (see [gap above](#known-gap-this-inventory-surfaced-resolved)) — nothing to test here unless the route is intentionally reintroduced later.
- CORS headers are present on responses.

## 7. SDG inference

The hardest area to unit test conventionally: `services/inference.py` loads real weights from the Hugging Face Hub and builds tensors. Loading is now lazy and behind `load()`/`is_loaded()`, and score formatting lives in `predict_scores()` — both are seams a future test can use without a full weight load.

Recommended approach:
- **Refactor first**: extract the score→JSON formatting (rounding, threshold filtering in `/predict`, min-max normalization in `/similarities`) into small pure functions so they're unit-testable without a loaded model.
- **Smoke/integration test** for the model itself: start the service, `POST` a fixed known text, assert the response shape and that every score is in `[0, 1]`. Mark this slow/optional in CI — it needs to download model weights and doesn't need to run on every commit.

## 8. Frontend

Requires installing Jest or Vitest + React Testing Library first.

**Pure logic (no rendering required):**
- `lib/utils.ts` — `cn()` class merging/deduplication.
- `components/editModal.tsx` — `parseSdgFromString` (extracting number/name from strings like `"SDG 3: Health"`), `getSdgNumber`/`getSdgName` (string vs. object `sdg` shape), duplicate-SDG rejection in `addNewSDG`.
- `components/results.tsx` — `isNoSdgs` (null, empty array, empty object, all-zero-score object, mixed number/`SDGValue` shapes), `getScore` (number vs. `SDGValue` vs. undefined).
- `components/mainScreen.tsx` — the inline repo-URL validation regex (`/^\/[^/]+\/[^/]+/`): valid GitHub/GitLab path, bare domain with no path, malformed URL string.
- `services/api.ts` — `classifyByModel` switch: each model type routes to the correct client method; an unknown type falls back to Aurora.

**Component tests:**
- `mainScreen.tsx` — every form-validation message branch ("Please fill in...", "valid repository URL").
- `results.tsx` — tab switching (`handleTabChange`) and its error path, `handleDownload`'s JSON/blob generation.
- `editModal.tsx` — add/remove SDG flow end to end.

## 9. Cross-cutting / necessary but not "unit tests"

- **Contract tests** between `frontend/services/api.ts` and the backend routes — would have caught the missing `classify_st_description` endpoint automatically instead of at runtime.
- **SSRF consideration**: `fetch_repo_text`/`get_provider` take a user-supplied URL and the *server* makes outbound requests to it. `_sanitise_url` currently only validates URL *shape*, not destination — it will happily route to `http://localhost/...` or an internal `169.254.169.254`/RFC1918 address if a domain-map or engine-detection match were ever added for one. Worth a test (and likely a fix) confirming internal/private hosts are rejected before any request is issued.
- **Rate-limit and timeout behavior** against real forges (GitHub/GitLab/Codeberg/Bitbucket) isn't practical to unit test — track this as a documented manual/staging check instead.
- **End-to-end smoke test**: submit a real, known-good repository URL through the full stack and confirm a plausible SDG comes back. This is what [`backend/tests/test_dpga_real_positives.py`](../backend/tests/test_dpga_real_positives.py) already does by hand. It belongs in a manual/nightly tier, not the automated unit suite, since it depends on three live external services (the forge API, the GE-Lab microservice, and the embedding model).

## Suggested priority order for contributors

1. ~~Install `pytest` for `backend/`~~ — done (`test_repo_fetcher.py`, `test_embedding_url.py`). Fix the failing `classify_repo` fallback test/behavior mismatch (see known gap above) before adding more `embedding_url.py` coverage on top of it. Install Jest/Vitest + RTL for `frontend/`.
2. ~~`backend/services/repo_fetcher.py`~~ — done, 72 tests.
3. `backend/services/summariser.py` and `backend/aurora_api.py` — both are mockable HTTP-boundary modules with well-defined fallback paths, still untested.
4. `backend/app.py` route tests (the `classify_st_description` gap is already resolved, so this is unblocked).
5. Frontend pure-logic tests, then component tests.
6. SDG inference — via `predict_scores()` with `load()` stubbed, now that formatting is separated from loading.
