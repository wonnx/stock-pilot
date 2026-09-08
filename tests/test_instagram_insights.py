"""Instagram Insights 모듈 단위 테스트."""
from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from stock_snap.analytics.instagram_insights import (
    InstagramInsights,
    _extract_tickers,
    _generate_suggestions,
    generate_weekly_report,
)

# ── 픽스처 ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_media_list():
    return [
        {
            "id": "media_001",
            "media_type": "IMAGE",
            "timestamp": "2026-03-10T09:00:00+0000",
            "like_count": 42,
            "comments_count": 5,
            "caption": "오늘의 핫 종목 $NVDA 실적 발표 후 급등! #주식 #미국주식",
            "permalink": "https://www.instagram.com/p/test001/",
        },
        {
            "id": "media_002",
            "media_type": "REELS",
            "timestamp": "2026-03-11T14:00:00+0000",
            "like_count": 88,
            "comments_count": 12,
            "caption": "$AAPL $TSLA 기술주 동향 분석 #테크주",
            "permalink": "https://www.instagram.com/p/test002/",
        },
        {
            "id": "media_003",
            "media_type": "IMAGE",
            "timestamp": "2026-03-12T08:30:00+0000",
            "like_count": 15,
            "comments_count": 2,
            "caption": "$MSFT 클라우드 성장 지속 #마이크로소프트",
            "permalink": "https://www.instagram.com/p/test003/",
        },
    ]


@pytest.fixture
def mock_media_insights_data():
    return {
        "media_001": {"reach": 1200, "impressions": 1800, "total_interactions": 47, "likes": 42, "comments": 5, "shares": 0, "saved": 0},
        "media_002": {"reach": 3500, "impressions": 5000, "total_interactions": 110, "plays": 4200, "likes": 88, "comments": 12, "shares": 8, "saved": 2},
        "media_003": {"reach": 600, "impressions": 900, "total_interactions": 17, "likes": 15, "comments": 2, "shares": 0, "saved": 0},
    }


@pytest.fixture
def sample_account_insights():
    return [
        {"metric": "follower_count", "period": "day", "end_time": "2026-03-07T08:00:00+0000", "value": 480},
        {"metric": "follower_count", "period": "day", "end_time": "2026-03-08T08:00:00+0000", "value": 485},
        {"metric": "follower_count", "period": "day", "end_time": "2026-03-12T08:00:00+0000", "value": 510},
        {"metric": "reach", "period": "day", "end_time": "2026-03-12T08:00:00+0000", "value": 2800},
        {"metric": "impressions", "period": "day", "end_time": "2026-03-12T08:00:00+0000", "value": 4200},
    ]


# ── 헬퍼 함수 테스트 ────────────────────────────────────────────────────


def test_extract_tickers_basic():
    assert _extract_tickers("오늘의 $NVDA 분석") == ["NVDA"]


def test_extract_tickers_multiple():
    tickers = _extract_tickers("$AAPL $TSLA $MSFT 기술주 동향")
    assert set(tickers) == {"AAPL", "TSLA", "MSFT"}


def test_extract_tickers_no_match():
    assert _extract_tickers("종목 없는 텍스트 #주식") == []


def test_extract_tickers_lowercase_ignored():
    assert _extract_tickers("$aapl should not match") == []


# ── InstagramInsights 클래스 테스트 ────────────────────────────────────


