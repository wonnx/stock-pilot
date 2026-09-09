"""애프터마켓 리캡 숏폼 영상 생성 — 장 마감 후 주요 종목 등락 정리 (30초)."""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL",
    "AMD", "INTC", "QCOM", "AVGO", "CRM", "SNOW", "PLTR",
    "SOFI", "COIN", "MRNA", "NFLX", "UBER", "SMCI", "MSTR", "ARM",
]

COMPANY_NAMES_KO = {
    "AAPL": "애플", "MSFT": "마이크로소프트", "GOOGL": "구글", "GOOG": "구글",
    "AMZN": "아마존", "META": "메타", "TSLA": "테슬라", "NVDA": "엔비디아",
    "NFLX": "넷플릭스", "AMD": "AMD", "INTC": "인텔", "CRM": "세일즈포스",
    "ORCL": "오라클", "ADBE": "어도비", "CSCO": "시스코", "QCOM": "퀄컴",
    "AVGO": "브로드컴", "TXN": "텍사스인스트루먼트", "BNTX": "바이오엔텍",
    "MRNA": "모더나", "PFE": "화이자", "JNJ": "존슨앤존슨",
    "V": "비자", "MA": "마스터카드", "JPM": "JP모건", "BAC": "뱅크오브아메리카",
    "DIS": "디즈니", "COIN": "코인베이스", "PLTR": "팔란티어", "UBER": "우버",
    "SNAP": "스냅", "SNOW": "스노우플레이크", "NET": "클라우드플레어",
    "CRWD": "크라우드스트라이크", "MU": "마이크론", "SMCI": "슈퍼마이크로",
    "ARM": "ARM홀딩스", "MSTR": "마이크로스트래티지", "SOFI": "소파이",
    "NIO": "니오", "RIVN": "리비안", "LCID": "루시드",
    "BA": "보잉", "XOM": "엑슨모빌", "CVX": "셰브론",
}


def select_aftermarket_hot_stock():
    """장 마감 후 당일 최고 변동 종목 선정."""
    import yfinance as yf

    def _fetch(sym):
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="1d", interval="1d")
            if hist.empty:
                return None
            row = hist.iloc[-1]
            prev_close = tk.fast_info.previous_close
            if not prev_close or prev_close <= 0:
                return None
            price = float(row["Close"])
            volume = int(row["Volume"])
            change_pct = (price - prev_close) / prev_close * 100
            # Combine price change magnitude with volume activity
            score = abs(change_pct) * 10 + (volume / 1_000_000)
            return {
                "symbol": sym,
                "price": price,
                "prev_close": prev_close,
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "score": score,
            }
        except Exception:
            return None

    logger.info("Fetching aftermarket data for %d symbols...", len(UNIVERSE))
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(filter(None, ex.map(_fetch, UNIVERSE)))

    if not results:
        logger.warning("No aftermarket data available")
        return None

    results.sort(key=lambda x: x["score"], reverse=True)

    logger.info("=== After-Market Top 5 ===")
    for r in results[:5]:
        arrow = "▲" if r["change_pct"] > 0 else "▼"
        logger.info("  %s %s%.2f%%  $%.2f", r["symbol"], arrow, abs(r["change_pct"]), r["price"])

    best = results[0]
    from stock_snap.hot_stock import HotStockResult

    direction = "rising" if best["change_pct"] > 0 else ("falling" if best["change_pct"] < 0 else "flat")
    return HotStockResult(
        symbol=best["symbol"],
        price=best["price"],
        prev_close=best["prev_close"],
        change_pct=best["change_pct"],
        volume=best["volume"],
        avg_volume=best["volume"],
        volume_ratio=1.0,
        hot_score=best["score"],
        direction=direction,
    )


