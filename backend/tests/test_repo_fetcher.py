"""
Unit tests for backend/services/repo_fetcher.py.

No real network access — every HTTP call goes through a mocked
`requests.get`, so these run fully offline and fast. See docs/TESTING.md
§1 for the coverage checklist this file implements.
"""

from unittest.mock import MagicMock

import pytest
import requests

import repo_fetcher
from repo_fetcher import (
    BitbucketProvider,
    CodebergProvider,
    FetchError,
    GitHubProvider,
    GitLabProvider,
    InvalidURLError,
    RateLimitError,
    RepositoryNotFoundError,
    SUPPORTED_HOSTS,
    UnsupportedHostError,
    _detect_engine,
    _rewrite_github_pages,
    _sanitise_url,
    get_provider,
)


def _mock_response(status_code=200, json_data=None, text="", headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    resp.json = MagicMock(return_value=json_data if json_data is not None else {})
    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=requests.HTTPError(f"{status_code} error")
        )
    else:
        resp.raise_for_status = MagicMock(return_value=None)
    return resp


# ─────────────────────────── _sanitise_url ───────────────────────────────────

class TestSanitiseUrl:
    def test_valid_url_is_stripped(self):
        assert _sanitise_url("  https://github.com/owner/repo  ") == (
            "https://github.com/owner/repo"
        )

    def test_valid_bytes_decoded(self):
        assert _sanitise_url(b"https://github.com/owner/repo") == (
            "https://github.com/owner/repo"
        )

    def test_invalid_utf8_bytes_raise(self):
        with pytest.raises(InvalidURLError):
            _sanitise_url(b"\xff\xfe")

    @pytest.mark.parametrize("bad", [None, 123, ["a"], {"a": 1}])
    def test_non_string_types_raise(self, bad):
        with pytest.raises(InvalidURLError):
            _sanitise_url(bad)

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_empty_or_whitespace_raises(self, bad):
        with pytest.raises(InvalidURLError):
            _sanitise_url(bad)

    def test_no_scheme_raises(self):
        with pytest.raises(InvalidURLError):
            _sanitise_url("owner/repo")

    @pytest.mark.parametrize("scheme", ["ftp", "git", "ssh"])
    def test_non_http_scheme_raises(self, scheme):
        with pytest.raises(InvalidURLError):
            _sanitise_url(f"{scheme}://github.com/owner/repo")

    def test_missing_hostname_raises(self):
        with pytest.raises(InvalidURLError):
            _sanitise_url("https:///owner/repo")


# ─────────────────────────── _rewrite_github_pages ───────────────────────────

class TestRewriteGithubPages:
    def test_root_pages_site_maps_to_owner_dot_github_io_repo(self):
        assert _rewrite_github_pages("https://emapr.github.io") == (
            "https://github.com/emapr/emapr.github.io"
        )

    def test_project_pages_site(self):
        assert _rewrite_github_pages("https://owner.github.io/repo") == (
            "https://github.com/owner/repo"
        )

    def test_project_pages_site_deep_link(self):
        assert _rewrite_github_pages("https://owner.github.io/repo/sub/path") == (
            "https://github.com/owner/repo"
        )

    def test_non_pages_url_unchanged(self):
        url = "https://github.com/owner/repo"
        assert _rewrite_github_pages(url) == url


# ─────────────────────────── provider _parse ─────────────────────────────────

class TestGitHubParse:
    def test_valid_owner_repo(self):
        p = GitHubProvider("https://github.com/torvalds/linux")
        assert (p._owner, p._repo) == ("torvalds", "linux")

    def test_strips_dot_git_suffix(self):
        p = GitHubProvider("https://github.com/torvalds/linux.git")
        assert p._repo == "linux"

    def test_missing_repo_segment_raises(self):
        with pytest.raises(InvalidURLError):
            GitHubProvider("https://github.com/torvalds")

    def test_invalid_characters_raise(self):
        with pytest.raises(InvalidURLError):
            GitHubProvider("https://github.com/owner/repo with spaces")


