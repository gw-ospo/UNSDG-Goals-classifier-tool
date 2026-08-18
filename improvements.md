# Improvements & Loopholes Registry
## UNSDG Classifier Tool

This document registers identified improvement opportunities, loopholes, and scope for enhancement
in the classification mechanism of the UNSDG Classifier Tool. It is intended to guide future
contributions and refactoring efforts.

---

## Classification Mechanism Loopholes & Gaps

### 1. SSRF Vulnerability in URL Sanitisation ✅ FIXED
- **Location**: `backend/services/repo_fetcher.py:54-143` (`_sanitise_url`)
- **Issue**: The function validated URL *shape* (scheme, hostname presence) but did **not**
  validate the *destination*. It would happily route to internal/private hosts such as
  `http://localhost/...`, `http://127.0.0.1/...`, or RFC1918 addresses (`10.x.x.x`,
  `172.16-31.x.x`, `192.168.x.x`).
- **Risk**: Server-side request forgery — a malicious user could force the server to make
  outbound requests to internal services, port scan internal networks, or exfiltrate metadata.
- **Fix**: Added host validation in `_sanitise_url` to reject:
  - `localhost`
  - RFC1918 private IP ranges: `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`
  - Loopback `127.x.x.x`
  The function now returns `InvalidURLError` for any of these hosts, preventing SSRF.
  Verified: all test cases pass (valid URLs pass, private/loopback IPs rejected).

### 2. Dead Code: Trailing `SDGs` List
- **Location**: `backend/sdg_constants.py:218-220`
- **Issue**: The list `SDGs = ["SDG 1", "SDG 2", "SDG 3"]` at the bottom of the file appears
  to be leftover dead code from development. It is not referenced anywhere else in the codebase.
- **Fix**: Remove the dead code or add a clear comment if it serves an intentional purpose.

### 3. Inconsistent SDG Label Formats
- **Location**: `backend/sdg_constants.py` multiple references
- **Issue**: Multiple SDG label representations exist with inconsistent formats:
  - `SDG_LABELS_DICT`: keys `"1"`-"`17"` mapping to full names (used by Aurora API)
  - `SDG_NAMES`: full `"SDG 1: End poverty..."` strings (used by embedding models)
  - `SDG_LABELS`: goal description strings (used by similarity scoring)
  - `SDG_DESCS`: descriptive strings in `models/similarities.py` and `backend/services/summariser.py`
- **Risk**: Confusion about which format to use where, potential mapping bugs when switching
  between models, and duplicated description text that diverges over time.
- **Fix**: Establish a single canonical SDG label format and convert/alias others to it.
  Consider removing redundant representations or adding clear conversion functions.

### 4. Hardcoded Classification Thresholds
- **Location**: 
  - `backend/app.py:67` (Aurora: `> 0.4`)
  - `backend/embedding_url.py:176` (`sc >= threshold` with default `0.5`)
  - `backend/embedding_url.py:188` (`main()` uses `threshold=0.4`)
- **Issue**: thresholds are hardcoded with no configuration mechanism. Different use cases
  may require different thresholds, and there's no way to tune them without code changes.
- **Fix**: Extract thresholds to a configuration file or environment variables. Support
  per-endpoint override via API parameters.

### 5. Aurora API `raise_for_status()` Not Called
- **Location**: `backend/aurora_api.py:22`
- **Issue**: The comment notes `response.raise_for_status()` is intentionally NOT called because
  the Aurora API can return HTTP 200 with an `"error"` key in the body. However, the code
  manually checks for this, which is correct but easy to miss during future maintenance.
- **Fix**: Add a clear docstring explaining why `raise_for_status()` is omitted, and add a
  unit test verifying the "HTTP 200 with error payload" fallback path.

### 6. No Best-Effort Fallback When No SDGs Above Threshold
- **Location**: `backend/embedding_url.py:176-177`
- **Issue**: `classify_repo` selects only predictions where `sc >= threshold`. If nothing matches,
  the result has an empty `predictions` list — the caller gets no indication whether the
  text was classified at all, or if the result is simply "none of the above".
- **Fix**: Add a fallback that returns the top-N ranked SDGs even if below threshold, or
  add a "no relevant SDG" signal to the response. Consider adding a secondary low-confidence
  band (e.g., 0.2) that surfaces the closest match with a "Low" confidence tag.

### 7. GE-Lab Microservice Dependency at localhost:9010
- **Location**: `backend/embedding_url.py:99` (`zero_shot_scores`)
- **Issue**: The zero-shot model calls `http://localhost:9010/predict` which requires the
  GE-Lab microservice to be running locally. If it's down, the entire classification fails.
- **Fix**: Add a fallback to the sentence-transformer ensemble-only mode when the microservice
  is unreachable. Consider making the microservice URL configurable.

### 8. Bitbucket Wiki Deprecation (2026-08-20)
- **Location**: `backend/services/repo_fetcher.py:647-676` (`fetch_wiki_home`)
- **Issue**: The code has a deprecation note that Bitbucket wikis will be removed on 2026-08-20,
  but the method still functions and is called silently in `fetch_readme`. After that date,
  it will start returning 404/empty for all repos.
- **Fix**: Add a runtime check near the deprecation date, or feature-flag the method behind a
  config. Consider removing wiki fallback entirely since wikis are being deprecated.

