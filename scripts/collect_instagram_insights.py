"""Instagram Insights 수집 + 주간 리포트 생성 스크립트."""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, "src")

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    from stock_pilot.analytics.instagram_insights import InstagramInsights, generate_weekly_report

    insights = InstagramInsights()

    if not insights._token or not insights._user_id:
        logger.error("INSTAGRAM_ACCESS_TOKEN 또는 INSTAGRAM_USER_ID 미설정")
        sys.exit(1)

    logger.info("게시물 Insights 수집 시작 (최근 50개)...")
    media_data = insights.collect_all_media_insights(limit=50)
    logger.info("게시물 %d개 수집 완료", len(media_data))

    logger.info("계정 레벨 Insights 수집 (최근 7일)...")
    account_data = insights.get_account_insights(period="day", days=7)
    logger.info("계정 지표 %d개 수집 완료", len(account_data))

    # 저장
    output_dir = os.getenv("INSIGHTS_OUTPUT_DIR", "output/insights")
    paths = insights.save_insights(media_data, account_data, output_dir=output_dir)
    logger.info("데이터 저장: %s", paths)

    # 주간 리포트
    report_dir = os.getenv("REPORTS_OUTPUT_DIR", "output/reports")
    report_path = generate_weekly_report(media_data, account_data, output_dir=report_dir)
    logger.info("주간 리포트 생성: %s", report_path)

    # 요약 출력
    print(f"\n=== Instagram Insights 수집 완료 ===")
    print(f"게시물 수: {len(media_data)}")
    print(f"JSON: {paths.get('json', '-')}")
    print(f"CSV: {paths.get('csv', '-')}")
    print(f"리포트: {report_path}")


if __name__ == "__main__":
    main()
