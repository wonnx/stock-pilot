"""
Instagram Reels E2E 테스트
핫 주식 선정 → 퀀트 분석 → AI 콘텐츠 생성 → 30초 영상 → Reels 업로드

실행:
    python tests/test_reels_e2e.py [--upload] [--symbol NVDA]

옵션:
    --upload    실제 Instagram Reels 업로드 수행 (기본값: 생성만)
    --symbol    특정 종목 지정 (기본값: 핫 주식 자동 선정)
    --dry-run   파이프라인만 실행, 업로드 안 함 (기본값)
"""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

# stock-pilot src를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

LINE = "=" * 60


def run_e2e(symbol: str | None = None, upload: bool = False) -> bool:
    """전체 E2E 파이프라인 실행. True = 성공."""
    from stock_pilot.content.pipeline import ContentPipeline

    pipeline = ContentPipeline(output_dir="output/e2e_test")

    print(LINE)
    if symbol:
        print(f"E2E 테스트 시작 — 지정 종목: {symbol}")
        print(LINE)
        result = pipeline.run_for_symbol(symbol, upload=upload)
    else:
        print("E2E 테스트 시작 — 핫 주식 자동 선정")
        print(LINE)
        result = pipeline.run_hot_stock(upload=upload)
        if result is None:
            print("\n❌ 핫 주식 선정 실패 — 테스트 중단")
            return False

    # ── 결과 출력 ──────────────────────────────────────────────────────────
    print(f"\n{'결과 요약':^60}")
    print(LINE)
    print(f"  종목              : {result.symbol}")
    print(f"  콘텐츠 생성       : {'✅ 성공' if result.content_ok else '❌ 실패'}")
    print(f"  카드뉴스 이미지   : {'✅ 성공' if result.card_news_ok else '❌ 실패'}")
    print(f"  TTS 나레이션      : {'✅ 성공' if result.tts_ok else '⚠️  실패 (영상은 무음으로 생성)'}")
    print(f"  30초 숏폼 영상    : {'✅ 성공' if result.video_ok else '❌ 실패'}")

    if result.video_path and result.video_path.exists():
        size_mb = result.video_path.stat().st_size / 1024 / 1024
        print(f"  영상 파일         : {result.video_path} ({size_mb:.1f} MB)")

    if upload:
        print(f"  영상 공개 URL     : {result.video_public_url or '없음'}")
        print(f"  Instagram Reels   : {'✅ 업로드 성공' if result.instagram_reel_ok else '❌ 업로드 실패'}")
        print(f"  YouTube Shorts    : {'✅ 업로드 성공' if result.youtube_ok else '⚠️  미설정/실패'}")

    if result.errors:
        print(f"\n  에러 목록:")
        for err in result.errors:
            print(f"    • {err}")

    print(LINE)

    # 성공 기준: 콘텐츠 생성 + 영상 생성 (업로드는 선택적)
    core_ok = result.content_ok and result.video_ok
    upload_ok = (result.instagram_reel_ok if upload else True)

    if core_ok and upload_ok:
        print("\n✅ E2E 테스트 통과")
        return True
    else:
        print("\n❌ E2E 테스트 실패")
        return False


def test_hot_stock_selection() -> bool:
    """핫 주식 선정 단위 테스트."""
    from stock_pilot.hot_stock import select_hot_stock

    print(f"\n[테스트] 핫 주식 자동 선정")
    result = select_hot_stock()
    if result is None:
        print("  ❌ 핫 주식 선정 실패")
        return False

    print(f"  ✅ 선정 종목: {result.symbol}")
    print(f"     등락률: {result.change_pct:+.2f}%")
    print(f"     거래량 비율: {result.volume_ratio:.1f}x")
    print(f"     핫 점수: {result.hot_score:.1f}")
    assert result.symbol, "symbol should not be empty"
    assert result.hot_score >= 0, "hot_score should be non-negative"
    return True


def test_quant_analysis(symbol: str = "AAPL") -> bool:
    """퀀트 분석 단위 테스트."""
    from stock_pilot.data.fetcher import fetcher
    from stock_pilot.analysis.indicators import TechnicalAnalyzer

    print(f"\n[테스트] 퀀트 분석 ({symbol})")
    try:
        df = fetcher.get_ohlcv(symbol, period="3mo", interval="1d")
        if df.empty or len(df) < 50:
            print(f"  ⚠️  데이터 부족 ({len(df)}행)")
            return False

        analyzer = TechnicalAnalyzer()
        tech = analyzer.compute(symbol, df)
        if tech is None:
            print("  ❌ 기술적 분석 실패")
            return False

        print(f"  ✅ RSI(14): {tech.rsi14:.1f} ({tech.rsi_zone})")
        print(f"     MACD: {tech.macd:.3f} / Signal: {tech.macd_signal:.3f}")
        print(f"     BB 위치: {tech.bb_position}")
        print(f"     EMA 추세: {tech.ema_trend}")
        print(f"     거래량 스파이크: {tech.volume_spike}")
        assert tech.rsi14 > 0, "RSI should be positive"
        return True
    except Exception as e:
        print(f"  ❌ 에러: {e}")
        return False


def test_content_generation(symbol: str = "NVDA") -> bool:
    """AI 콘텐츠 생성 단위 테스트."""
    from stock_pilot.content.generator import generator, ContentPackage

    print(f"\n[테스트] AI 콘텐츠 생성 ({symbol})")
    try:
        pkg = generator.generate(
            symbol=symbol,
            price=875.50,
            prev_close=848.00,
            news_items=[],
            sentiment_summary="AI 수요 급증으로 강세",
        )
        if pkg is None:
            print("  ❌ 콘텐츠 생성 실패")
            return False

        print(f"  ✅ 헤드라인: {pkg.card_title}")
        print(f"     서브타이틀: {pkg.card_subtitle}")
        print(f"     스크립트 길이: {len(pkg.script)}자")
        print(f"     퀀트 요약: {pkg.quant_summary[:50] if pkg.quant_summary else '(없음)'}...")
        assert pkg.card_title, "card_title should not be empty"
        assert pkg.script, "script should not be empty"
        return True
    except Exception as e:
        print(f"  ❌ 에러: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram Reels E2E 테스트")
    parser.add_argument("--upload", action="store_true", help="실제 Instagram Reels 업로드")
    parser.add_argument("--symbol", type=str, default=None, help="특정 종목 지정 (기본: 자동 선정)")
    parser.add_argument("--unit-only", action="store_true", help="단위 테스트만 실행")
    args = parser.parse_args()

    print(LINE)
    print("Stock Pilot — Instagram Reels E2E 테스트 스위트")
    print(LINE)

    results: list[tuple[str, bool]] = []

    # 단위 테스트
    results.append(("핫 주식 선정", test_hot_stock_selection()))
    results.append(("퀀트 분석", test_quant_analysis(args.symbol or "AAPL")))
    results.append(("AI 콘텐츠 생성", test_content_generation(args.symbol or "NVDA")))

    if not args.unit_only:
        # 전체 E2E
        print(f"\n{LINE}")
        print("전체 파이프라인 E2E 테스트")
        e2e_ok = run_e2e(symbol=args.symbol, upload=args.upload)
        results.append(("전체 E2E 파이프라인", e2e_ok))

    # 최종 결과
    print(f"\n{'최종 테스트 결과':^60}")
    print(LINE)
    all_passed = True
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name}")
        if not ok:
            all_passed = False
    print(LINE)

    sys.exit(0 if all_passed else 1)
