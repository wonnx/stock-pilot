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

    card_title = f"{symbol} {arrow}{abs(change_pct):.1f}% {'surge' if change_pct > 0 else 'plunge'}"
    card_subtitle = f"RSI {rsi_label}({rsi:.0f}) | MACD {macd_label}"
    card_body = (
        f"Price: ${price:,.2f}\n"
        f"Change: {arrow} {abs(change_pct):.2f}%\n"
        f"Volume: {vol_ratio:.1f}x average"
    )

    script = (
        f"Today {symbol} {'surged' if change_pct > 0 else 'plunged'} {abs(change_pct):.1f} percent. "
        f"RSI is at {rsi:.0f}, entering the {rsi_label} zone, "
        f"and MACD shows a {macd_label}. "
        f"Volume spiked to {vol_ratio:.1f}x the 20-day average. "
        f"{'Will this plunge become a buying opportunity, or is more downside ahead?' if change_pct < 0 else 'Can this rally sustain?'}"
        f" This content is not investment advice."
    )

    caption = (
        f"{'📉' if change_pct < 0 else '📈'} {symbol} {arrow}{abs(change_pct):.1f}% "
        f"{'plunge' if change_pct < 0 else 'surge'}!\n\n"
        f"RSI {rsi:.0f} ({rsi_label}) | MACD {macd_label}\n"
        f"Volume {vol_ratio:.1f}x spike\n\n"
        f"#{symbol} #stocks #USstocks #quant #shorts\n"
        f"This content is not investment advice."
    )

    quant_summary = f"RSI {rsi:.0f}({rsi_label}), MACD {macd_label}, BB {bb_pos}, EMA {ema}"

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
        chart_data=chart_data,
    )

    logger.info("Content generated: %s", card_title)

    # 5. Remotion video rendering
    output_dir = Path("/Users/jwkim/stock-pilot/output")
    output_dir.mkdir(exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = output_dir / f"{symbol}_{ts}_short.mp4"

    logger.info("Rendering video (30s)...")
    ok = generate_short_video(pkg, video_path)
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
