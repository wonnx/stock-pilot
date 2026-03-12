"""콘텐츠 성과 트래킹 — Instagram + YouTube 조회수/좋아요 수집."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime

import httpx

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

IG_API_BASE = "https://graph.facebook.com/v19.0"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"


def fetch_instagram_insights(
    ig_user_id: str,
    access_token: str,
    limit: int = 10,
) -> list[dict]:
    """Instagram 최근 미디어의 조회수/좋아요/댓글 수집."""
    results = []
    try:
        # 최근 미디어 목록
        resp = httpx.get(
            f"{IG_API_BASE}/{ig_user_id}/media",
            params={
                "fields": "id,media_type,timestamp,like_count,comments_count",
                "limit": limit,
                "access_token": access_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        media_items = resp.json().get("data", [])

        for item in media_items:
            media_id = item["id"]
            # Insights (views, reach, plays)
            try:
                ins_resp = httpx.get(
                    f"{IG_API_BASE}/{media_id}/insights",
                    params={
                        "metric": "plays,reach,total_interactions",
                        "access_token": access_token,
                    },
                    timeout=15,
                )
                ins_resp.raise_for_status()
                insights = {d["name"]: d["values"][0]["value"] for d in ins_resp.json().get("data", [])}
            except Exception as e:
                logger.warning("Instagram insights fetch failed for %s: %s", media_id, e)
                insights = {}

            results.append({
                "platform": "instagram",
                "id": media_id,
                "media_type": item.get("media_type"),
                "timestamp": item.get("timestamp"),
                "likes": item.get("like_count", 0),
                "comments": item.get("comments_count", 0),
                "plays": insights.get("plays", 0),
                "reach": insights.get("reach", 0),
                "interactions": insights.get("total_interactions", 0),
            })
    except Exception as e:
        logger.error("Instagram fetch failed: %s", e)
    return results


def fetch_youtube_stats(
    channel_id: str,
    api_key: str,
    max_results: int = 10,
) -> list[dict]:
    """YouTube 최근 업로드 영상의 조회수/좋아요/댓글 수집."""
    results = []
    try:
        # 최근 업로드 목록
        search_resp = httpx.get(
            f"{YT_API_BASE}/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "maxResults": max_results,
                "order": "date",
                "type": "video",
                "key": api_key,
            },
            timeout=15,
        )
        search_resp.raise_for_status()
        items = search_resp.json().get("items", [])
        video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]

        if not video_ids:
            return results

        # 통계 조회
        stats_resp = httpx.get(
            f"{YT_API_BASE}/videos",
            params={
                "part": "statistics,snippet",
                "id": ",".join(video_ids),
                "key": api_key,
            },
            timeout=15,
        )
        stats_resp.raise_for_status()
        for v in stats_resp.json().get("items", []):
            stats = v.get("statistics", {})
            results.append({
                "platform": "youtube",
                "id": v["id"],
                "title": v["snippet"]["title"],
                "published_at": v["snippet"]["publishedAt"],
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
            })
    except Exception as e:
        logger.error("YouTube fetch failed: %s", e)
    return results


def main() -> None:
    ig_token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    ig_user_id = os.getenv("INSTAGRAM_USER_ID", "17841440692210432")
    yt_api_key = os.getenv("YOUTUBE_API_KEY", "")
    yt_channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "")

    all_metrics: list[dict] = []

    if ig_token and ig_user_id:
        logger.info("Fetching Instagram metrics...")
        ig_data = fetch_instagram_insights(ig_user_id, ig_token)
        all_metrics.extend(ig_data)
        logger.info("Instagram: %d items", len(ig_data))
    else:
        logger.warning("Instagram credentials not set — skipping")

    if yt_api_key and yt_channel_id:
        logger.info("Fetching YouTube metrics...")
        yt_data = fetch_youtube_stats(yt_channel_id, yt_api_key)
        all_metrics.extend(yt_data)
        logger.info("YouTube: %d items", len(yt_data))
    else:
        logger.warning("YouTube credentials not set — skipping")

    # 결과 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"output/performance_{ts}.json"
    os.makedirs("output", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, ensure_ascii=False, indent=2)
    logger.info("Saved performance data: %s (%d records)", out_path, len(all_metrics))

    # 요약 출력
    print(f"\n=== 성과 트래킹 요약 ({ts}) ===")
    for item in all_metrics:
        platform = item["platform"]
        if platform == "instagram":
            print(
                f"[IG] {item['id']} | plays={item['plays']} reach={item['reach']} "
                f"likes={item['likes']} comments={item['comments']}"
            )
        elif platform == "youtube":
            print(
                f"[YT] {item['title'][:40]} | views={item['views']} "
                f"likes={item['likes']} comments={item['comments']}"
            )


if __name__ == "__main__":
    main()