### 9. Limited Error Classification for Aurora API
- **Location**: `backend/aurora_api.py:91-107`
- **Issue**: The Aurora API client catches `RequestException` and generic `Exception`, but the
  error response format is vague ("Aurora API processing failed") without distinguishing between
  network errors, API downtime, or malformed input.
- **Fix**: Map specific error types to appropriate HTTP status codes (similar to how
  `app.py` maps repo_fetcher errors) and include more descriptive error codes in the response.

### 10. No Confidence Banding in Predictions
- **Location**: Multiple locations (`app.py:67`, `embedding_url.py:176`, `api.ts` frontend)
- **Issue**: Predictions are returned as `{"SDG name": score}` with no confidence classification.
  The UI has no way to distinguish "High/Medium/Low" confidence based on score ranges.
- **Fix**: Add confidence banding (e.g., High: 0.7-1.0, Medium: 0.4-0.69, Low: 0.1-0.3) and
  include the band in both API responses and frontend display.

### 11. GitHub Pages Rewriting Limited to github.com
- **Location**: `backend/services/repo_fetcher.py:702-737` (`_rewrite_github_pages`)
- **Issue**: The function only handles `github.com` and `www.github.io` domains. Other GitHub
  enterprise instances or custom Pages hosts are not supported.
- **Fix**: Make the GitHub Pages rewrite domain-aware or add a configuration for custom GitHub
  Enterprise hosts.

### 12. CORS and API Route Status Code Mapping Not Explicitly Tested
- **Location**: `backend/app.py:39-161`
- **Issue**: The status code mapping (`InvalidURLError`→400, `RepositoryNotFoundError`→404,
  `RateLimitError`→429, `FetchError`→502) is documented in TESTING.md but not explicitly
  tested. A silent route change could break frontend expectations.
- **Fix**: Add integration tests in `backend/tests/` that assert each error maps to the correct
  status code, preventing regressions during refactors.

---

## Scope of Improvement

### High-Priority Enhancements

1. **SSRF Protection**: Implement host validation in `_sanitise_url` to reject private/internal
   addresses. This is the most critical security fix.

2. **Unified SDG Label Format**: Establish one canonical SDG label representation across the
   codebase and add conversion functions between formats. Remove or document duplicates.

3. **Configurable Thresholds**: Extract classification thresholds to a config file or environment
   variables. Support API-level override.

4. **Best-Effort Fallback**: When no SDGs exceed the threshold, return the top-N ranked SDGs
   with a "Low" confidence indicator, rather than an empty predictions list.

5. **Aurora API Robustness**: Add better error categorization and HTTP status code mapping for
   the Aurora API client.

### Medium-Priority Enhancements

6. **Confidence Banding**: Add High/Medium/Low confidence bands based on score ranges and
   propagate them through the API and frontend.

7. **Ensemble Alpha Configuration**: Make the ensemble alpha (currently 0.3) configurable
   via environment variable or API parameter.

8. **Microservice Failover**: Add fallback to ensemble-only mode when GE-Lab microservice
   at localhost:9010 is unreachable.

9. **Bitbucket Wiki Deprecation Handling**: Add runtime check or config flag for the
   Bitbucket wiki deprecation date (2026-08-20).

10. **Explicit Error Status Code Tests**: Add integration tests verifying each error type
    maps to the correct HTTP status code in `app.py`.

### Lower-Priority Enhancements

11. **GitHub Enterprise Support**: Extend `_rewrite_github_pages` and domain map to support
    GitHub Enterprise Server instances.

12. **Rate-Limit-Aware Retries**: Add exponential backoff and retry logic for repository
    fetching when rate limits are hit.

13. **Private Repository Token Flow**: Improve token handling so authenticated access to
    private repos works seamlessly across all supported hosts.

14. **Prediction Reason Codes**: Add a `reason` field to predictions indicating why a
    particular SDG was selected (e.g., "keyword_match", "topic_match", "description_match").

15. **End-to-End Test Suite**: Build an automated end-to-end test that submits known
    repositories and validates plausible SDG output, suitable for nightly CI runs.

### Future / Research Directions

16. **Multi-Label Correlation Analysis**: Analyze SDG prediction correlations to identify
    which text signals most strongly correlate with specific goals, enabling better
    prompt engineering and text preprocessing.

17. **Language Diversity Improvement**: The summariser forces English output, but the
    underlying models may benefit from multilingual input. Research whether keeping
    non-English signals (translated) improves classification accuracy.

18. **Ensemble Weight Tuning**: Research optimal `alpha` values for the zero-shot + cosine
    similarity ensemble. Consider data-driven tuning based on validation set performance.

19. **Aurora API Integration**: Deeper integration with the Aurora SDG API, including
    bidirectional mapping between Aurora's SDG codes and the tool's internal SDG labels.

20. **Model Version Pinning**: Add version pinning / checksum validation for the GE-Lab
    microservice model and sentence-transformer models to ensure reproducible results.

---

## Summary

The classification mechanism is functional but has several areas where robustness,
security, and maintainability can be improved. The highest-impact changes are:
- SSRF protection (security critical)
- Unified SDG label format (developer ergonomics)
- Configurable thresholds (usability)
- Best-effort fallback when no goals match (user experience)

These improvements should be addressed in priority order, starting with the SSRF fix
and dead code removal, followed by configuration and fallback enhancements.