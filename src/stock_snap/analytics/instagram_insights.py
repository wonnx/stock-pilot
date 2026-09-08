"""Instagram Insights API 모듈 — 게시물/계정 성과 자동 수집."""
from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from stock_snap.utils.config import config

logger = logging.getLogger(__name__)

IG_API_BASE = "https://graph.facebook.com/v19.0"

# 게시물 타입별 지원 metrics
MEDIA_METRICS = {
    "IMAGE": ["impressions", "reach", "likes", "comments", "shares", "saved", "total_interactions"],
    "VIDEO": ["impressions", "reach", "likes", "comments", "shares", "saved", "total_interactions", "plays"],
    "REELS": ["plays", "reach", "likes", "comments", "shares", "saved", "total_interactions"],
    "CAROUSEL_ALBUM": ["impressions", "reach", "likes", "comments", "shares", "saved", "total_interactions"],
}

ACCOUNT_METRICS = [
    "follower_count",
    "impressions",
    "reach",
    "profile_views",
]


class InstagramInsights:
    """Instagram Graph API Insights 수집기."""

    def __init__(self, access_token: str | None = None, user_id: str | None = None) -> None:
        self._token = access_token or config.INSTAGRAM_ACCESS_TOKEN
        self._user_id = user_id or config.INSTAGRAM_USER_ID

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params["access_token"] = self._token
        resp = httpx.get(f"{IG_API_BASE}{path}", params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    # ──────────────────────────────────────────────
    # 게시물 목록 조회
    # ──────────────────────────────────────────────

    def get_media_list(self, limit: int = 50) -> list[dict[str, Any]]:
        """최근 게시물 목록 반환 (id, media_type, timestamp, caption, permalink)."""
        data = self._get(
            f"/{self._user_id}/media",
            {
                "fields": "id,media_type,timestamp,like_count,comments_count,caption,permalink",
                "limit": limit,
            },
        )
        return data.get("data", [])  # type: ignore[no-any-return]

    # ──────────────────────────────────────────────
    # 게시물별 Insights 수집
    # ──────────────────────────────────────────────

    def get_media_insights(self, media_id: str, media_type: str) -> dict[str, int]:
        """단일 게시물의 Insights 반환."""
        metrics = MEDIA_METRICS.get(media_type, MEDIA_METRICS["IMAGE"])
        try:
            data = self._get(
                f"/{media_id}/insights",
                {"metric": ",".join(metrics)},
            )
            return {item["name"]: item.get("values", [{}])[0].get("value", 0)
                    for item in data.get("data", [])}
        except httpx.HTTPStatusError as e:
            logger.warning("Insights 조회 실패 media_id=%s: %s", media_id, e)
            return {}

    def collect_all_media_insights(self, limit: int = 50) -> list[dict[str, Any]]:
        """모든 게시물 insights + 기본 메타 통합 반환."""
        media_list = self.get_media_list(limit)
        results: list[dict[str, Any]] = []

        for item in media_list:
            media_id = item["id"]
            media_type = item.get("media_type", "IMAGE")
            insights = self.get_media_insights(media_id, media_type)

            # caption에서 종목 티커 추출 (예: $AAPL, $NVDA)
            caption = item.get("caption", "")
            tickers = _extract_tickers(caption)

            results.append({
                "id": media_id,
                "media_type": media_type,
                "timestamp": item.get("timestamp", ""),
                "permalink": item.get("permalink", ""),
                "caption_preview": caption[:80] if caption else "",
                "tickers": tickers,
                "like_count": item.get("like_count", 0),
                "comments_count": item.get("comments_count", 0),
                **insights,
            })
            logger.debug("수집 완료: %s (%s)", media_id, media_type)

        return results

    # ──────────────────────────────────────────────
    # 계정 레벨 Insights
    # ──────────────────────────────────────────────

    def get_account_insights(self, period: str = "day", days: int = 7) -> list[dict[str, Any]]:
        """계정 레벨 follower_count, reach, impressions 수집.

        period: 'day' | 'week' | 'month'
        """
        results: list[dict[str, Any]] = []
        for metric in ACCOUNT_METRICS:
            try:
                data = self._get(
                    f"/{self._user_id}/insights",
                    {
                        "metric": metric,
                        "period": period,
                        "since": _days_ago_unix(days),
                        "until": _now_unix(),
                    },
                )
                for item in data.get("data", []):
                    for val in item.get("values", []):
                        results.append({
                            "metric": item["name"],
                            "period": period,
                            "end_time": val.get("end_time", ""),
                            "value": val.get("value", 0),
                        })
            except httpx.HTTPStatusError as e:
                logger.warning("계정 insights 조회 실패 metric=%s: %s", metric, e)
        return results

    # ──────────────────────────────────────────────
    # 저장
    # ──────────────────────────────────────────────

    def save_insights(
        self,
        media_insights: list[dict[str, Any]],
        account_insights: list[dict[str, Any]],
        output_dir: str = "output/insights",
    ) -> dict[str, str]:
        """JSON + CSV로 저장. 저장된 파일 경로 딕셔너리 반환."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        paths: dict[str, str] = {}

        # JSON
        json_path = f"{output_dir}/media_insights_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"collected_at": ts, "media": media_insights, "account": account_insights},
                      f, ensure_ascii=False, indent=2)
        paths["json"] = json_path

        # CSV (media) — 모든 행의 키 합집합을 헤더로 사용
        if media_insights:
            csv_path = f"{output_dir}/media_insights_{ts}.csv"
            all_keys: list[str] = list(
                dict.fromkeys(k for row in media_insights for k in row.keys())
            )
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore", restval=0)
                writer.writeheader()
                writer.writerows(media_insights)
            paths["csv"] = csv_path

        logger.info("Insights 저장 완료: %s", paths)
        return paths


# ──────────────────────────────────────────────
# 주간 리포트 생성
# ──────────────────────────────────────────────

def generate_weekly_report(
    media_insights: list[dict[str, Any]],
    account_insights: list[dict[str, Any]],
    output_dir: str = "output/reports",
) -> str:
    """주간 성과 리포트 markdown 파일 생성. 파일 경로 반환."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    report_path = f"{output_dir}/weekly_report_{ts}.md"

    if not media_insights:
        report = "# 주간 Instagram 성과 리포트\n\n데이터 없음\n"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return report_path

    # 성과 지표 계산
    total_posts = len(media_insights)
    total_reach = sum(r.get("reach", 0) for r in media_insights)
    total_plays = sum(r.get("plays", 0) for r in media_insights)
    total_likes = sum(r.get("like_count", 0) for r in media_insights)
    total_comments = sum(r.get("comments_count", 0) for r in media_insights)
    total_interactions = sum(r.get("total_interactions", 0) for r in media_insights)

    avg_reach = total_reach / total_posts if total_posts else 0
    engagement_rate = (total_interactions / total_reach * 100) if total_reach else 0

    # Top 5 / Bottom 5 (reach 기준)
    sorted_by_reach = sorted(media_insights, key=lambda x: x.get("reach", 0), reverse=True)
    top5 = sorted_by_reach[:5]
    bottom5 = sorted_by_reach[-5:]

    # 종목별 평균 reach
    ticker_stats: dict[str, list[int]] = {}
    for r in media_insights:
        for ticker in r.get("tickers", []):
            ticker_stats.setdefault(ticker, []).append(r.get("reach", 0))
    ticker_avg = {t: sum(v) / len(v) for t, v in ticker_stats.items()}
    top_tickers = sorted(ticker_avg.items(), key=lambda x: x[1], reverse=True)[:5]

    # 미디어 타입별 성과
    type_stats: dict[str, dict[str, float]] = {}
    for r in media_insights:
        mtype = r.get("media_type", "UNKNOWN")
        if mtype not in type_stats:
            type_stats[mtype] = {"count": 0, "reach": 0, "plays": 0, "interactions": 0}
        type_stats[mtype]["count"] += 1
        type_stats[mtype]["reach"] += r.get("reach", 0)
        type_stats[mtype]["plays"] += r.get("plays", 0)
        type_stats[mtype]["interactions"] += r.get("total_interactions", 0)

    # 계정 follower 추이
    follower_data = [a for a in account_insights if a["metric"] == "follower_count"]
    follower_latest = follower_data[-1]["value"] if follower_data else "N/A"
    follower_first = follower_data[0]["value"] if len(follower_data) > 1 else None
    follower_change = ""
    if follower_first and follower_latest != "N/A":
        diff = int(follower_latest) - int(follower_first)
        follower_change = f" ({'+' if diff >= 0 else ''}{diff})"

    # ── 리포트 작성 ──
    lines = [
        "# 주간 Instagram 성과 리포트",
        f"생성일: {datetime.now().strftime('%Y-%m-%d')}  |  기간: 최근 수집 데이터 기준",
        "",
        "## 계정 요약",
        f"- 팔로워: **{follower_latest}{follower_change}**",
        f"- 분석 게시물 수: **{total_posts}개**",
        f"- 총 도달 (Reach): **{total_reach:,}**",
        f"- 총 조회수 (Plays): **{total_plays:,}**",
        f"- 총 좋아요: **{total_likes:,}** / 댓글: **{total_comments:,}**",
        f"- 평균 Reach/게시물: **{avg_reach:,.0f}**",
        f"- 평균 참여율 (Engagement Rate): **{engagement_rate:.2f}%**",
        "",
        "## 미디어 타입별 성과",
        "| 타입 | 게시물 수 | 총 Reach | 총 Plays | 총 Interactions |",
        "|------|----------|----------|----------|-----------------|",
    ]
    for mtype, stat in type_stats.items():
        lines.append(
            f"| {mtype} | {int(stat['count'])} | {int(stat['reach']):,} | "
            f"{int(stat['plays']):,} | {int(stat['interactions']):,} |"
        )

    lines += [
        "",
        "## Top 5 게시물 (Reach 기준)",
        "| # | 날짜 | 타입 | 종목 | Reach | Plays | 좋아요 | 링크 |",
        "|---|------|------|------|-------|-------|--------|------|",
    ]
    for i, r in enumerate(top5, 1):
        date_str = r.get("timestamp", "")[:10]
        tickers = ", ".join(r.get("tickers", [])) or "-"
        link = r.get("permalink", "")
        lines.append(
            f"| {i} | {date_str} | {r.get('media_type','')} | {tickers} | "
            f"{r.get('reach',0):,} | {r.get('plays',0):,} | {r.get('like_count',0):,} | "
            f"[보기]({link}) |"
        )

    lines += [
        "",
        "## Bottom 5 게시물 (Reach 기준)",
        "| # | 날짜 | 타입 | 종목 | Reach | Plays | 좋아요 |",
        "|---|------|------|------|-------|-------|--------|",
    ]
    for i, r in enumerate(bottom5, 1):
        date_str = r.get("timestamp", "")[:10]
        tickers = ", ".join(r.get("tickers", [])) or "-"
        lines.append(
            f"| {i} | {date_str} | {r.get('media_type','')} | {tickers} | "
            f"{r.get('reach',0):,} | {r.get('plays',0):,} | {r.get('like_count',0):,} |"
        )

    if top_tickers:
        lines += [
            "",
            "## 종목별 평균 Reach Top 5",
            "| 종목 | 평균 Reach |",
            "|------|-----------|",
        ]
        for ticker, avg in top_tickers:
            lines.append(f"| {ticker} | {avg:,.0f} |")

    lines += [
        "",
        "## 콘텐츠 최적화 제안",
    ]
    suggestions = _generate_suggestions(media_insights, type_stats, top_tickers)
    for s in suggestions:
        lines.append(f"- {s}")

    report = "\n".join(lines) + "\n"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("주간 리포트 생성 완료: %s", report_path)
    return report_path


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _extract_tickers(text: str) -> list[str]:
    """caption에서 $TICKER 형태의 종목코드 추출."""
    import re
    return re.findall(r"\$([A-Z]{1,5})", text)


def _days_ago_unix(days: int) -> int:
    from datetime import timedelta
    dt = datetime.now(tz=UTC) - timedelta(days=days)
    return int(dt.timestamp())


def _now_unix() -> int:
    return int(datetime.now(tz=UTC).timestamp())


def _generate_suggestions(
    media_insights: list[dict[str, Any]],
    type_stats: dict[str, dict[str, float]],
    top_tickers: list[tuple[str, float]],
) -> list[str]:
    """데이터 기반 최적화 제안 생성."""
    suggestions: list[str] = []

    # 최고 성과 미디어 타입 추천
    if type_stats:
        best_type = max(
            type_stats.items(),
            key=lambda x: x[1]["reach"] / x[1]["count"] if x[1]["count"] > 0 else 0,
        )
        suggestions.append(
            f"**{best_type[0]}** 콘텐츠가 평균 Reach {best_type[1]['reach']/best_type[1]['count']:,.0f}으로 "
            f"가장 높은 성과 → 해당 포맷 비중 확대 권장"
        )

    # 톱 종목 추천
    if top_tickers:
        ticker_names = ", ".join(f"${t}" for t, _ in top_tickers[:3])
        suggestions.append(f"높은 참여율 종목: {ticker_names} → 관련 콘텐츠 우선 제작 권장")

    # Reels vs Image 비교
    reels_reach = type_stats.get("REELS", {}).get("reach", 0)
    image_reach = type_stats.get("IMAGE", {}).get("reach", 0)
    if reels_reach and image_reach and reels_reach > image_reach * 1.5:
        suggestions.append("Reels가 이미지 대비 도달률 50%+ 우위 → Reels 위주 전략 유지")
    elif image_reach and reels_reach and image_reach > reels_reach:
        suggestions.append("이미지 카드뉴스가 Reels 대비 높은 도달률 → 카드뉴스 비중 검토")

    # 게시 시간대 분석
    hours: dict[int, list[int]] = {}
    for r in media_insights:
        ts_str = r.get("timestamp", "")
        if ts_str:
            try:
                hour = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).hour
                hours.setdefault(hour, []).append(r.get("reach", 0))
            except ValueError:
                pass
    if hours:
        best_hour = max(hours.items(), key=lambda x: sum(x[1]) / len(x[1]))
        suggestions.append(
            f"최고 Reach 게시 시간대: **{best_hour[0]:02d}:00 UTC** → 해당 시간대 게시 집중 권장"
        )

    if not suggestions:
        suggestions.append("더 많은 데이터 축적 후 최적화 제안 가능 (게시물 10개 이상 권장)")

    return suggestions
