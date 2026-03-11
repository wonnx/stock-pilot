"""Generate a short-form video from live market data and upload to Instagram Reels."""
import sys
import logging
import tempfile
from pathlib import Path

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

import httpx

def translate_to_korean(text: str) -> str:
    """Translate English text to Korean using Google Translate."""
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='en', target='ko').translate(text)
    except Exception:
        return text  # Fallback: return original English text

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

    # Korean company name lookup
    COMPANY_NAMES_KO = {
        "AAPL": "애플", "MSFT": "마이크로소프트", "GOOGL": "구글", "GOOG": "구글",
        "AMZN": "아마존", "META": "메타", "TSLA": "테슬라", "NVDA": "엔비디아",
        "NFLX": "넷플릭스", "AMD": "AMD", "INTC": "인텔", "CRM": "세일즈포스",
        "ORCL": "오라클", "ADBE": "어도비", "CSCO": "시스코", "QCOM": "퀄컴",
        "AVGO": "브로드컴", "TXN": "텍사스인스트루먼트", "BNTX": "바이오엔텍",
        "MRNA": "모더나", "PFE": "화이자", "JNJ": "존슨앤존슨", "UNH": "유나이티드헬스",
        "V": "비자", "MA": "마스터카드", "JPM": "JP모건", "BAC": "뱅크오브아메리카",
        "GS": "골드만삭스", "WMT": "월마트", "COST": "코스트코", "HD": "홈디포",
        "DIS": "디즈니", "PYPL": "페이팔", "SQ": "블록", "COIN": "코인베이스",
        "PLTR": "팔란티어", "UBER": "우버", "ABNB": "에어비앤비", "SNAP": "스냅",
        "SHOP": "쇼피파이", "ROKU": "로쿠", "ZM": "줌", "DDOG": "데이터독",
        "SNOW": "스노우플레이크", "NET": "클라우드플레어", "CRWD": "크라우드스트라이크",
        "MU": "마이크론", "MRVL": "마벨", "SMCI": "슈퍼마이크로",
        "ARM": "ARM홀딩스", "MSTR": "마이크로스트래티지", "SOFI": "소파이",
        "NIO": "니오", "RIVN": "리비안", "LCID": "루시드", "LI": "리오토",
        "BA": "보잉", "CAT": "캐터필러", "XOM": "엑슨모빌", "CVX": "셰브론",
    }
    company_name_ko = COMPANY_NAMES_KO.get(symbol, "")

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

    # 3. News collection (yfinance + fallback to NewsCollector)
    logger.info("Collecting news...")
    import re
    import yfinance as yf
    news_headlines = []  # For video display (title + detail)
    news_items = []      # For backward compat

    try:
        ticker_obj = yf.Ticker(symbol)
        yf_news = ticker_obj.news or []
        for n in yf_news[:8]:
            content = n.get("content", {})
            title = content.get("title", "")
            desc_html = content.get("description", "")
            desc = re.sub(r"<[^>]+>", "", desc_html).strip()
            # Only keep articles that mention this symbol or company name
            full_text = f"{title} {desc}".lower()
            if symbol.lower() in full_text or (company_name_ko and company_name_ko.lower() in full_text):
                # Build detailed headline
                if desc and len(desc) > 30:
                    news_headlines.append(f"{title}\n{desc[:200]}")
                else:
                    news_headlines.append(title)
        logger.info("yfinance news: %d relevant articles", len(news_headlines))
    except Exception as e:
        logger.warning("yfinance news fetch failed: %s", e)

    # Fallback to NewsCollector if yfinance had no results
    if not news_headlines:
        try:
            collector = NewsCollector(lookback_hours=48)
            news_items = collector.fetch_for_symbol(symbol, max_items=5)
            news_headlines = [f"{n.title}\n{n.summary[:150]}" if n.summary else n.title for n in news_items[:4]]
        except Exception:
            pass

    # Translate news headlines to Korean
    news_headlines_ko = []
    for h in news_headlines:
        parts = h.split("\n")
        title_ko = translate_to_korean(parts[0])
        if len(parts) > 1 and parts[1].strip():
            detail_ko = translate_to_korean(parts[1].strip())
            news_headlines_ko.append(f"{title_ko}\n{detail_ko}")
        else:
            news_headlines_ko.append(title_ko)
    news_headlines = news_headlines_ko
    logger.info("Translated %d headlines to Korean", len(news_headlines))

    # 4. Template-based content generation (no ANTHROPIC_API_KEY needed)
    direction = hot.direction
    sign = "+" if change_pct > 0 else "-"
    arrow = "▲" if change_pct > 0 else "▼"
    rsi_label = "overbought" if rsi >= 70 else ("oversold" if rsi <= 30 else "neutral")
    macd_label = "golden cross" if macd > macd_signal else "death cross"

    rsi_label_ko = "과매수" if rsi >= 70 else ("과매도" if rsi <= 30 else "중립")
    macd_label_ko = "골든크로스" if macd > macd_signal else "데드크로스"
    bb_label_ko = "상단 돌파" if bb_pos == "upper" else ("하단 지지" if bb_pos == "lower" else "중간대")
    ema_label_ko = "상승추세" if ema == "bullish" else ("하락추세" if ema == "bearish" else "혼조")

    display_name = f"{company_name_ko}({symbol})" if company_name_ko else symbol
    card_title = f"{display_name} {arrow}{abs(change_pct):.1f}% {'급등' if change_pct > 0 else '급락'}"
    card_subtitle = f"RSI {rsi_label_ko}({rsi:.0f}) | MACD {macd_label_ko}"
    card_body = (
        f"현재가: ${price:,.2f}\n"
        f"변동: {arrow} {abs(change_pct):.2f}%\n"
        f"거래량: 평균 대비 {vol_ratio:.1f}배"
    )

    tts_name = company_name_ko if company_name_ko else symbol

    # Build TTS script segments — each reads exactly what's shown on screen
    # S1 Hero (0-5s): reads stock name, price, change%
    seg_hero = (
        f"{tts_name}, {symbol}. "
        f"현재가 {price:,.2f}달러. "
        f"{abs(change_pct):.1f}퍼센트 {'급등' if change_pct > 0 else '급락'}."
    )

    # S2 News (5-17s): reads the news headlines shown on screen
    if news_headlines:
        news_parts = []
        for i, h in enumerate(news_headlines[:3]):
            title = h.split("\n")[0]
            detail = h.split("\n")[1] if "\n" in h else ""
            news_parts.append(f"{i+1}번. {title}.")
            if detail:
                news_parts.append(detail[:80])
        seg_news = f"{'급등' if change_pct > 0 else '급락'} 배경. " + " ".join(news_parts)
    else:
        seg_news = f"{'시장 전반의 매수세가 주요 요인으로 분석됩니다.' if change_pct > 0 else '시장 전반의 매도 압력이 주요 원인으로 분석됩니다.'}"

    # S3 Chart (17-26s): reads chart interpretation shown on screen
    if chart_data and len(chart_data) >= 2:
        pct_20d = ((chart_data[-1] / chart_data[0]) - 1) * 100
        trend = "강한 상승추세" if pct_20d > 5 else "완만한 상승" if pct_20d > 0 else "완만한 하락" if pct_20d > -5 else "급격한 하락"
        seg_chart = (
            f"가격 추이, 최근 20거래일. "
            f"20일 전 {chart_data[0]:.2f}달러에서 현재 {chart_data[-1]:.2f}달러. "
            f"{trend}, {abs(pct_20d):.1f}퍼센트 {'상승' if pct_20d > 0 else '하락'}."
        )
    else:
        seg_chart = "최근 20거래일 차트를 분석합니다."

    # S4 Indicators (26-37s): reads indicator values shown on screen
    seg_indicators = (
        f"기술적 분석, 핵심 지표. "
        f"RSI {rsi:.0f}, {rsi_label_ko}. "
        f"MACD {macd_label_ko}. "
        f"볼린저밴드 {bb_label_ko}. "
        f"거래량 {vol_ratio:.1f}배."
    )

    # S5 Conclusion (37-45s): reads the conclusion card
    seg_conclusion = (
        f"오늘의 분석. {card_title}. "
        f"{card_subtitle}. "
        f"스톡스냅 팔로우하고 매일 분석 받으세요."
    )

    script_segments = [seg_hero, seg_news, seg_chart, seg_indicators, seg_conclusion]
    script = " ".join(script_segments)

    news_summary = "\n".join(f"- {h.split(chr(10))[0]}" for h in news_headlines[:3]) if news_headlines else ""
    rsi_outlook = (
        "RSI 과매도 접근 — 반등 가능 구간입니다." if rsi <= 35
        else ("RSI 과매수 영역 — 조정 가능성에 유의하세요." if rsi >= 65
              else "RSI 중립 — 추세 지속 가능성이 높습니다.")
    )

    from datetime import datetime
    import pytz
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(kst)
    time_label = now_kst.strftime("%Y년 %m월 %d일 %H:%M") + " (한국시간) 기준"

    caption = (
        f"${display_name} {arrow}{abs(change_pct):.1f}% "
        f"{'급락' if change_pct < 0 else '급등'}!\n\n"
        f"[분석 기준] {time_label}\n\n"
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
        company_name_ko=company_name_ko,
        news_headlines=news_headlines[:4],
    )

    logger.info("Content generated: %s", card_title)

    # 5. Remotion video rendering
    output_dir = Path("/Users/jwkim/stock-pilot/output")
    output_dir.mkdir(exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = output_dir / f"{symbol}_{ts}_short.mp4"

    # 4b. TTS narration — generate per-scene audio segments for sync
    from stock_pilot.media.tts import generate_tts
    tts_segment_paths = []
    tts_all_ok = True
    for i, seg_text in enumerate(script_segments):
        seg_path = output_dir / f"{symbol}_{ts}_tts_s{i}.mp3"
        ok = generate_tts(seg_text, seg_path)
        if ok:
            tts_segment_paths.append(seg_path)
            logger.info("TTS segment %d: %s", i, seg_path)
        else:
            tts_all_ok = False
            logger.warning("TTS segment %d failed", i)
            break

    # Fallback: single audio file if segments fail
    audio_path = None
    if not tts_all_ok or len(tts_segment_paths) != 5:
        tts_path = output_dir / f"{symbol}_{ts}_tts.mp3"
        if generate_tts(script, tts_path):
            audio_path = tts_path
            tts_segment_paths = []
            logger.info("TTS fallback (single file): %s", tts_path)
        else:
            logger.warning("TTS generation skipped")

    logger.info("Rendering video (45s)...")
    ok = generate_short_video(
        pkg, video_path, audio_path,
        audio_segment_paths=tts_segment_paths if tts_segment_paths else None,
        script_segments=script_segments,
    )
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