def build_aftermarket_script(symbol: str, price: float, change_pct: float,
                              direction: str, tech, news_items: list) -> list[str]:
    """애프터마켓 리캡용 TTS 스크립트 세그먼트 생성 (3개 세그먼트, 약 30초)."""
    name = COMPANY_NAMES_KO.get(symbol, symbol)
    arrow = "급등" if change_pct > 0 else "급락"
    arrow_sign = "상승" if change_pct > 0 else "하락"
    abs_pct = abs(change_pct)

    # 세그먼트 1: 마감 브리핑 (Hero)
    seg_hero = (
        f"오늘 미국 증시 마감 브리핑입니다. "
        f"{name}이 오늘 {abs_pct:.1f}퍼센트 {arrow}하며 "
        f"주목받았습니다. "
        f"마감가는 {price:,.2f}달러입니다."
    )

    # 세그먼트 2: 원인 분석 (News)
    if news_items:
        top_news = news_items[0]
        title_ko = getattr(top_news, "title_ko", None) or getattr(top_news, "title", "")
        seg_news = (
            f"{name}의 {arrow_sign} 배경을 살펴보면, "
            f"{title_ko} "
            f"이 핵심 요인으로 작용했습니다."
        )
    else:
        seg_news = (
            f"{name}의 {arrow_sign} 배경으로는 "
            f"시장 전반적인 {arrow_sign} 심리와 섹터 모멘텀이 작용했습니다."
        )

    # 세그먼트 3: 내일 관전 포인트 (Conclusion)
    rsi = getattr(tech, "rsi14", 50)
    if change_pct > 0:
        if rsi > 70:
            outlook = "과매수 구간에 진입한 만큼 내일 차익 실현 압력에 주의가 필요합니다."
        else:
            outlook = "추가 상승 여력이 남아 있어 내일도 강세 흐름이 이어질지 주목됩니다."
    else:
        if rsi < 30:
            outlook = "과매도 구간으로 단기 반등 가능성에 주목해 보시기 바랍니다."
        else:
            outlook = "추가 하락 여부를 확인하며 지지선 테스트 여부를 살펴봐야 합니다."

    seg_conclusion = f"내일 관전 포인트입니다. {outlook} 투자에는 항상 신중을 기하시기 바랍니다."

    return [seg_hero, seg_news, seg_conclusion]


