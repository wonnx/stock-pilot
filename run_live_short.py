"""Generate a short-form video from live market data and upload to Instagram Reels."""
import sys
import logging
import tempfile
from pathlib import Path

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import httpx

def upload_to_catbox(file_path: Path, mime: str = "video/mp4") -> str | None:
    with open(file_path, "rb") as f:
        resp = httpx.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (file_path.name, f, mime)},
            timeout=120,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    return url if url.startswith("https://") else None


def run():
    from stock_pilot.hot_stock import select_hot_stock
    from stock_pilot.data.fetcher import fetcher
    from stock_pilot.analysis.indicators import TechnicalAnalyzer
    from stock_pilot.news.collector import NewsCollector
    from stock_pilot.content.generator import ContentPackage
    from stock_pilot.media.short_video import generate_short_video
    from stock_pilot.upload.instagram import instagram

    # 1. Hot stock selection
    logger.info("Selecting hottest stock...")
    hot = select_hot_stock()
    if not hot:
        logger.error("Hot stock selection failed")
        sys.exit(1)

    symbol = hot.symbol
    logger.info("Selected: %s %+.2f%% (score %.1f)", symbol, hot.change_pct, hot.hot_score)

    # 2. Quant analysis
    logger.info("Running quant analysis...")
    df = fetcher.get_ohlcv(symbol, period="3mo", interval="1d")
    analyzer = TechnicalAnalyzer()
    tech = analyzer.compute(symbol, df)
    chart_data = [round(float(v), 2) for v in df["Close"].iloc[-20:].tolist()]

    price = hot.price
    change_pct = hot.change_pct
    rsi = tech.rsi14
    macd = tech.macd
    macd_signal = tech.macd_signal
    bb_pos = tech.bb_position
    ema = tech.ema_trend
    vol_ratio = hot.volume_ratio

    logger.info("RSI=%.1f, MACD=%.3f, BB=%s, EMA=%s", rsi, macd, bb_pos, ema)

    # 3. News collection
    logger.info("Collecting news...")
    try:
        collector = NewsCollector(lookback_hours=24)
        news_items = collector.fetch_for_symbol(symbol, max_items=5)
        news_text = "\n".join(f"- {n.title}" for n in news_items[:3]) if news_items else ""
    except Exception:
        news_items = []
        news_text = ""

    # 4. Template-based content generation (no ANTHROPIC_API_KEY needed)
    direction = hot.direction
    sign = "+" if change_pct > 0 else "-"
    arrow = "▲" if change_pct > 0 else "▼"
    rsi_label = "overbought" if rsi >= 70 else ("oversold" if rsi <= 30 else "neutral")
    macd_label = "golden cross" if macd > macd_signal else "death cross"

    rsi_label_ko = "과매수" if rsi >= 70 else ("과매도" if rsi <= 30 else "중립")
    macd_label_ko = "골든크로스" if macd > macd_signal else "데드크로스"

    card_title = f"{symbol} {arrow}{abs(change_pct):.1f}% {'급등' if change_pct > 0 else '급락'}"
    card_subtitle = f"RSI {rsi_label_ko}({rsi:.0f}) | MACD {macd_label_ko}"
    card_body = (
        f"현재가: ${price:,.2f}\n"
        f"변동: {arrow} {abs(change_pct):.2f}%\n"
        f"거래량: 평균 대비 {vol_ratio:.1f}배"
    )

    script = (
        f"오늘 {symbol}이 {abs(change_pct):.1f}퍼센트 {'급등' if change_pct > 0 else '급락'}했습니다. "
        f"RSI는 {rsi:.0f}으로 {rsi_label_ko} 구간에 진입했고, "
        f"MACD는 {macd_label_ko}를 보이고 있습니다. "
        f"거래량은 20일 평균 대비 {vol_ratio:.1f}배 급증했습니다. "
        f"{'이번 하락이 매수 기회가 될지, 추가 하락이 이어질지 주목됩니다.' if change_pct < 0 else '이 상승세가 지속될 수 있을지 주목됩니다.'}"
        f" 본 콘텐츠는 투자 조언이 아닙니다."
    )

    news_summary = "\n".join(f"- {n.title}" for n in news_items[:3]) if news_items else ""
    rsi_outlook = (
        "RSI 과매도 접근 — 반등 가능 구간입니다." if rsi <= 35
        else ("RSI 과매수 영역 — 조정 가능성에 유의하세요." if rsi >= 65
              else "RSI 중립 — 추세 지속 가능성이 높습니다.")
    )

    bb_label_ko = "상단 돌파" if bb_pos == "upper" else ("하단 지지" if bb_pos == "lower" else "중간대")
    ema_label_ko = "상승추세" if ema == "bullish" else ("하락추세" if ema == "bearish" else "혼조")

    caption = (
        f"${symbol} {arrow}{abs(change_pct):.1f}% "
        f"{'급락' if change_pct < 0 else '급등'}!\n\n"
        f"[기술적 분석]\n"
        f"- 현재가: ${price:,.2f} ({sign}{abs(change_pct):.2f}%)\n"
        f"- RSI {rsi:.0f} ({rsi_label_ko}) | MACD: {macd_label_ko}\n"
        f"- 거래량: 20일 평균 대비 {vol_ratio:.1f}배 급증\n"
        f"- 볼린저: {bb_label_ko} | EMA 추세: {ema_label_ko}\n\n"
        + (f"[주요 뉴스]\n{news_summary}\n\n" if news_summary else "")
        + f"[단기 전망]\n"
        f"{'하방 압력 지속 여부를 주시하세요.' if change_pct < 0 else '저항선 돌파 여부를 주시하세요.'} "
        f"{rsi_outlook}\n\n"
        f"#{symbol} #주식 #미국주식 #주식투자 #투자 #숏폼\n"
        f"본 콘텐츠는 투자 조언이 아닙니다."
    )

    quant_summary = f"RSI {rsi:.0f}({rsi_label_ko}), MACD {macd_label_ko}, 볼린저 {bb_label_ko}, EMA {ema_label_ko}"

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
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        volume_ratio=vol_ratio,
        bb_position=bb_pos,
        ema_trend=ema,
        quant_summary=quant_summary,
        forecast_detail=(
            f"{'하방 압력이 관찰됩니다.' if change_pct < 0 else '상승 모멘텀이 관찰됩니다.'} "
            f"RSI {rsi:.0f} ({rsi_label_ko}). "
            f"MACD {macd_label_ko}. "
            f"거래량 평균 대비 {vol_ratio:.1f}배. "
            f"{'지지선 확인 후 진입을 검토하세요.' if change_pct < 0 else '저항선 확인 후 추가 매수를 검토하세요.'}"
        ),
        chart_data=chart_data,
    )

    logger.info("Content generated: %s", card_title)

    # 5. Remotion video rendering
    output_dir = Path("/Users/jwkim/stock-pilot/output")
    output_dir.mkdir(exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = output_dir / f"{symbol}_{ts}_short.mp4"

    # 4b. TTS narration
    from stock_pilot.media.tts import generate_tts
    tts_path = output_dir / f"{symbol}_{ts}_tts.mp3"
    tts_ok = generate_tts(script, tts_path)
    audio_path = tts_path if tts_ok else None
    if tts_ok:
        logger.info("TTS generated: %s", tts_path)
    else:
        logger.warning("TTS generation skipped (edge-tts not available or failed)")

    logger.info("Rendering video (30s)...")
    ok = generate_short_video(pkg, video_path, audio_path)
    if not ok or not video_path.exists():
        logger.error("Video rendering failed")
        sys.exit(1)

    logger.info("Video rendered: %s (%.1f MB)", video_path, video_path.stat().st_size / 1024**2)

    # 6. Upload to catbox.moe for public URL
    logger.info("Uploading to temporary host...")
    video_url = upload_to_catbox(video_path, "video/mp4")
    if not video_url:
        logger.error("Temporary hosting failed")
        sys.exit(1)
    logger.info("Public URL: %s", video_url)

    # 7. Instagram Reels upload
    logger.info("Uploading to Instagram Reels...")
    reels_ok = instagram.upload_reel(video_url, caption)

    if reels_ok:
        logger.info("Instagram Reels upload successful!")
        print(f"\nDone!")
        print(f"Stock: {symbol} {arrow}{abs(change_pct):.1f}%")
        print(f"Video: {video_path}")
        print(f"URL: {video_url}")
    else:
        logger.error("Instagram Reels upload failed")
        sys.exit(1)


if __name__ == "__main__":
    run()