class TestGitLabParse:
    def test_valid_owner_repo(self):
        p = GitLabProvider("https://gitlab.com/gitlab-org/gitlab")
        assert (p._owner, p._repo) == ("gitlab-org", "gitlab")

    def test_nested_subgroups(self):
        p = GitLabProvider("https://gitlab.com/group/subgroup/project")
        assert (p._owner, p._repo) == ("group/subgroup", "project")

    def test_strips_dot_git_suffix(self):
        p = GitLabProvider("https://gitlab.com/group/project.git")
        assert p._repo == "project"

    def test_missing_repo_segment_raises(self):
        with pytest.raises(InvalidURLError):
            GitLabProvider("https://gitlab.com/onlyowner")

    def test_encoded_path_escapes_slashes(self):
        p = GitLabProvider("https://gitlab.com/group/subgroup/project")
        assert p._encoded_path() == "group%2Fsubgroup%2Fproject"

    def test_self_hosted_api_base_derived_from_host(self):
        p = GitLabProvider("https://framagit.org/group/project")
        assert p._API == "https://framagit.org/api/v4"


class TestCodebergParse:
    def test_valid_owner_repo(self):
        p = CodebergProvider("https://codeberg.org/forgejo/forgejo")
        assert (p._owner, p._repo) == ("forgejo", "forgejo")

    def test_missing_repo_segment_raises(self):
        with pytest.raises(InvalidURLError):
            CodebergProvider("https://codeberg.org/onlyowner")


class TestBitbucketParse:
    def test_valid_workspace_repo_slug(self):
        p = BitbucketProvider("https://bitbucket.org/cioapps/wapor-et-look")
        assert (p._owner, p._repo) == ("cioapps", "wapor-et-look")
        assert p._is_wiki_url is False

    def test_wiki_url_detected(self):
        p = BitbucketProvider("https://bitbucket.org/cioapps/wapor-et-look/wiki/Home")
        assert p._is_wiki_url is True

    def test_missing_repo_segment_raises(self):
        with pytest.raises(InvalidURLError):
            BitbucketProvider("https://bitbucket.org/onlyworkspace")


# ─────────────────────────── _raise_for_status / _get ────────────────────────

class TestRaiseForStatusAndGet:
    """Exercised through GitHubProvider._get since the logic lives on the
    shared BaseRepositoryProvider and GitHubProvider is a concrete stand-in."""

    def _provider(self):
        return GitHubProvider("https://github.com/owner/repo")

    def test_200_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(200)))
        r = self._provider()._get("http://x", context="ctx")
        assert r.status_code == 200

    def test_404_raises_repository_not_found(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(404)))
        with pytest.raises(RepositoryNotFoundError):
            self._provider()._get("http://x", context="ctx")

    def test_429_raises_rate_limit_with_retry_after(self, monkeypatch):
        resp = _mock_response(429, headers={"Retry-After": "42"})
        monkeypatch.setattr(repo_fetcher.requests, "get", MagicMock(return_value=resp))
        with pytest.raises(RateLimitError, match="42"):
            self._provider()._get("http://x", context="ctx")

    def test_403_with_rate_limit_body_raises_rate_limit(self, monkeypatch):
        resp = _mock_response(403, text="Secondary Rate Limit exceeded")
        monkeypatch.setattr(repo_fetcher.requests, "get", MagicMock(return_value=resp))
        with pytest.raises(RateLimitError):
            self._provider()._get("http://x", context="ctx")

    def test_401_raises_fetch_error(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(401)))
        with pytest.raises(FetchError):
            self._provider()._get("http://x", context="ctx")

    def test_403_without_rate_limit_body_raises_fetch_error(self, monkeypatch):
        resp = _mock_response(403, text="Forbidden: private repository")
        monkeypatch.setattr(repo_fetcher.requests, "get", MagicMock(return_value=resp))
        with pytest.raises(FetchError):
            self._provider()._get("http://x", context="ctx")

    def test_other_error_code_raises_fetch_error(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(500)))
        with pytest.raises(FetchError):
            self._provider()._get("http://x", context="ctx")

    def test_connection_error_wrapped_as_fetch_error(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=requests.exceptions.ConnectionError()),
        )
        with pytest.raises(FetchError):
            self._provider()._get("http://x", context="ctx")

    def test_timeout_wrapped_as_fetch_error(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=requests.exceptions.Timeout()),
        )
        with pytest.raises(FetchError):
            self._provider()._get("http://x", context="ctx")


# ─────────────────────────── GitHubProvider fetch_* ──────────────────────────