def run():
    """애프터마켓 리캡 파이프라인 실행."""
    import datetime

    from stock_snap.analysis.indicators import TechnicalAnalyzer
    from stock_snap.content.generator import ContentPackage
    from stock_snap.data.fetcher import MarketDataFetcher
    from stock_snap.media.short_video import generate_short_video
    from stock_snap.media.tts import generate_tts_with_timing
    from stock_snap.news.collector import NewsCollector
    from stock_snap.upload.instagram import instagram
    from stock_snap.upload.youtube import youtube

    # 1. 핫 종목 선정
    hot = select_aftermarket_hot_stock()
    if not hot:
        logger.error("Aftermarket hot stock selection failed")
        sys.exit(1)

    symbol = hot.symbol
    price = hot.price
    change_pct = hot.change_pct
    direction = hot.direction
    name = COMPANY_NAMES_KO.get(symbol, symbol)

    logger.info("Aftermarket hot stock: %s %+.2f%%", symbol, change_pct)

    # 2. 기술적 분석
    fetcher = MarketDataFetcher()
    df = fetcher.get_ohlcv(symbol, period="3mo", interval="1d")
    analyzer = TechnicalAnalyzer()
    tech = analyzer.compute(symbol, df)
    chart_data = [round(float(v), 2) for v in df["Close"].iloc[-20:].tolist()]

    # 3. 뉴스 수집
    collector = NewsCollector()
    news_items = collector.fetch_for_symbol(symbol, max_items=5)

    # 4. TTS 스크립트 생성
    script_segments = build_aftermarket_script(symbol, price, change_pct, direction, tech, news_items)
    script = " ".join(script_segments)

    # 5. ContentPackage 조립
    arrow_emoji = "▲" if change_pct > 0 else "▼"
    abs_pct = abs(change_pct)
    card_title = f"{symbol} {arrow_emoji}{abs_pct:.1f}% 마감"
    card_subtitle = f"애프터마켓 리캡 — {name}"
    card_body = (
        f"• 마감가: ${price:,.2f}\n"
        f"• 등락률: {arrow_emoji} {abs_pct:.1f}%\n"
        f"• RSI: {tech.rsi14:.0f}"
    )
    hashtags = f"#{symbol} #{name} #미국주식 #주식투자 #마감브리핑"
    caption = f"{card_title} — {card_subtitle}\n\n{hashtags}\n⚠️ 본 콘텐츠는 투자 조언이 아닙니다."

    pkg = ContentPackage(
        symbol=symbol,
        price=price,
        change_pct=change_pct,
        direction=direction,
        script=script,
        card_title=card_title,
        card_subtitle=card_subtitle,
        card_body=card_body,
        caption=caption,
        rsi=tech.rsi14,
        macd=tech.macd,
        macd_signal=tech.macd_signal,
        bb_position=tech.bb_position,
        ema_trend=tech.ema_trend,
        volume_ratio=hot.volume_ratio,
        chart_data=chart_data,
        news_headlines=[getattr(n, "title", "") for n in news_items[:3]],
    )

    # 6. 출력 경로
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / f"aftermarket_{symbol}_{ts}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 7. TTS 생성 (세그먼트별)
    tts_segment_paths = []
    all_timings = []
    for i, seg_text in enumerate(script_segments):
        seg_path = output_dir / f"{symbol}_{ts}_tts_s{i}.mp3"
        ok, timings = generate_tts_with_timing(seg_text, seg_path)
        if ok:
            tts_segment_paths.append(seg_path)
            all_timings.append(timings)
            logger.info("TTS segment %d OK", i)
        else:
            logger.error("TTS segment %d FAILED", i)
            tts_segment_paths.append(None)
            all_timings.append([])

    # 8. 영상 렌더링
    video_path = output_dir / f"{symbol}_{ts}_aftermarket.mp4"
    ok = generate_short_video(
        pkg,
        video_path,
        script_segments=script_segments,
        tts_segment_paths=tts_segment_paths,
        subtitle_timings=all_timings,
    )
    if not ok:
        logger.error("Video rendering failed")
        sys.exit(1)
    logger.info("Video rendered: %s", video_path)

    # 9. 업로드 (공개 URL 확보 → Instagram → YouTube)
    from stock_snap.upload.media_host import publish_media

    def _host(file_path: Path, mime: str = "video/mp4") -> str | None:
        try:
            return publish_media(file_path, mime)
        except Exception as e:
            logger.error("media host upload failed: %s", e)
            return None

    video_url = _host(video_path)
    if not video_url:
        logger.error("media host upload failed — aborting")
        sys.exit(1)

    # 썸네일
    from stock_snap.media.short_video import generate_thumbnail
    thumbnail_path = output_dir / f"{symbol}_{ts}_thumb.jpg"
    cover_url = ""
    if generate_thumbnail(pkg, thumbnail_path):
        cover_url = _host(thumbnail_path, "image/jpeg") or ""

    # Instagram Reels 업로드
    reels_ok = instagram.upload_reel(video_url, caption, cover_url=cover_url)

    # YouTube Shorts 업로드
    yt_title = f"{card_title} | Stock Snap 마감브리핑"
    yt_desc = caption + "\n\n#Shorts #주식 #미국주식 #마감"
    yt_tags = [symbol, "주식", "미국주식", "마감브리핑", "Shorts"]
    yt_video_id = youtube.upload_short(video_path, yt_title, yt_desc, yt_tags)

    if reels_ok or yt_video_id:
        logger.info("Aftermarket recap published successfully!")
    else:
        logger.error("All platform uploads failed")
        sys.exit(1)


if __name__ == "__main__":
    run()
