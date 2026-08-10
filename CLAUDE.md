# UNSDG Classifier Tool

Web app (under the CHAOSS UN-SDG Working Group) that analyzes open source repos and classifies them against the 17 UN Sustainable Development Goals. See [README.md](README.md) for the project pitch and community links.

## Architecture — three separate services

- **`frontend/`** — Next.js 15 (App Router) + TypeScript + Tailwind + MUI. Entry: [app/page.tsx](frontend/app/page.tsx). API calls live in `frontend/services/api.ts`. Run: `cd frontend && npm run dev` (localhost:3000). Lint: `npm run lint`.
- **`backend/`** — Flask API in [backend/app.py](backend/app.py). Routes: `/api/classify_aurora` (Aurora SDG API), `/api/classify_st_url` (sentence-transformer + repo fetch). Run: `cd backend && python app.py`.
  - `backend/services/repo_fetcher.py` — fetches README/topics/meta from GitHub/GitLab/Codeberg/Bitbucket, with a deliberate exception hierarchy (`InvalidURLError`, `UnsupportedHostError`, `RepositoryNotFoundError`, `RateLimitError`, `FetchError`).
  - `backend/services/summariser.py` — Groq LLM summarization with graceful fallback when no API key / on any failure.
  - `backend/embedding_url.py` — zero-shot + embedding-similarity ensemble scoring against the `models/` microservice.
  - `backend/aurora_api.py` — client for the external Aurora SDG API.
- **`models/`** — separate FastAPI microservice (`fastapi`/`uvicorn`/`torch`/`transformers`) serving a LUKE-based multi-label SDG classifier (`models/classifier.py`, `models/config.json`). Loads real weights from Hugging Face Hub at import time.

The frontend never talks to `models/` directly — it goes through the Flask backend.

## Testing

Real state as of 2026-08 (see [docs/TESTING.md](docs/TESTING.md) for the fuller inventory):

- `backend/tests/` — pytest, installed via `requirements.txt`. Two real automated suites, all 96 tests passing: `test_repo_fetcher.py` (72 tests, mocked HTTP, no network) and `test_embedding_url.py` (24 tests). `test_dpga_real_positives.py` and `test_gitlab_provider.py` are manual/live-network scripts, excluded from collection via `conftest.py`'s `collect_ignore` — don't try to run them as part of the normal suite.
- `frontend/` — no test runner installed yet (`npm run lint` is the only check).
- `models/` — no tests; hard to unit test because weight-loading happens at import time. If asked to add tests here, extract pure formatting/scoring logic first rather than mocking the model load.
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