class TestGitHubFetch:
    def _provider(self):
        return GitHubProvider("https://github.com/owner/repo")

    def test_fetch_readme_returns_text(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, text="# Hello")),
        )
        assert self._provider().fetch_readme() == "# Hello"

    def test_fetch_readme_missing_returns_empty_string(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(404)))
        assert self._provider().fetch_readme() == ""

    def test_fetch_topics(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={"topics": ["a", "b"]})),
        )
        assert self._provider().fetch_topics() == ["a", "b"]

    def test_fetch_meta(self, monkeypatch):
        json_data = {"name": "repo", "description": "desc", "homepage": "http://x"}
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data=json_data)),
        )
        assert self._provider().fetch_meta() == json_data


# ─────────────────────────── GitLabProvider fetch_* ──────────────────────────

class TestGitLabFetch:
    def _provider(self):
        return GitLabProvider("https://gitlab.com/group/project")

    def test_fetch_readme_uses_filename_from_readme_url(self, monkeypatch):
        meta_resp = _mock_response(
            200,
            json_data={"readme_url": "https://gitlab.com/g/p/-/blob/main/README.rst"},
        )
        raw_resp = _mock_response(200, text="Gitlab readme content")
        mock_get = MagicMock(side_effect=[meta_resp, raw_resp])
        monkeypatch.setattr(repo_fetcher.requests, "get", mock_get)

        assert self._provider().fetch_readme() == "Gitlab readme content"
        second_call_url = mock_get.call_args_list[1].args[0]
        assert "README.rst" in second_call_url

    def test_fetch_readme_project_not_found_returns_empty(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(404)))
        assert self._provider().fetch_readme() == ""

    def test_readme_filename_defaults_to_readme_md(self):
        p = self._provider()
        assert p._readme_filename({}) is None

    def test_fetch_topics(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={"topics": ["x"]})),
        )
        assert self._provider().fetch_topics() == ["x"]


# ─────────────────────────── CodebergProvider fetch_* ────────────────────────

class TestCodebergFetch:
    def _provider(self):
        return CodebergProvider("https://codeberg.org/forgejo/forgejo")

    def test_fetch_readme_first_filename_succeeds(self, monkeypatch):
        branch_resp = _mock_response(200, json_data={"default_branch": "main"})
        readme_resp = _mock_response(200, text="Codeberg readme")
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=[branch_resp, readme_resp]),
        )
        assert self._provider().fetch_readme() == "Codeberg readme"

    def test_default_branch_falls_back_to_main_on_error(self, monkeypatch):
        branch_resp = _mock_response(500)
        readme_resp = _mock_response(200, text="content")
        mock_get = MagicMock(side_effect=[branch_resp, readme_resp])
        monkeypatch.setattr(repo_fetcher.requests, "get", mock_get)

        assert self._provider().fetch_readme() == "content"
        second_call_params = mock_get.call_args_list[1].kwargs.get("params")
        assert second_call_params == {"ref": "main"}

    def test_fetch_readme_all_filenames_missing_returns_empty(self, monkeypatch):
        branch_resp = _mock_response(200, json_data={"default_branch": "main"})
        not_found = _mock_response(404)
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=[branch_resp, not_found, not_found, not_found, not_found]),
        )
        assert self._provider().fetch_readme() == ""

    def test_fetch_topics(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={"topics": ["y"]})),
        )
        assert self._provider().fetch_topics() == ["y"]

    def test_fetch_topics_not_found_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(404)))
        assert self._provider().fetch_topics() == []


# ─────────────────────────── BitbucketProvider fetch_* ───────────────────────

