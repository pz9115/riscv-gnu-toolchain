from pathlib import Path
import sys

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

import post_check_to_patchworks


def test_create_data_uses_rise_context_and_issue_url():
    data = post_check_to_patchworks.create_data(
        "Testing passed",
        "123#issuecomment-456",
        None,
        "success",
        "test",
        "riseproject-dev/gcc-precommit-ci",
    )

    assert data == {
        "state": "success",
        "target_url": "https://github.com/riseproject-dev/gcc-precommit-ci/issues/123#issuecomment-456",
        "context": "toolchain-ci-rise-test",
        "description": "Testing passed",
    }


def test_main_skips_patchwork_post_when_reporting_disabled(monkeypatch, capsys):
    def fail_send(*_args, **_kwargs):
        raise AssertionError("Patchwork post should be skipped")

    monkeypatch.delenv("PATCHWORK_REPORTING_ENABLED", raising=False)
    monkeypatch.setattr(post_check_to_patchworks, "send", fail_send)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "post_check_to_patchworks.py",
            "-event",
            "schedule",
            "-repo",
            "riseproject-dev/gcc-precommit-ci",
            "-pid",
            "123",
            "-desc",
            "Testing passed",
            "-iid",
            "1#issuecomment-2",
            "-state",
            "success",
            "-context",
            "test",
            "-token",
            "secret",
        ],
    )

    post_check_to_patchworks.main()

    assert "skipping Patchwork check post" in capsys.readouterr().out
