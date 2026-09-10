"""Instagram Reels container polling.

Two production failures came from this one method: a 113s video timed out against a
fixed 120s budget, and an ERROR was logged with no reason because only `status_code`
was requested.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stock_snap.upload import instagram as ig  # noqa: E402


def _uploader():
    u = ig.InstagramUploader.__new__(ig.InstagramUploader)
    u._token = "fake-token"
    u._ig_user_id = "fake-user"
    return u


def _response(status_code: str, status: str = ""):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    body = {"status_code": status_code}
    if status:
        body["status"] = status
    resp.json.return_value = body
    return resp


def test_requests_the_status_detail_field():
    """`status` must be requested; it is the only place the error reason appears."""
    with patch.object(ig.httpx, "get", return_value=_response("FINISHED")) as get:
        assert _uploader()._wait_for_container("c1") is True
    fields = get.call_args.kwargs["params"]["fields"]
    assert "status" in fields.split(","), f"error detail not requested: {fields}"


def test_error_reason_is_logged(caplog):
    detail = "The media you tried to publish is not a valid video file"
    with patch.object(ig.httpx, "get", return_value=_response("ERROR", detail)):
        with caplog.at_level("ERROR"):
            assert _uploader()._wait_for_container("c1") is False
    assert detail in caplog.text, "Instagram's reason was discarded"


def test_timeout_is_configurable_and_generous(monkeypatch):
    """A 45s clip cleared 120s; a 113s one did not. The default has to cover both."""
    assert ig.CONTAINER_TIMEOUT_SECS >= 300

    calls = {"n": 0}

    def _slow(*_a, **_k):
        calls["n"] += 1
        return _response("IN_PROGRESS")

    with (
        patch.object(ig.httpx, "get", side_effect=_slow),
        patch.object(ig.time, "sleep"),
    ):
        assert _uploader()._wait_for_container("c1", timeout=0.1) is False
    assert calls["n"] >= 1


@pytest.mark.parametrize("terminal", ["FINISHED", "ERROR"])
def test_polling_stops_on_terminal_status(terminal):
    with patch.object(ig.httpx, "get", return_value=_response(terminal, "detail")) as get:
        _uploader()._wait_for_container("c1")
    assert get.call_count == 1