class TestBitbucketFetch:
    def _provider(self, url="https://bitbucket.org/cioapps/wapor-et-look"):
        return BitbucketProvider(url)

    def test_fetch_readme_uses_mainbranch_name(self, monkeypatch):
        meta_resp = _mock_response(200, json_data={"mainbranch": {"name": "develop"}})
        readme_resp = _mock_response(200, text="Bitbucket readme")
        mock_get = MagicMock(side_effect=[meta_resp, readme_resp])
        monkeypatch.setattr(repo_fetcher.requests, "get", mock_get)

        assert self._provider().fetch_readme() == "Bitbucket readme"
        second_call_url = mock_get.call_args_list[1].args[0]
        assert "/src/develop/README.md" in second_call_url

    def test_fetch_readme_repo_not_found_returns_empty(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher.requests, "get",
                             MagicMock(return_value=_mock_response(404)))
        assert self._provider().fetch_readme() == ""

    def test_fetch_readme_falls_back_to_wiki_home(self, monkeypatch):
        meta_resp = _mock_response(200, json_data={"mainbranch": {"name": "master"}})
        not_found = _mock_response(404)
        wiki_resp = _mock_response(200, text="Wiki home content")
        mock_get = MagicMock(
            side_effect=[meta_resp, not_found, not_found, not_found, not_found, wiki_resp]
        )
        monkeypatch.setattr(repo_fetcher.requests, "get", mock_get)

        provider = self._provider(
            "https://bitbucket.org/cioapps/wapor-et-look/wiki/Home"
        )
        assert provider.fetch_readme() == "Wiki home content"

    def test_fetch_topics_returns_language_as_single_item_list(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={"language": "python"})),
        )
        assert self._provider().fetch_topics() == ["python"]

    def test_fetch_topics_empty_when_no_language(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={})),
        )
        assert self._provider().fetch_topics() == []

    def test_fetch_meta_homepage_always_empty(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(
                200, json_data={"name": "repo", "description": "desc"}
            )),
        )
        meta = self._provider().fetch_meta()
        assert meta == {"name": "repo", "description": "desc", "homepage": ""}


# ─────────────────────────── _detect_engine ──────────────────────────────────

class TestDetectEngine:
    def test_gitlab_probe_succeeds(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(200, json_data={"version": "16.0"})),
        )
        assert _detect_engine("git.example.org") is GitLabProvider

    def test_gitlab_fails_gitea_probe_succeeds(self, monkeypatch):
        gitlab_fail = requests.exceptions.RequestException("no gitlab here")
        gitea_ok = _mock_response(200, json_data={"version": "1.20"})
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=[gitlab_fail, gitea_ok]),
        )
        assert _detect_engine("git.example.org") is CodebergProvider

    def test_neither_probe_matches_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(return_value=_mock_response(404)),
        )
        assert _detect_engine("git.example.org") is None

    def test_network_failures_are_swallowed(self, monkeypatch):
        monkeypatch.setattr(
            repo_fetcher.requests, "get",
            MagicMock(side_effect=requests.exceptions.ConnectionError()),
        )
        assert _detect_engine("git.example.org") is None


# ─────────────────────────── get_provider factory ────────────────────────────

class TestGetProviderFactory:
    def test_known_domain_routes_without_network_call(self, monkeypatch):
        mock_get = MagicMock()
        monkeypatch.setattr(repo_fetcher.requests, "get", mock_get)

        provider = get_provider("https://github.com/torvalds/linux")

        assert isinstance(provider, GitHubProvider)
        mock_get.assert_not_called()

    def test_self_hosted_gitlab_domain_derives_api_base(self):
        provider = get_provider("https://framagit.org/group/project")
        assert isinstance(provider, GitLabProvider)
        assert provider._API == "https://framagit.org/api/v4"

    def test_github_pages_url_rewritten_before_routing(self):
        provider = get_provider("https://owner.github.io/repo")
        assert isinstance(provider, GitHubProvider)
        assert (provider._owner, provider._repo) == ("owner", "repo")

    def test_unregistered_host_falls_through_to_detect_engine(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher, "_detect_engine", lambda host: GitLabProvider)
        provider = get_provider("https://git.unknown-forge.example/group/project")
        assert isinstance(provider, GitLabProvider)

    def test_unsupported_host_raises_with_supported_hosts_listed(self, monkeypatch):
        monkeypatch.setattr(repo_fetcher, "_detect_engine", lambda host: None)
        with pytest.raises(UnsupportedHostError) as exc_info:
            get_provider("https://example.com/owner/repo")
        assert SUPPORTED_HOSTS[0] in str(exc_info.value)

    def test_invalid_input_raises_invalid_url_error(self):
        with pytest.raises(InvalidURLError):
            get_provider(None)

    def test_token_passed_through_to_provider(self):
        provider = get_provider("https://github.com/owner/repo", token="secret-token")
        assert provider.token == "secret-token"
