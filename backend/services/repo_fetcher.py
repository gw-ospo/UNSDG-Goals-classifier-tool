"""
services/repository_provider.py

Agnostic repository fetcher — Strategy pattern.
Supported hosts: GitHub, GitLab, Codeberg (Gitea-based).

Error hierarchy
---------------
ProviderError           base for all errors this module raises
  InvalidURLError       bad type, empty string, non-HTTP scheme, missing owner/repo
  UnsupportedHostError  domain not in the registry
  RepositoryNotFoundError  404 / repo is private without a token
  RateLimitError        429 / secondary rate limit from any host
  FetchError            any other network / HTTP failure (wraps original)
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse, quote

import requests


# ─────────────────────────── custom exceptions ───────────────────────────────

class ProviderError(Exception):
    """Base class for all repository-provider errors."""


class InvalidURLError(ProviderError):
    """Raised when the input cannot be interpreted as a valid repo URL."""


class UnsupportedHostError(ProviderError):
    """Raised when the domain is not in the supported-host registry."""


class RepositoryNotFoundError(ProviderError):
    """Raised on HTTP 404 — repo does not exist or is private."""


class RateLimitError(ProviderError):
    """Raised on HTTP 429 or GitHub secondary-rate-limit 403."""


class FetchError(ProviderError):
    """Raised on any other network or HTTP error. Wraps the original exception."""


# ────────────────────────── input sanitiser ──────────────────────────────────

def _sanitise_url(raw: object) -> str:
    """
    Coerce *raw* to a clean URL string.

    Accepts:
      - str  with optional leading/trailing whitespace
      - bytes (decoded as UTF-8)

    Rejects with InvalidURLError:
      - None, int, list, dict, or any other non-string type
      - empty / whitespace-only strings
      - strings that look like a bare label ("my project") not a URL
      - non-HTTP(S) schemes  (ftp://, git://, ssh://, …)
      - plain owner/repo shorthand  ("owner/repo") — ambiguous without a host
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidURLError("URL bytes could not be decoded as UTF-8.")

    if not isinstance(raw, str):
        raise InvalidURLError(
            f"Expected a URL string, got {type(raw).__name__!r}. "
            "Pass a full URL such as 'https://github.com/owner/repo'."
        )

    url = raw.strip()

    if not url:
        raise InvalidURLError("URL must not be empty.")

    parsed = urlparse(url)

    # No scheme → likely bare "owner/repo" or a plain label
    if not parsed.scheme:
        raise InvalidURLError(
            f"URL has no scheme: {url!r}. "
            "Use the full URL, e.g. 'https://github.com/owner/repo'."
        )

    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError(
            f"Unsupported scheme {parsed.scheme!r}. Only http / https are accepted."
        )

    if not parsed.hostname:
        raise InvalidURLError(f"URL has no host: {url!r}.")

    hostname = parsed.hostname.lower()
    # Reject private/internal IP addresses and localhost to prevent SSRF
    if hostname == "localhost":
        raise InvalidURLError(
            f"URL host localhost is not allowed. "
            "Use a public repository URL such as github.com/owner/repo."
        )
    # Check for RFC1918 private IP ranges
    parts = hostname.split(".")
    if len(parts) == 4:
        try:
            octets = [int(p) for p in parts]
            # 10.0.0.0/8
            if octets[0] == 10:
                raise InvalidURLError(
                    f"URL host {hostname} is not allowed. "
                    "Private IP addresses (10.x.x.x) are not supported."
                )
            # 172.16.0.0/12
            if octets[0] == 172 and 16 <= octets[1] <= 31:
                raise InvalidURLError(
                    f"URL host {hostname} is not allowed. "
                    "Private IP addresses (172.16-31.x.x) are not supported."
                )
            # 192.168.0.0/16
            if octets[0] == 192 and octets[1] == 168:
                raise InvalidURLError(
                    f"URL host {hostname} is not allowed. "
                    "Private IP addresses (192.168.x.x) are not supported."
                )
            # 127.0.0.0/8 (loopback)
            if octets[0] == 127:
                raise InvalidURLError(
                    f"URL host {hostname} is not allowed. "
                    "Loopback address (127.x.x.x) is not supported."
                )
        except ValueError:
            # If octets aren't valid integers, continue without IP checking
            pass

    return url


# ─────────────────────────── abstract base ───────────────────────────────────

class BaseRepositoryProvider(ABC):
    """
    Contract every provider must satisfy.

    Subclasses receive a sanitised URL; input validation is done by the
    factory before the constructor is called.
    """

    def __init__(self, url: str, token: str | None = None) -> None:
        self.url = url
        self.token = token
        self._owner, self._repo = self._parse(url)

    # ── interface ──────────────────────────────────────────────────────────

    @abstractmethod
    def _parse(self, url: str) -> tuple[str, str]:
        """Extract (owner, repo) from a sanitised URL. Raise InvalidURLError on bad shape."""

    @abstractmethod
    def fetch_readme(self) -> str:
        """Return raw README text, or '' if the repo has none."""

    @abstractmethod
    def fetch_topics(self) -> list[str]:
        """Return list of topic / tag strings (may be empty)."""

    # ── shared helpers ─────────────────────────────────────────────────────

    def _base_headers(self) -> dict:
        return {}

    def _raise_for_status(self, r: requests.Response, context: str) -> None:
        """
        Translate HTTP error codes into typed ProviderErrors.
        *context* is a short human-readable description of the call.
        """
        code = r.status_code

        if code == 200:
            return

        if code == 404:
            raise RepositoryNotFoundError(
                f"{context}: repository not found (404). "
                "Check the URL, or supply a token if the repository is private."
            )

        if code == 429:
            retry = r.headers.get("Retry-After", "unknown")
            raise RateLimitError(
                f"{context}: rate-limited (429). Retry after {retry}s."
            )

        # GitHub secondary rate limit comes back as 403 with a specific body
        if code == 403 and "rate limit" in r.text.lower():
            raise RateLimitError(
                f"{context}: secondary rate limit hit (403). "
                "Slow down requests or supply an authenticated token."
            )

        if code == 401:
            raise FetchError(
                f"{context}: authentication failed (401). "
                "The token is invalid or has insufficient scope."
            )

        if code == 403:
            raise FetchError(
                f"{context}: forbidden (403). "
                "The repository may be private and the token lacks access."
            )

        # Anything else
        try:
            r.raise_for_status()
        except requests.HTTPError as exc:
            raise FetchError(f"{context}: HTTP {code}.") from exc

    def _get(self, url: str, *, context: str, **kwargs) -> requests.Response:
        """
        GET with unified network-error handling.
        Callers are responsible for supplying headers= (merged with _base_headers()).
        """
        kwargs.setdefault("headers", self._base_headers())
        try:
            r = requests.get(url, timeout=30, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            raise FetchError(
                f"{context}: could not connect. Check network or host availability."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise FetchError(f"{context}: request timed out after 30 s.") from exc
        except requests.exceptions.RequestException as exc:
            raise FetchError(f"{context}: network error — {exc}") from exc

        self._raise_for_status(r, context)
        return r


# ─────────────────────────── GitHub ──────────────────────────────────────────

class GitHubProvider(BaseRepositoryProvider):
    _API = "https://api.github.com"

    # owner and repo are both 1-39 chars: alphanumeric + hyphen (not at start/end)
    _SEGMENT = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$|^[A-Za-z0-9]$')

    def _parse(self, url: str) -> tuple[str, str]:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise InvalidURLError(
                f"GitHub URL must have the form https://github.com/owner/repo. Got: {url!r}"
            )
        owner = parts[0]
        repo  = parts[1].removesuffix(".git")

        for label, value in (("owner", owner), ("repo", repo)):
            if not self._SEGMENT.match(value):
                raise InvalidURLError(
                    f"GitHub {label} name {value!r} contains invalid characters."
                )

        return owner, repo

    def _base_headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "User-Agent": "sdg-classifier"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def fetch_readme(self) -> str:
        headers = {**self._base_headers(), "Accept": "application/vnd.github.v3.raw"}
        try:
            r = self._get(
                f"{self._API}/repos/{self._owner}/{self._repo}/readme",
                context="GitHub fetch_readme",
                headers=headers,
            )
        except RepositoryNotFoundError:
            return ""          # no README is a valid state, not an error
        return r.text

    def fetch_topics(self) -> list[str]:
        headers = {
            **self._base_headers(),
            "Accept": "application/vnd.github.mercy-preview+json",
        }
        r = self._get(
            f"{self._API}/repos/{self._owner}/{self._repo}",
            context="GitHub fetch_topics",
            headers=headers,
        )
        return r.json().get("topics", [])

    def fetch_meta(self) -> dict:
        """name, description, homepage — convenience method beyond the contract."""
        r = self._get(
            f"{self._API}/repos/{self._owner}/{self._repo}",
            context="GitHub fetch_meta",
        )
        d = r.json()
        return {
            "name":        d.get("name", ""),
            "description": d.get("description", ""),
            "homepage":    d.get("homepage", ""),
        }


# ─────────────────────────── GitLab ──────────────────────────────────────────

class GitLabProvider(BaseRepositoryProvider):
    """
    GitLab REST API v4 — works against gitlab.com AND self-hosted GitLab
    CE/EE instances, since the API contract is identical regardless of host.

    Docs: https://docs.gitlab.com/api/repository_files/
          https://docs.gitlab.com/api/projects/

    Key facts from the docs:
    - Project ID in URL-encoded path form: namespace%2Frepo (quote safe="")
    - Files API: GET /projects/:id/repository/files/:file_path/raw?ref=HEAD
      - ref=HEAD resolves the default branch automatically — no guessing needed
      - :file_path must also be URL-encoded (e.g. README.md stays as-is;
        docs/readme.rst → docs%2Freadme.rst)
    - Project endpoint returns `readme_url` and `default_branch` — we use
      readme_url to extract the actual readme filename rather than hardcoding
      README.md, covering .rst, .txt, and other variants
    - topics field (not deprecated tag_list) contains the tag list
    - Auth: PRIVATE-TOKEN header (not Bearer) for personal/project tokens;
      Authorization: Bearer for OAuth tokens

    Self-hosted note: `_api_base` is set per-instance (not a hardcoded class
    constant) so the same provider class serves gitlab.com and any number
    of self-hosted GitLab instances (e.g. git.gfz-potsdam.de, framagit.org).
    The factory passes the correct base via the `api_base` constructor kwarg.
    """
    _DEFAULT_API_BASE = "https://gitlab.com/api/v4"

    def __init__(self, url: str, token: str | None = None, api_base: str | None = None) -> None:
        # Derive the API base from the URL's own host if not explicitly given,
        # so this class works correctly even if instantiated directly without
        # going through get_provider()'s registry.
        if api_base is None:
            host = urlparse(url).hostname or "gitlab.com"
            api_base = f"https://{host}/api/v4"
        self._api_base = api_base
        super().__init__(url, token=token)

    @property
    def _API(self) -> str:
        return self._api_base

    def _parse(self, url: str) -> tuple[str, str]:
        path  = urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]   # drop empty segments
        if len(parts) < 2:
            raise InvalidURLError(
                f"GitLab URL must have at least owner and repo. Got: {url!r}"
            )
        owner = "/".join(parts[:-1])   # supports group/subgroup/… nesting
        repo  = parts[-1].removesuffix(".git")
        return owner, repo

    def _base_headers(self) -> dict:
        h = {"User-Agent": "sdg-classifier", "Accept": "application/json"}
        if self.token:
            h["PRIVATE-TOKEN"] = self.token
        return h

    def _encoded_path(self) -> str:
        """URL-encode the full namespace/repo path as required by the GitLab v4 API."""
        return quote(f"{self._owner}/{self._repo}", safe="")

    def _readme_filename(self, project_json: dict) -> str | None:
        """
        Extract the actual readme filename from the project's readme_url field.
        e.g. "…/blob/main/README.rst" → "README.rst"
        Falls back to None if the field is absent or unparseable.
        """
        readme_url = project_json.get("readme_url") or ""
        if not readme_url:
            return None
        # readme_url looks like: https://gitlab.com/group/repo/-/blob/main/README.md
        # We want the last path component after the branch name.
        try:
            path_part = urlparse(readme_url).path   # /group/repo/-/blob/main/README.md
            return path_part.split("/")[-1] or None
        except Exception:
            return None

    def fetch_readme(self) -> str:
        """
        Two-step fetch:
        1. GET /projects/:id  — to learn the actual readme filename via readme_url
           and confirm the repo exists. ref=HEAD on the files endpoint resolves
           the default branch automatically per docs.
        2. GET /projects/:id/repository/files/:file_path/raw?ref=HEAD
           Returns raw text directly (no base64, no JSON wrapper).
        """
        # Step 1: fetch project metadata
        try:
            meta_r = self._get(
                f"{self._API}/projects/{self._encoded_path()}",
                context="GitLab fetch_readme (project meta)",
            )
        except RepositoryNotFoundError:
            return ""

        readme_filename = self._readme_filename(meta_r.json()) or "README.md"
        # File path in the API must be URL-encoded (forward slashes → %2F)
        encoded_file = quote(readme_filename, safe="")

        # Step 2: fetch raw file content using ref=HEAD (resolves default branch)
        try:
            r = self._get(
                f"{self._API}/projects/{self._encoded_path()}"
                f"/repository/files/{encoded_file}/raw",
                context="GitLab fetch_readme (raw file)",
                params={"ref": "HEAD"},
            )
            return r.text
        except RepositoryNotFoundError:
            return ""   # readme_url pointed at a file that doesn't exist — edge case

    def fetch_topics(self) -> list[str]:
        """
        Returns the `topics` field from the project object.
        (`tag_list` is deprecated per GitLab docs — use `topics` only.)
        """
        r = self._get(
            f"{self._API}/projects/{self._encoded_path()}",
            context="GitLab fetch_topics",
        )
        return r.json().get("topics", [])


# ─────────────────────────── Codeberg / Gitea / Forgejo ──────────────────────

class CodebergProvider(BaseRepositoryProvider):
    """
    Codeberg runs Forgejo (a Gitea fork) exposing REST API v1. This class
    also serves any other Gitea/Forgejo instance, since the API contract
    (raw file endpoint, repo object shape, topics endpoint) is the same
    software family regardless of host — only the base URL differs.

    Swagger: https://codeberg.org/api/swagger
    Docs: https://forgejo.org/docs/latest/user/api-usage/
          https://docs.gitea.com/api/

    Key facts from the docs:
    - Auth header: `Authorization: token <PAT>` (not Bearer)
    - Raw file endpoint: GET /repos/{owner}/{repo}/raw/{filepath}?ref={branch}
      Returns raw text directly — no base64, no JSON wrapper.
      (Confirmed: https://codeberg.org/forgejo/forgejo/issues/901)
    - Repo endpoint: GET /repos/{owner}/{repo}
      Returns `default_branch` — use this instead of guessing branch names.
    - Topics endpoint: GET /repos/{owner}/{repo}/topics
      Returns {"topics": [...]} — separate from the repo object.
    - The /contents/{filepath} endpoint exists but returns base64 JSON;
      /raw/{filepath} is the correct choice for plain text.
    - Version probe (used by _detect_engine in the factory section below):
      GET /api/v1/version → {"version": "..."} — present on both Gitea
      and Forgejo, including Codeberg itself.

    Self-hosted note: `_api_base` is set per-instance (not a hardcoded class
    constant), mirroring GitLabProvider's pattern, so this same class
    correctly serves codeberg.org and any other detected Gitea/Forgejo host.
    """
    _DEFAULT_API_BASE = "https://codeberg.org/api/v1"

    def __init__(self, url: str, token: str | None = None, api_base: str | None = None) -> None:
        if api_base is None:
            host = urlparse(url).hostname or "codeberg.org"
            api_base = f"https://{host}/api/v1"
        self._api_base = api_base
        super().__init__(url, token=token)

    @property
    def _API(self) -> str:
        return self._api_base

    def _parse(self, url: str) -> tuple[str, str]:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if len(parts) < 2:
            raise InvalidURLError(
                f"Codeberg URL must have the form https://codeberg.org/owner/repo. "
                f"Got: {url!r}"
            )
        owner = parts[0]
        repo  = parts[1].removesuffix(".git")
        return owner, repo

    def _base_headers(self) -> dict:
        h = {"User-Agent": "sdg-classifier", "Accept": "application/json"}
        if self.token:
            # Forgejo requires the literal word "token" before the PAT
            h["Authorization"] = f"token {self.token}"
        return h

    def _default_branch(self) -> str:
        """
        Fetch the repo's actual default branch from the repo object.
        Falls back to 'main' if the call fails for any reason.
        """
        try:
            r = self._get(
                f"{self._API}/repos/{self._owner}/{self._repo}",
                context="Codeberg default_branch",
            )
            return r.json().get("default_branch") or "main"
        except ProviderError:
            return "main"

    def fetch_readme(self) -> str:
        """
        Uses the /raw/{filepath} endpoint which returns plain text directly.
        Branch is resolved from the repo object (default_branch field) —
        no hardcoded branch guessing.

        Tries README.md, then README.rst, then README.txt in that order,
        all on the default branch.
        """
        branch = self._default_branch()

        for filename in ("README.md", "README.rst", "README.txt", "readme.md"):
            try:
                r = self._get(
                    f"{self._API}/repos/{self._owner}/{self._repo}/raw/{filename}",
                    context=f"Codeberg fetch_readme ({filename})",
                    params={"ref": branch},
                    # Override Accept — this endpoint returns text/plain, not JSON
                    headers={**self._base_headers(), "Accept": "text/plain"},
                )
                if r.text.strip():
                    return r.text
            except RepositoryNotFoundError:
                continue   # file doesn't exist, try the next name
        return ""

    def fetch_topics(self) -> list[str]:
        """
        Uses the dedicated /topics endpoint (returns {"topics": [...]}).
        Separate from the repo object per the Forgejo API spec.
        """
        try:
            r = self._get(
                f"{self._API}/repos/{self._owner}/{self._repo}/topics",
                context="Codeberg fetch_topics",
            )
            return r.json().get("topics", [])
        except RepositoryNotFoundError:
            return []


# ─────────────────────────── Bitbucket (Cloud) ───────────────────────────────

class BitbucketProvider(BaseRepositoryProvider):
    """
    Bitbucket Cloud REST API v2.0.
    Docs: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-source/
          https://developer.atlassian.com/cloud/bitbucket/rest/api-group-repositories/

    Key facts from the docs:
    - Workspace/repo terminology: Bitbucket calls the owner segment a
      "workspace" and the repo a "repo_slug" — same two-segment URL shape
      as GitHub/GitLab/Codeberg though, so _parse() is unchanged in form.
    - Repo object: GET /2.0/repositories/{workspace}/{repo_slug}
      Returns `name`, `description`, `language` (closest equivalent to
      "topics" — Bitbucket has no tag/topic system), and `mainbranch.name`.
    - Source endpoint: GET /2.0/repositories/{workspace}/{repo_slug}/src/{branch}/{path}
      Returns the RAW file content directly when path matches a file
      (confirmed in docs: "the raw contents of the file are returned").
      No base64, no JSON wrapper — same ergonomics as GitHub's v3.raw header.
    - Unlike GitLab's ref=HEAD, Bitbucket's /src/ endpoint has NO magic
      "default branch" alias — the branch name (or commit hash) must be
      given explicitly. We fetch `mainbranch.name` from the repo object
      first, mirroring what CodebergProvider does for default_branch.
    - Auth: Bearer token (OAuth 2.0 / API token) via Authorization header.
      App passwords use HTTP Basic auth instead — not supported here since
      the rest of this module standardizes on bearer-style tokens.
    - No native "topics" concept. `language` is returned as `topics` (a
      single-element list) so the corpus assembly in fetch_repo_text still
      gets a meaningful signal instead of an empty list.

    Wiki URLs:
    - A URL like .../workspace/repo_slug/wiki/Home points at a *separate*
      Git repository (the wiki), not the main repo's source tree. Per
      Atlassian docs: "Wikis can be exported via cloning since they are
      stored as a separate repository."
    - We detect the /wiki/ segment in _parse() so the provider still
      resolves to the correct workspace/repo_slug (silently dropping the
      wiki path would otherwise hide from the caller that a wiki page,
      not the repo root, was pasted).
    - The wiki repo is addressable at the same /src/ endpoint pattern
      using "{repo_slug}.wiki" as the repo_slug — confirmed by Bitbucket's
      git clone convention (git clone .../repo_slug.git/wiki, exposed via
      the API as a sibling repo named "{repo_slug}.wiki").
    - fetch_readme() prefers actual README files on the main repo; if none
      exist AND the original URL pointed at a wiki, fetch_wiki_home() can
      be called explicitly to pull the wiki's Home page as a fallback —
      kept as a separate opt-in method rather than silently folded into
      fetch_readme(), since wiki content is being deprecated by Bitbucket
      (removal announced for August 20, 2026) and shouldn't become a load
      bearing part of the corpus pipeline.
    """
    _API = "https://api.bitbucket.org/2.0"

    def _parse(self, url: str) -> tuple[str, str]:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if len(parts) < 2:
            raise InvalidURLError(
                f"Bitbucket URL must have the form "
                f"https://bitbucket.org/workspace/repo_slug. Got: {url!r}"
            )
        workspace = parts[0]
        repo_slug = parts[1].removesuffix(".git")

        # Detect /wiki/... so callers can know this was a wiki link, not a
        # repo-root link, without us silently discarding that information.
        self._is_wiki_url = len(parts) > 2 and parts[2] == "wiki"

        return workspace, repo_slug

    def _base_headers(self) -> dict:
        h = {"User-Agent": "sdg-classifier", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _repo_meta(self) -> dict:
        """Fetch the repo object once; used by both fetch_readme and fetch_meta."""
        r = self._get(

            f"{self._API}/repositories/{self._owner}/{self._repo}",
            context="Bitbucket repo meta",
        )
        return r.json()

    def fetch_readme(self) -> str:
        """
        Two-step fetch, mirroring the GitLab/Codeberg pattern:
        1. GET the repo object to learn mainbranch.name (no ref=HEAD alias exists)
        2. GET /src/{branch}/{filename} for each candidate readme filename —
           the docs confirm this returns raw file content directly when the
           path resolves to a file.

        If the original URL was a /wiki/... link AND the main repo has no
        README at all, falls back to the wiki's Home page — better than
        returning empty text when the user explicitly pointed at the wiki.
        """
        try:
            meta = self._repo_meta()
        except RepositoryNotFoundError:
            return ""

        branch = (meta.get("mainbranch") or {}).get("name") or "master"

        for filename in ("README.md", "README.rst", "README.txt", "readme.md"):
            try:
                r = self._get(
                    f"{self._API}/repositories/{self._owner}/{self._repo}"
                    f"/src/{branch}/{filename}",
                    context=f"Bitbucket fetch_readme ({filename})",
                    headers={**self._base_headers(), "Accept": "text/plain"},
                )
                if r.text.strip():
                    return r.text
            except RepositoryNotFoundError:
                continue   # this filename doesn't exist on this branch, try next

        if getattr(self, "_is_wiki_url", False):
            try:
                return self.fetch_wiki_home()
            except ProviderError:
                pass

        return ""

    def fetch_wiki_home(self) -> str:
        """
        Fetch the wiki's Home page content.

        Bitbucket wikis are stored as a separate Git repository, addressable
        via the same /src/ endpoint pattern but under "{repo_slug}.wiki" as
        the repo_slug — this mirrors Bitbucket's own git clone convention
        for wiki repos.

        Deprecation note: Atlassian has announced wiki removal from
        Bitbucket Cloud on 2026-08-20. This method will start returning
        empty/404 for all repos after that date; callers should not treat
        it as a permanent data source.
        """
        wiki_repo_slug = f"{self._repo}.wiki"

        
        for filename in ("Home.md", "Home.rst", "Home.creole", "home.md"):
            try:
                r = self._get(
                    f"{self._API}/repositories/{self._owner}/{wiki_repo_slug}"
                    f"/src/master/{filename}",
                    context=f"Bitbucket fetch_wiki_home ({filename})",
                    headers={**self._base_headers(), "Accept": "text/plain"},
                )
                if r.text.strip():
                    return r.text
            except RepositoryNotFoundError:
                continue
        return ""

    def fetch_topics(self) -> list[str]:
        """
        Bitbucket has no topics/tags system. The closest equivalent signal
        is the repo's primary `language` field. Returned as a single-element
        list so callers (e.g. fetch_repo_text's " ".join(topics)) work
        unchanged regardless of which provider supplied the data.
        """
        meta = self._repo_meta()
        language = meta.get("language") or ""
        return [language] if language else []

    def fetch_meta(self) -> dict:
        """name, description, homepage — Bitbucket has no homepage field,
        so we leave it empty for parity with the other providers' shape."""
        meta = self._repo_meta()
        return {
            "name":        meta.get("name", ""),
            "description": meta.get("description", ""),
            "homepage":    "",   # Bitbucket repo objects don't expose this
        }


# ─────────────────────────── factory ─────────────────────────────────────────

def _rewrite_github_pages(url: str) -> str:
    """
    Detect a GitHub Pages URL and rewrite it to the underlying repo URL.

    GitHub Pages sites are published at:
        https://{owner}.github.io                  → user/org root site
        https://{owner}.github.io/{repo}            → project site (most common)
        https://{owner}.github.io/{repo}/sub/path   → project site, deep link

    The README and topics live on the real repo (github.com/{owner}/{repo}),
    not on the Pages host, so we resolve to that before routing.

    Root-level Pages sites (no repo segment, e.g. https://emapr.github.io)
    map by GitHub convention to a repo literally named "{owner}.github.io" —
    we rewrite to that rather than guessing.

    Non-Pages URLs are returned unchanged.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if not host.endswith(".github.io"):
        return url

    owner = host[: -len(".github.io")]
    if not owner:
        return url   

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    if path_parts:
        repo = path_parts[0]
    else:
        repo = host

    return f"https://github.com/{owner}/{repo}"


_DOMAIN_MAP: dict[str, type[BaseRepositoryProvider]] = {
    "github.com":        GitHubProvider,
    "www.github.com":    GitHubProvider,
    "gitlab.com":        GitLabProvider,
    "www.gitlab.com":    GitLabProvider,
    "codeberg.org":      CodebergProvider,
    "bitbucket.org":     BitbucketProvider,
    "www.bitbucket.org": BitbucketProvider,

    # ── Self-hosted GitLab CE/EE instances ──────────────────────────────────
    # All confirmed via direct verification (GitLab Community/Enterprise
    # Edition footer, "GitLab Community Edition" branding on the explore
    # pages, or official documentation) to run unmodified GitLab, meaning
    # the API contract is byte-identical to gitlab.com — only the host
    # differs. GitLabProvider derives `_api_base` from the URL's own
    # hostname automatically (see GitLabProvider.__init__), so registering
    # these here is purely about passing the UnsupportedHostError gate;
    # no new provider code is needed per domain.
    "framagit.org":                          GitLabProvider,
    "git.ufz.de":                             GitLabProvider,
    "gitlab.inria.fr":                        GitLabProvider,
    "git.gfz-potsdam.de":                     GitLabProvider,
    "gitlab.dkrz.de":                         GitLabProvider,
    "invent.kde.org":                         GitLabProvider,
    "gricad-gitlab.univ-grenoble-alpes.fr":   GitLabProvider,
    "code.usgs.gov":                          GitLabProvider,
    "code.europa.eu":                         GitLabProvider,
    "git.geomar.de":                          GitLabProvider,
    "git.rwth-aachen.de":                     GitLabProvider,
    "forge.ird.fr":                           GitLabProvider,
    "gitlab.dune-project.org":                GitLabProvider,
    "git.wur.nl":                             GitLabProvider,
    "gitlab.heigit.org":                      GitLabProvider,
}

SUPPORTED_HOSTS = sorted({h.removeprefix("www.") for h in _DOMAIN_MAP})


def _detect_engine(host: str) -> type[BaseRepositoryProvider] | None:
    """
    Probe an unregistered host to identify which forge engine it runs,
    so unknown self-hosted GitLab/Gitea/Forgejo instances work without
    requiring a manual _DOMAIN_MAP entry.

    Detection is based on each engine's own version endpoint, which is
    cheap (small JSON payload, no auth needed) and stable across versions:

      GitLab CE/EE        GET /api/v4/version        → {"version": "..."}
      Gitea / Forgejo      GET /api/v1/version        → {"version": "..."}

    GitHub Enterprise Server is deliberately NOT probed here: it requires
    a different base path (/api/v3) and reliable detection needs the
    X-GitHub-Enterprise-Version response header, which is a separate,
    slightly riskier heuristic (some reverse proxies strip custom headers).
    Self-hosted GitHub Enterprise is rare enough in the open-source/DPG
    space this tool targets that we leave it as an explicit _DOMAIN_MAP
    addition rather than a guess.

    Returns the provider class on a confident match, or None if neither
    probe succeeds (caller falls through to UnsupportedHostError).
    Network failures during probing are swallowed — a failed probe just
    means "couldn't confirm", not "definitely unsupported".
    """
    probes: list[tuple[str, type[BaseRepositoryProvider]]] = [
        (f"https://{host}/api/v4/version", GitLabProvider),
        (f"https://{host}/api/v1/version",  CodebergProvider),  # Gitea/Forgejo-compatible
    ]

    for probe_url, cls in probes:
        try:
            r = requests.get(
                probe_url,
                headers={"User-Agent": "sdg-classifier", "Accept": "application/json"},
                timeout=5,   
            )
            if r.status_code == 200:
                body = r.json()
                if isinstance(body, dict) and "version" in body:
                    return cls
        except (requests.exceptions.RequestException, ValueError):
            continue   

    return None


def get_provider(repo_url: object, token: str | None = None) -> BaseRepositoryProvider:
    """
    Validate *repo_url*, route to the correct provider, and return an instance.

    Parameters
    ----------
    repo_url : str
        Full URL to a public (or token-accessible) repository.
        GitHub Pages URLs (*.github.io) are automatically rewritten to the
        underlying github.com repo URL before routing.
    token : str | None
        Optional PAT / API token for the target host.

    Routing order:
      1. Exact match in _DOMAIN_MAP (known hosts — fast, no network call)
      2. Engine detection probe (_detect_engine) — for unregistered hosts,
         tries GitLab's and Gitea/Forgejo's version endpoints to identify
         the engine without requiring a manual domain registration

    Raises
    ------
    InvalidURLError        bad type, empty, wrong scheme, or missing owner/repo
    UnsupportedHostError   domain not in the registry AND engine detection
                            found neither GitLab nor Gitea/Forgejo
    (Other errors are raised lazily when fetch_* methods are called.)
    """
    
    url = _sanitise_url(repo_url)           # type + format guard
    url = _rewrite_github_pages(url)        # *.github.io → github.com/owner/repo

    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower()

    cls = _DOMAIN_MAP.get(domain)

    if cls is None:
        cls = _detect_engine(domain)

    if cls is None:
        raise UnsupportedHostError(
            f"Host {domain!r} is not supported. "
            f"Supported hosts: {', '.join(SUPPORTED_HOSTS)}. "
            f"Engine auto-detection (GitLab/Gitea/Forgejo) also found no match — "
            f"this may be GitHub Enterprise, Bitbucket Server, or an unsupported host."
        )

    return cls(url, token=token)

def main():
    get_provider("https://gitlab.com/trapper-project/trapper")


if __name__ == "__main__":
    main()
