from pathlib import Path
import sys

import pytest

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

from get_baseline_hash import (
    BaselineLookupError,
    fetch_issues,
    filter_results,
    parse_baseline_hash,
    select_baseline_hash,
)


BASELINE_HASH = "0123456789abcdef0123456789abcdef01234567"


class FakeResponse:
    def __init__(self, status_code, payload=None, text="", links=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.links = links or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def issue(title, labels=None, pull_request=False):
    result = {"title": title, "labels": [{"name": label} for label in labels or []]}
    if pull_request:
        result["pull_request"] = {}
    return result


def test_filter_results_accepts_valid_baseline_issue():
    assert filter_results(issue(f"Testsuite Status {BASELINE_HASH}"))


def test_filter_results_rejects_failures_and_pull_requests():
    assert not filter_results(
        issue(f"Testsuite Status {BASELINE_HASH}", labels=["testsuite-failure"])
    )
    assert not filter_results(issue(f"Testsuite Status {BASELINE_HASH}", pull_request=True))


def test_select_baseline_hash_returns_first_valid_issue():
    issues = [
        issue(f"Testsuite Status {BASELINE_HASH}", labels=["build-failure"]),
        issue(f"Testsuite Status {BASELINE_HASH}"),
    ]

    assert select_baseline_hash(issues) == BASELINE_HASH


def test_select_baseline_hash_errors_when_no_valid_issue():
    with pytest.raises(BaselineLookupError, match="No valid post-commit baseline"):
        select_baseline_hash([issue("Coordination Branch Testsuite Status abc")])


def test_fetch_issues_uses_requested_repository_and_paginates(monkeypatch):
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append((url, params))
        if len(calls) == 1:
            return FakeResponse(
                200,
                [issue("ignored")],
                links={"next": {"url": "https://api.github.com/page/2"}},
            )
        return FakeResponse(200, [issue(f"Testsuite Status {BASELINE_HASH}")])

    monkeypatch.setattr("get_baseline_hash.requests.get", fake_get)

    issues = fetch_issues("riseproject-dev/gcc-postcommit-ci", "token")

    assert len(issues) == 2
    assert calls[0][0] == "https://api.github.com/repos/riseproject-dev/gcc-postcommit-ci/issues"
    assert calls[0][1] == {"state": "all", "per_page": 100}
    assert calls[1][0] == "https://api.github.com/page/2"
    assert calls[1][1] is None


def test_fetch_issues_reports_http_errors(monkeypatch):
    def fake_get(url, headers, params, timeout):
        return FakeResponse(403, text="rate limited")

    monkeypatch.setattr("get_baseline_hash.requests.get", fake_get)

    with pytest.raises(BaselineLookupError, match="HTTP 403"):
        fetch_issues("riseproject-dev/gcc-postcommit-ci", "token")


def test_parse_baseline_hash_writes_selected_hash(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "get_baseline_hash.fetch_issues",
        lambda repo, token: [issue(f"Testsuite Status {BASELINE_HASH}")],
    )
    output = tmp_path / "baseline.txt"

    assert (
        parse_baseline_hash("riseproject-dev/gcc-postcommit-ci", "token", str(output))
        == BASELINE_HASH
    )
    assert output.read_text() == BASELINE_HASH
