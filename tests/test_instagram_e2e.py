"""Instagram end-to-end test: 카드뉴스 생성 → 임시 호스팅 → 업로드."""
from __future__ import annotations
import logging
import os
import sys
import tempfile
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# stock-pilot src를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def upload_to_temp_host(image_path: Path) -> str | None:
    """임시 호스팅 서비스에 이미지를 업로드하여 공개 URL 반환."""
    # Try catbox.moe (permanent free host)
    try:
        with open(image_path, "rb") as f:
            resp = httpx.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (image_path.name, f, "image/png")},
                timeout=60,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("https://"):
            logger.info("임시 호스팅 URL (catbox): %s", url)
            return url
    except Exception as e:
        logger.warning("catbox.moe 실패: %s", e)

    # Try litterbox.catbox.moe (1h expiry)
    try:
        with open(image_path, "rb") as f:
            resp = httpx.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": (image_path.name, f, "image/png")},
                timeout=60,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("https://"):
            logger.info("임시 호스팅 URL (litterbox): %s", url)
            return url
    except Exception as e:
        logger.error("litterbox 실패: %s", e)

    return None


def test_card_news_generation() -> Path | None:
    """카드뉴스 이미지 생성 테스트."""
    from stock_pilot.content.generator import ContentPackage
    from stock_pilot.media.card_news import generate_card_news

    pkg = ContentPackage(
        symbol="NVDA",
        price=875.50,
        change_pct=3.25,
        direction="상승",
        script="엔비디아가 AI 수요 급증으로 3.25% 상승했습니다.",
        card_title="NVDA +3.25% 급등",
        card_subtitle="AI 칩 수요 급증으로 분기 최고가 경신",
        card_body="• 현재가: $875.50\n• 등락률: ▲ 3.25%\n• AI 데이터센터 수요 지속 증가",
        caption="엔비디아 급등! #NVDA #엔비디아 #미국주식 #AI주식 #주식투자\n⚠️ 본 콘텐츠는 투자 조언이 아닙니다.",
    )

    output_path = Path(tempfile.mktemp(suffix="_card_test.png"))
    logger.info("카드뉴스 생성 중: %s", output_path)

    success = generate_card_news(pkg, output_path)
    if success and output_path.exists():
        size = output_path.stat().st_size
        logger.info("✅ 카드뉴스 생성 성공: %s (%d bytes)", output_path, size)
        return output_path
    else:
        logger.error("❌ 카드뉴스 생성 실패")
        return None


def test_instagram_upload(image_path: Path) -> bool:
    """생성된 이미지를 Instagram에 업로드 테스트."""
    from stock_pilot.upload.instagram import instagram

    # 1. 임시 공개 URL로 호스팅
    logger.info("이미지를 임시 호스팅 서비스에 업로드 중...")
    public_url = upload_to_temp_host(image_path)
    if not public_url:
        logger.error("❌ 임시 호스팅 실패 — Instagram 업로드 불가")
        return False

    # 2. Instagram 업로드
    caption = (
        "📊 NVDA 오늘 +3.25% 급등!\n\n"
        "AI 칩 수요 급증으로 분기 최고가 경신\n\n"
        "#NVDA #엔비디아 #미국주식 #AI주식 #주식투자\n"
        "⚠️ 본 콘텐츠는 투자 조언이 아닙니다."
    )
    logger.info("Instagram 업로드 시도: @stock.snap")
    success = instagram.upload_photo(public_url, caption)
    if success:
        logger.info("✅ Instagram 업로드 성공!")
    else:
        logger.error("❌ Instagram 업로드 실패")
    return success


if __name__ == "__main__":
    print("=" * 60)
    print("Instagram E2E 테스트 시작")
    print("=" * 60)

    # Step 1: 카드뉴스 생성
    print("\n[1/2] 카드뉴스 이미지 생성...")
    card_path = test_card_news_generation()

    if card_path is None:
        print("\n❌ 카드뉴스 생성 실패 — 테스트 중단")
        sys.exit(1)

    # Step 2: Instagram 업로드
    print("\n[2/2] Instagram 업로드 테스트...")
    upload_ok = test_instagram_upload(card_path)

    # Cleanup
    if card_path.exists():
        card_path.unlink()

    print("\n" + "=" * 60)
    print("테스트 결과 요약:")
    print(f"  카드뉴스 생성: {'✅ 성공' if card_path else '❌ 실패'}")
    print(f"  Instagram 업로드: {'✅ 성공' if upload_ok else '❌ 실패'}")
    print("=" * 60)

    sys.exit(0 if upload_ok else 1)
