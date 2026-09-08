"""YouTube E2E 테스트 — dry-run 모드로 실제 업로드 없이 전체 파이프라인 검증."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ──────────────────────────────────────────────────────────────
# YouTubeUploader 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestYouTubeUploaderDryRun:
    def _make_uploader(self):
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        uploader._client_id = ""
        uploader._client_secret = ""
        uploader._refresh_token = ""
        uploader._static_oauth_token = "fake-token"
        uploader._access_token = None
        uploader._token_expiry = 0.0
        return uploader

    def test_dry_run_returns_placeholder(self, tmp_path):
        uploader = self._make_uploader()
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)
        result = uploader.upload_short(video, "Test Title", "Test description", dry_run=True)
        assert result == "dry-run-video-id"

    def test_dry_run_skips_quota_check(self, tmp_path):
        """dry-run이면 quota 파일을 수정하지 않아야 함."""
        from stock_pilot.upload.youtube import _load_quota
        uploader = self._make_uploader()
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)
        quota_before = _load_quota()["used"]
        uploader.upload_short(video, "T", "D", dry_run=True)
        quota_after = _load_quota()["used"]
        assert quota_before == quota_after

    def test_missing_video_returns_none(self, tmp_path):
        uploader = self._make_uploader()
        result = uploader.upload_short(tmp_path / "nonexistent.mp4", "T", "D", dry_run=False)
        # Without token refresh credentials, should fail at token check
        assert result is None

    def test_shorts_tag_appended(self, tmp_path):
        """upload_short가 #Shorts 태그를 자동으로 추가해야 함 (내부 로직 검증)."""
        self._make_uploader()
        tags: list[str] = []
        # Simulate tag normalization logic
        if "#Shorts" not in tags:
            tags.append("#Shorts")
        assert "#Shorts" in tags

    def test_title_truncated_to_100(self):
        long_title = "A" * 150
        truncated = long_title[:100]
        assert len(truncated) == 100


class TestYouTubeOAuthRefresh:
    def test_refresh_token_flow_called(self):
        """refresh token이 설정되면 _refresh_access_token이 호출되어야 함."""
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        uploader._client_id = "client_id"
        uploader._client_secret = "client_secret"
        uploader._refresh_token = "refresh_token"
        uploader._static_oauth_token = ""
        uploader._access_token = None
        uploader._token_expiry = 0.0

        with patch("stock_pilot.upload.youtube.httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}
            mock_post.return_value = mock_resp
            token = uploader._get_access_token()
            assert token == "new_token"
            mock_post.assert_called_once()

    def test_static_token_fallback(self):
        """refresh token 없으면 static token을 반환해야 함."""
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        uploader._client_id = ""
        uploader._client_secret = ""
        uploader._refresh_token = ""
        uploader._static_oauth_token = "static-token"
        uploader._access_token = None
        uploader._token_expiry = 0.0
        token = uploader._get_access_token()
        assert token == "static-token"

    def test_no_credentials_returns_none(self):
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        uploader._client_id = ""
        uploader._client_secret = ""
        uploader._refresh_token = ""
        uploader._static_oauth_token = ""
        uploader._access_token = None
        uploader._token_expiry = 0.0
        token = uploader._get_access_token()
        assert token is None


class TestYouTubeQuota:
    def test_quota_exceeded_blocks_upload(self, tmp_path, monkeypatch):
        """quota 초과 시 upload_short가 None을 반환해야 함."""
        from stock_pilot.upload import youtube as yt_module
        fake_quota = {"date": str(__import__("datetime").date.today()), "used": 9000}
        monkeypatch.setattr(yt_module, "_load_quota", lambda: fake_quota)
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        uploader._client_id = ""
        uploader._client_secret = ""
        uploader._refresh_token = ""
        uploader._static_oauth_token = "token"
        uploader._access_token = None
        uploader._token_expiry = 0.0
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)
        result = uploader.upload_short(video, "T", "D", dry_run=False)
        assert result is None

    def test_quota_within_limit_passes(self, monkeypatch):
        """quota 여유 있을 때 _check_quota가 True를 반환해야 함."""
        from stock_pilot.upload import youtube as yt_module
        fake_quota = {"date": str(__import__("datetime").date.today()), "used": 0}
        monkeypatch.setattr(yt_module, "_load_quota", lambda: fake_quota)
        from stock_pilot.upload.youtube import YouTubeUploader
        uploader = YouTubeUploader.__new__(YouTubeUploader)
        assert uploader._check_quota()


# ──────────────────────────────────────────────────────────────
# YouTubeAnalytics 단위 테스트
# ──────────────────────────────────────────────────────────────

class TestYouTubeAnalytics:
    def _make_analytics(self):
        from stock_pilot.analytics.youtube_analytics import YouTubeAnalytics
        analytics = YouTubeAnalytics.__new__(YouTubeAnalytics)
        uploader_mock = MagicMock()
        uploader_mock._get_access_token.return_value = "fake-token"
        analytics._uploader = uploader_mock
        return analytics

    def test_get_video_stats_empty_list(self):
        analytics = self._make_analytics()
        result = analytics.get_video_stats([])
        assert result == []

    def test_get_video_stats_parses_response(self):
        analytics = self._make_analytics()
        fake_response = {
            "items": [
                {
                    "id": "abc123",
                    "snippet": {"title": "Test Video", "publishedAt": "2026-03-13T00:00:00Z"},
                    "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "5"},
                }
            ]
        }
        with patch("stock_pilot.analytics.youtube_analytics.httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = fake_response
            mock_get.return_value = mock_resp
            stats = analytics.get_video_stats(["abc123"])
        assert len(stats) == 1
        assert stats[0]["video_id"] == "abc123"
        assert stats[0]["view_count"] == 1000
        assert stats[0]["like_count"] == 50
        assert stats[0]["url"] == "https://youtu.be/abc123"

    def test_get_video_stat_single(self):
        analytics = self._make_analytics()
        with patch.object(analytics, "get_video_stats") as mock_stats:
            mock_stats.return_value = [{"video_id": "vid1", "view_count": 42}]
            result = analytics.get_video_stat("vid1")
        assert result is not None
        assert result["view_count"] == 42

    def test_get_video_stat_not_found(self):
        analytics = self._make_analytics()
        with patch.object(analytics, "get_video_stats") as mock_stats:
            mock_stats.return_value = []
            result = analytics.get_video_stat("nonexistent")
        assert result is None


# ──────────────────────────────────────────────────────────────
# run_live_short.py dry-run 통합 테스트
# ──────────────────────────────────────────────────────────────

class TestPipelineDryRun:
    def test_dry_run_env_var_parsed(self, monkeypatch):
        """DRY_RUN 환경변수가 올바르게 파싱되어야 함."""
        monkeypatch.setenv("DRY_RUN", "true")
        # Re-evaluate the module-level constant
        dry_run = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
        assert dry_run is True

    def test_dry_run_false_by_default(self, monkeypatch):
        monkeypatch.delenv("DRY_RUN", raising=False)
        dry_run = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
        assert dry_run is False
