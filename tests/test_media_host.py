"""GitHub Release media hosting tests.

The Instagram Graph API fetches Reels by URL, so these paths decide whether a
scheduled run can publish at all. Everything here is mocked — no network.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stock_pilot.upload import media_host

RELEASE_URL = "https://github.com/wonnx/stock-pilot/releases/download/media/TSLA_short.mp4"


class _Resp:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def _client_with(get=None, post=None, delete=None) -> MagicMock:
    """A context-manager mock standing in for httpx.Client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get = get or MagicMock(return_value=_Resp(404))
    client.post = post or MagicMock(return_value=_Resp(201, {}))
    client.delete = delete or MagicMock(return_value=_Resp(204))
    return client


@pytest.fixture
def video(tmp_path) -> Path:
    f = tmp_path / "TSLA_short.mp4"
    f.write_bytes(b"\x00" * 2048)
    return f


@pytest.fixture
def gh_env():
    env = {"GITHUB_TOKEN": "ghs_test", "GITHUB_REPOSITORY": "wonnx/stock-pilot"}
    with patch.dict(os.environ, env, clear=False):
        yield


class TestAvailability:
    def test_unavailable_without_env(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""}, clear=False):
            assert media_host.is_available() is False

    def test_available_with_env(self, gh_env):
        assert media_host.is_available() is True


class TestUploadToRelease:
    def test_returns_browser_download_url(self, video, gh_env):
        get = MagicMock(
            side_effect=[
                _Resp(200, {"id": 11}),                          # existing release
                _Resp(200, {"state": "uploaded"}),               # _await_ready
                _Resp(200, []),                                  # _prune listing
            ]
        )
        post = MagicMock(return_value=_Resp(201, {"id": 99, "browser_download_url": RELEASE_URL}))
        with patch.object(media_host.httpx, "Client", return_value=_client_with(get, post)):
            url = media_host.upload_to_github_release(video, "video/mp4")
        assert url == RELEASE_URL

    def test_creates_release_when_missing(self, video, gh_env):
        get = MagicMock(
            side_effect=[
                _Resp(404),                                      # no release yet
                _Resp(200, {"state": "uploaded"}),
                _Resp(200, []),
            ]
        )
        post = MagicMock(
            side_effect=[
                _Resp(201, {"id": 11}),                          # release created
                _Resp(201, {"id": 99, "browser_download_url": RELEASE_URL}),
            ]
        )
        with patch.object(media_host.httpx, "Client", return_value=_client_with(get, post)):
            url = media_host.upload_to_github_release(video, "video/mp4")
        assert url == RELEASE_URL
        assert post.call_count == 2

    def test_replaces_asset_on_name_conflict(self, video, gh_env):
        get = MagicMock(
            side_effect=[
                _Resp(200, {"id": 11}),
                _Resp(200, [{"id": 42, "name": "TSLA_short.mp4"}]),   # conflict lookup
                _Resp(200, {"state": "uploaded"}),
                _Resp(200, []),
            ]
        )
        post = MagicMock(
            side_effect=[
                _Resp(422, text="already_exists"),
                _Resp(201, {"id": 99, "browser_download_url": RELEASE_URL}),
            ]
        )
        delete = MagicMock(return_value=_Resp(204))
        with patch.object(media_host.httpx, "Client", return_value=_client_with(get, post, delete)):
            url = media_host.upload_to_github_release(video, "video/mp4")
        assert url == RELEASE_URL
        delete.assert_called_once()

    def test_returns_none_when_upload_rejected(self, video, gh_env):
        get = MagicMock(return_value=_Resp(200, {"id": 11}))
        post = MagicMock(return_value=_Resp(403, text="forbidden"))
        with patch.object(media_host.httpx, "Client", return_value=_client_with(get, post)):
            assert media_host.upload_to_github_release(video, "video/mp4") is None

    def test_returns_none_without_credentials(self, video):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""}, clear=False):
            assert media_host.upload_to_github_release(video, "video/mp4") is None

    def test_returns_none_for_missing_file(self, tmp_path, gh_env):
        assert media_host.upload_to_github_release(tmp_path / "nope.mp4") is None


class TestPublishMedia:
    def test_prefers_release_host(self, video, gh_env):
        with (
            patch.object(media_host, "upload_to_github_release", return_value=RELEASE_URL) as rel,
            patch.object(media_host, "upload_to_catbox") as cat,
        ):
            assert media_host.publish_media(video) == RELEASE_URL
        rel.assert_called_once()
        cat.assert_not_called()

    def test_falls_back_to_catbox_locally(self, video):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""}, clear=False):
            with (
                patch.object(media_host, "upload_to_github_release") as rel,
                patch.object(
                    media_host, "upload_to_catbox", return_value="https://files.catbox.moe/x.mp4"
                ) as cat,
            ):
                assert media_host.publish_media(video) == "https://files.catbox.moe/x.mp4"
            rel.assert_not_called()
            cat.assert_called_once()