class TestInstagramInsights:
    def test_init_with_explicit_credentials(self):
        ig = InstagramInsights(access_token="test_token", user_id="12345")
        assert ig._token == "test_token"
        assert ig._user_id == "12345"

    def test_get_media_list(self, mock_media_list):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        with patch.object(ig, "_get", return_value={"data": mock_media_list}):
            result = ig.get_media_list(limit=10)
        assert len(result) == 3
        assert result[0]["id"] == "media_001"

    def test_get_media_insights_image(self):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        mock_response = {
            "data": [
                {"name": "reach", "values": [{"value": 1200}]},
                {"name": "impressions", "values": [{"value": 1800}]},
                {"name": "total_interactions", "values": [{"value": 47}]},
            ]
        }
        with patch.object(ig, "_get", return_value=mock_response):
            result = ig.get_media_insights("media_001", "IMAGE")
        assert result["reach"] == 1200
        assert result["impressions"] == 1800
        assert result["total_interactions"] == 47

    def test_get_media_insights_reels_includes_plays(self):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        mock_response = {
            "data": [
                {"name": "plays", "values": [{"value": 4200}]},
                {"name": "reach", "values": [{"value": 3500}]},
            ]
        }
        with patch.object(ig, "_get", return_value=mock_response):
            result = ig.get_media_insights("media_002", "REELS")
        assert result["plays"] == 4200
        assert result["reach"] == 3500

    def test_get_media_insights_http_error_returns_empty(self):
        import httpx
        ig = InstagramInsights(access_token="tok", user_id="uid")
        with patch.object(ig, "_get", side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=MagicMock(status_code=400))):
            result = ig.get_media_insights("bad_id", "IMAGE")
        assert result == {}

    def test_collect_all_media_insights(self, mock_media_list, mock_media_insights_data):
        ig = InstagramInsights(access_token="tok", user_id="uid")

        def fake_get_insights(media_id, media_type):
            return mock_media_insights_data.get(media_id, {})

        with patch.object(ig, "get_media_list", return_value=mock_media_list), \
             patch.object(ig, "get_media_insights", side_effect=fake_get_insights):
            results = ig.collect_all_media_insights()

        assert len(results) == 3
        # NVDA ticker 추출 확인
        nvda_post = next(r for r in results if r["id"] == "media_001")
        assert "NVDA" in nvda_post["tickers"]
        # AAPL, TSLA ticker 추출 확인
        multi_post = next(r for r in results if r["id"] == "media_002")
        assert "AAPL" in multi_post["tickers"]
        assert "TSLA" in multi_post["tickers"]

    def test_get_account_insights(self, sample_account_insights):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        follower_data = {
            "data": [
                {
                    "name": "follower_count",
                    "values": [
                        {"end_time": "2026-03-07T08:00:00+0000", "value": 480},
                        {"end_time": "2026-03-12T08:00:00+0000", "value": 510},
                    ]
                }
            ]
        }
        with patch.object(ig, "_get", return_value=follower_data):
            results = ig.get_account_insights(period="day", days=7)

        follower_vals = [r for r in results if r["metric"] == "follower_count"]
        assert len(follower_vals) >= 2
        values = [v["value"] for v in follower_vals]
        assert 510 in values

    def test_save_insights_creates_files(self, mock_media_list, mock_media_insights_data, sample_account_insights):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        media_data = []
        for item in mock_media_list:
            ins = mock_media_insights_data.get(item["id"], {})
            media_data.append({
                "id": item["id"],
                "media_type": item["media_type"],
                "timestamp": item["timestamp"],
                "permalink": item["permalink"],
                "caption_preview": item["caption"][:80],
                "tickers": _extract_tickers(item["caption"]),
                "like_count": item["like_count"],
                "comments_count": item["comments_count"],
                **ins,
            })

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ig.save_insights(media_data, sample_account_insights, output_dir=tmpdir)

        assert "json" in paths
        assert "csv" in paths

    def test_save_insights_json_content(self, sample_account_insights):
        ig = InstagramInsights(access_token="tok", user_id="uid")
        media_data = [
            {"id": "m1", "media_type": "IMAGE", "timestamp": "2026-03-12", "reach": 100, "tickers": ["NVDA"]}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ig.save_insights(media_data, sample_account_insights, output_dir=tmpdir)
            with open(paths["json"], encoding="utf-8") as f:
                saved = json.load(f)

        assert len(saved["media"]) == 1
        assert saved["media"][0]["id"] == "m1"
        assert len(saved["account"]) == len(sample_account_insights)


# ── 리포트 생성 테스트 ──────────────────────────────────────────────────


class TestGenerateWeeklyReport:
    def _make_media(self, count: int = 5) -> list[dict]:
        base = [
            {"id": f"m{i}", "media_type": "IMAGE" if i % 2 == 0 else "REELS",
             "timestamp": f"2026-03-{10+i:02d}T09:00:00+0000",
             "permalink": f"https://instagram.com/p/m{i}/",
             "tickers": ["NVDA"] if i < 3 else ["AAPL"],
             "like_count": 10 * i, "comments_count": i,
             "reach": 500 * (i + 1), "impressions": 800 * (i + 1),
             "plays": 600 * (i + 1) if i % 2 == 1 else 0,
             "total_interactions": 12 * (i + 1)}
            for i in range(count)
        ]
        return base

    def test_report_file_created(self, sample_account_insights):
        media = self._make_media(5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report(media, sample_account_insights, output_dir=tmpdir)
        assert path.endswith(".md")

    def test_report_contains_key_sections(self, sample_account_insights):
        media = self._make_media(5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report(media, sample_account_insights, output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                content = f.read()

        assert "계정 요약" in content
        assert "미디어 타입별 성과" in content
        assert "Top 5 게시물" in content
        assert "Bottom 5 게시물" in content
        assert "콘텐츠 최적화 제안" in content

    def test_report_with_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report([], [], output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                content = f.read()
        assert "데이터 없음" in content

    def test_report_ticker_section(self, sample_account_insights):
        media = self._make_media(6)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report(media, sample_account_insights, output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                content = f.read()
        assert "종목별 평균 Reach" in content
        assert "NVDA" in content

    def test_report_engagement_rate_calculated(self, sample_account_insights):
        media = self._make_media(3)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report(media, sample_account_insights, output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                content = f.read()
        assert "참여율" in content

    def test_report_follower_change(self):
        account = [
            {"metric": "follower_count", "period": "day", "end_time": "2026-03-06", "value": 490},
            {"metric": "follower_count", "period": "day", "end_time": "2026-03-12", "value": 520},
        ]
        media = self._make_media(3)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_weekly_report(media, account, output_dir=tmpdir)
            with open(path, encoding="utf-8") as f:
                content = f.read()
        assert "520" in content
        assert "+30" in content


# ── _generate_suggestions 테스트 ──────────────────────────────────────


def test_generate_suggestions_returns_list():
    type_stats = {
        "REELS": {"count": 3, "reach": 9000, "plays": 8000, "interactions": 300},
        "IMAGE": {"count": 2, "reach": 2000, "plays": 0, "interactions": 60},
    }
    top_tickers = [("NVDA", 3000.0), ("AAPL", 1500.0)]
    media = []
    suggestions = _generate_suggestions(media, type_stats, top_tickers)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0


def test_generate_suggestions_reels_dominant():
    type_stats = {
        "REELS": {"count": 5, "reach": 20000, "plays": 18000, "interactions": 600},
        "IMAGE": {"count": 5, "reach": 5000, "plays": 0, "interactions": 150},
    }
    suggestions = _generate_suggestions([], type_stats, [])
    combined = " ".join(suggestions)
    # Reels 또는 최고 성과 타입에 대한 언급 확인
    assert "REELS" in combined or "확대" in combined
