# UNSDG Classifier Tool

Web app (under the CHAOSS UN-SDG Working Group) that analyzes open source repos and classifies them against the 17 UN Sustainable Development Goals. See [README.md](README.md) for the project pitch and community links.

## Architecture — two separate services

- **`frontend/`** — Next.js 15 (App Router) + TypeScript + Tailwind + MUI. Entry: [app/page.tsx](frontend/app/page.tsx). API calls live in `frontend/services/api.ts`. Run: `cd frontend && npm run dev` (localhost:3000). Lint: `npm run lint`.
- **`backend/`** — Flask API in [backend/app.py](backend/app.py). Routes: `/api/classify_aurora` (Aurora SDG API), `/api/classify_st_url` (sentence-transformer + repo fetch). Run: `cd backend && python app.py` (localhost:8010 — not Flask's default 5000, which macOS AirPlay occupies; `API_BASE_URL` in `frontend/services/api.ts` must match).
  - `backend/services/repo_fetcher.py` — fetches README/topics/meta from GitHub/GitLab/Codeberg/Bitbucket, with a deliberate exception hierarchy (`InvalidURLError`, `UnsupportedHostError`, `RepositoryNotFoundError`, `RateLimitError`, `FetchError`).
  - `backend/services/summariser.py` — Groq LLM summarization with graceful fallback when no API key / on any failure.
  - `backend/embedding_url.py` — zero-shot + embedding-similarity ensemble scoring. `zero_shot_scores` runs the classifier in-process by default; setting `MODEL_SERVICE_URL` routes it over HTTP to a remote model service instead (the seam kept for a future GPU/scale split).
  - `backend/services/inference.py` — lazy singleton holding the LUKE tokenizer + model, exposing `predict_scores(text)`. Rounds to 4 decimals, matching the retired `/predict` endpoint exactly.
  - `backend/services/sdg_model.py` — the `SDGClassifier` architecture. Builds its backbone with `AutoModel.from_config`, no pretrained download; the fine-tuned checkpoint supplies every parameter.
  - `backend/services/embedder.py` — the one shared `all-mpnet-base-v2` accessor for the process.
  - `backend/aurora_api.py` — client for the external Aurora SDG API.

The former `models/` Flask microservice was retired: its classifier now runs inside the backend process. `backend/services/sdg_model_config.json` is the model's committed config, currently unreferenced by code (the architecture resolves from the Hub id).

## Testing

Real state as of 2026-08 (see [docs/TESTING.md](docs/TESTING.md) for the fuller inventory):

- `backend/tests/` — pytest, installed via `requirements.txt`. Two real automated suites, all 99 tests passing: `test_repo_fetcher.py` (72 tests, mocked HTTP, no network) and `test_embedding_url.py` (24 tests). `test_dpga_real_positives.py` and `test_gitlab_provider.py` are manual/live-network scripts, excluded from collection via `conftest.py`'s `collect_ignore` — don't try to run them as part of the normal suite.
- `frontend/` — no test runner installed yet (`npm run lint` is the only check).
- SDG inference (`services/inference.py`, `services/sdg_model.py`) — no direct tests; loading real weights makes naive unit testing hard. The load path is covered indirectly by a mocked import trace; `zero_shot_scores` is tested on both the in-process and HTTP branches.
- No CI workflow exists in `.github/workflows` yet — nothing runs these automatically on PRs.

When adding backend logic, prefer pure/mockable functions (see `repo_fetcher.py`'s style) so pytest coverage stays cheap.

## Conventions ([CONTRIBUTING.md](CONTRIBUTING.md) has the full contributor-facing version)

- Branch names: `feat/`, `fix/`, `docs/`, `chore/`, `test/`, `refactor/` + short description.
- Commits: Conventional Commits — `type(scope): short description`, subject under 72 chars.
- PRs: one logical change each, reference the related issue, describe *why* not just *how*.
- Backend error mapping in `app.py` is intentional and tested for (`InvalidURLError`→400, `RepositoryNotFoundError`→404, `RateLimitError`→429, `FetchError`→502) — preserve it when touching routes.

## Known rough edges (don't "fix" silently — confirm with a maintainer first)

- `_sanitise_url` in `repo_fetcher.py` validates URL *shape* only, not destination — no SSRF guard against internal/private hosts yet.
- The trailing `SDGs = [...]` list at the bottom of `backend/sdg_constants.py` looks like leftover dead code.

See `CLAUDE.local.md` (untracked) for maintainer-specific working notes.
