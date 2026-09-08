"""YouTube Analytics API 모듈 — 동영상/채널 성과 자동 수집."""
from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from stock_pilot.upload.youtube import YouTubeUploader

logger = logging.getLogger(__name__)

YT_API_BASE = "https://www.googleapis.com/youtube/v3"
YT_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"


class YouTubeAnalytics:
    """YouTube Data API v3 + Analytics API 성과 수집기."""

    def __init__(self) -> None:
        # Reuse the uploader's token management
        self._uploader = YouTubeUploader()

    def _headers(self) -> dict[str, str]:
        token = self._uploader._get_access_token()
        if not token:
            raise RuntimeError("YouTube OAuth token unavailable")
        return {"Authorization": f"Bearer {token}"}

    # ──────────────────────────────────────────────
    # 채널 ID 조회
    # ──────────────────────────────────────────────

    def get_channel_id(self) -> str | None:
        """인증된 계정의 채널 ID 반환."""
        try:
            resp = httpx.get(
                f"{YT_API_BASE}/channels",
                params={"part": "id,snippet", "mine": "true"},
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if items:
                channel_id = items[0]["id"]
                title = items[0].get("snippet", {}).get("title", "")
                logger.info("YouTube 채널: %s (%s)", title, channel_id)
                return channel_id
        except Exception as e:
            logger.error("채널 ID 조회 실패: %s", e)
        return None

    # ──────────────────────────────────────────────
    # 동영상 목록 조회
    # ──────────────────────────────────────────────

    def get_video_list(self, channel_id: str, max_results: int = 50) -> list[dict[str, Any]]:
        """채널의 최근 동영상 목록 반환 (id, title, publishedAt, description)."""
        try:
            # 채널 업로드 재생목록 ID 가져오기
            ch_resp = httpx.get(
                f"{YT_API_BASE}/channels",
                params={"part": "contentDetails", "id": channel_id},
                headers=self._headers(),
                timeout=15,
            )
            ch_resp.raise_for_status()
            ch_items = ch_resp.json().get("items", [])
            if not ch_items:
                return []
            uploads_playlist = ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # 재생목록 항목 조회
            pl_resp = httpx.get(
                f"{YT_API_BASE}/playlistItems",
                params={
                    "part": "contentDetails,snippet",
                    "playlistId": uploads_playlist,
                    "maxResults": max_results,
                },
                headers=self._headers(),
                timeout=15,
            )
            pl_resp.raise_for_status()
            items = pl_resp.json().get("items", [])
            return [
                {
                    "video_id": item["contentDetails"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "description": item["snippet"].get("description", "")[:200],
                }
                for item in items
            ]
        except Exception as e:
            logger.error("동영상 목록 조회 실패: %s", e)
            return []

    # ──────────────────────────────────────────────
    # 동영상 통계 조회 (조회수, 좋아요, 댓글)
    # ──────────────────────────────────────────────

    def get_video_stats(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """동영상 ID 목록의 통계(조회수, 좋아요, 댓글수) 반환."""
        if not video_ids:
            return []
        results: list[dict[str, Any]] = []
        # API는 한 번에 최대 50개 처리
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            try:
                resp = httpx.get(
                    f"{YT_API_BASE}/videos",
                    params={
                        "part": "statistics,snippet",
                        "id": ",".join(chunk),
                    },
                    headers=self._headers(),
                    timeout=15,
                )
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    stats = item.get("statistics", {})
                    snippet = item.get("snippet", {})
                    results.append({
                        "video_id": item["id"],
                        "title": snippet.get("title", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "url": f"https://youtu.be/{item['id']}",
                    })
            except Exception as e:
                logger.error("동영상 통계 조회 실패 (chunk %d): %s", i, e)
        return results

    # ──────────────────────────────────────────────
    # YouTube Analytics API — 채널 일별 성과
    # ──────────────────────────────────────────────

    def get_channel_analytics(
        self,
        channel_id: str,
        days: int = 7,
        metrics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """채널 일별 Analytics 데이터 반환 (조회수, 추정 시청 시간, 구독자 등).

        YouTube Analytics API가 활성화되어 있어야 합니다.
        metrics 기본값: views, estimatedMinutesWatched, subscribersGained, subscribersLost
        """
        if metrics is None:
            metrics = ["views", "estimatedMinutesWatched", "subscribersGained", "subscribersLost", "likes", "comments"]
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=days)

        try:
            resp = httpx.get(
                f"{YT_ANALYTICS_BASE}/reports",
                params={
                    "ids": f"channel=={channel_id}",
                    "startDate": str(start_dt),
                    "endDate": str(end_dt),
                    "metrics": ",".join(metrics),
                    "dimensions": "day",
                    "sort": "day",
                },
                headers=self._headers(),
                timeout=20,
            )
            resp.raise_for_status()
            body = resp.json()
            col_headers = [h["name"] for h in body.get("columnHeaders", [])]
            rows = body.get("rows", [])
            return [dict(zip(col_headers, row, strict=False)) for row in rows]
        except Exception as e:
            logger.warning("YouTube Analytics API 호출 실패 (Analytics API 미활성화일 수 있음): %s", e)
            return []

    # ──────────────────────────────────────────────
    # 통합 수집 및 저장
    # ──────────────────────────────────────────────

    def collect_all(self, output_dir: str = "output/yt_analytics") -> dict[str, Any]:
        """채널 전체 성과 수집 후 JSON/CSV 저장. 결과 딕셔너리 반환."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        channel_id = self.get_channel_id()
        if not channel_id:
            logger.error("채널 ID 조회 실패 — 수집 중단")
            return {}

        video_list = self.get_video_list(channel_id)
        video_ids = [v["video_id"] for v in video_list]
        video_stats = self.get_video_stats(video_ids)
        channel_analytics = self.get_channel_analytics(channel_id, days=30)

        result: dict[str, Any] = {
            "collected_at": ts,
            "channel_id": channel_id,
            "videos": video_stats,
            "channel_daily": channel_analytics,
        }

        # JSON 저장
        json_path = f"{output_dir}/yt_analytics_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info("YouTube Analytics JSON 저장: %s", json_path)

        # CSV 저장 (동영상 통계)
        if video_stats:
            csv_path = f"{output_dir}/yt_video_stats_{ts}.csv"
            keys = list(video_stats[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(video_stats)
            logger.info("YouTube 동영상 통계 CSV 저장: %s", csv_path)
            result["csv_path"] = csv_path

        result["json_path"] = json_path
        return result

    # ──────────────────────────────────────────────
    # 단일 동영상 조회 (업로드 직후 확인용)
    # ──────────────────────────────────────────────

    def get_video_stat(self, video_id: str) -> dict[str, Any] | None:
        """단일 동영상 통계 반환 (업로드 후 빠른 확인용)."""
        stats = self.get_video_stats([video_id])
        return stats[0] if stats else None
