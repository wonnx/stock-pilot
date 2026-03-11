"""Full content generation pipeline: hot stock selection -> quant analysis -> content -> media -> Instagram Reels upload."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


def _upload_to_catbox(file_path: Path, mime: str = "image/png") -> str | None:
    """Upload file to catbox.moe and return a public URL."""
    try:
        with open(file_path, "rb") as f:
            resp = httpx.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (file_path.name, f, mime)},
                timeout=120,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("https://"):
            logger.info("catbox URL: %s", url)
            return url
    except Exception as e:
        logger.warning("catbox.moe failed: %s", e)
    return None


def _upload_to_litterbox(file_path: Path, mime: str = "video/mp4", hours: str = "24h") -> str | None:
    """Upload file to litterbox.catbox.moe temporarily (default 24h)."""
    try:
        with open(file_path, "rb") as f:
            resp = httpx.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": hours},
                files={"fileToUpload": (file_path.name, f, mime)},
                timeout=120,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("https://"):
            logger.info("litterbox URL (%s): %s", hours, url)
            return url
    except Exception as e:
        logger.warning("litterbox failed: %s", e)
    return None


@dataclass
class PipelineResult:
    symbol: str
    content_ok: bool = False
    card_news_ok: bool = False
    video_ok: bool = False
    tts_ok: bool = False
    instagram_reel_ok: bool = False
    youtube_ok: bool = False
    errors: list[str] = field(default_factory=list)
    # Generated file paths
    card_path: Path | None = None
    video_path: Path | None = None
    # Upload URLs
    video_public_url: str | None = None


class ContentPipeline:
    """Orchestrate the full content generation and upload pipeline."""

    def __init__(self, output_dir: str = "output") -> None:
        self._out = Path(output_dir)
        self._out.mkdir(parents=True, exist_ok=True)

    def run_hot_stock(self, upload: bool = False) -> "PipelineResult | None":
        """
        Auto-select the hottest stock and run the full pipeline.

        Returns:
            PipelineResult or None if hot stock selection fails.
        """
        from stock_pilot.hot_stock import select_hot_stock

        hot = select_hot_stock()
        if not hot:
            logger.error("Hot stock selection failed")
            return None

        logger.info("Hot stock: %s (%+.2f%%, vol %.1fx)", hot.symbol, hot.change_pct, hot.volume_ratio)
        return self.run_for_symbol(hot.symbol, upload=upload, hot_volume_ratio=hot.volume_ratio)

    def run_for_symbol(
        self,
        symbol: str,
        upload: bool = False,
        hot_volume_ratio: float | None = None,
    ) -> PipelineResult:
        """Run full pipeline for one symbol."""
        result = PipelineResult(symbol=symbol)

        from stock_pilot.data.fetcher import fetcher
        from stock_pilot.news.collector import NewsCollector
        from stock_pilot.news.sentiment import SentimentAnalyzer
        from stock_pilot.content.generator import generator
        from stock_pilot.analysis.indicators import TechnicalAnalyzer

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Real-time price
        try:
            quote = fetcher.get_realtime_quote(symbol)
            price = float(quote.get("price", 0))
            prev_close = float(quote.get("prev_close", price))
        except Exception as e:
            result.errors.append(f"Price fetch failed: {e}")
            return result

        # 2. Quant analysis + chart data (last 20 days close)
        tech = None
        chart_data: list[float] = []
        try:
            df = fetcher.get_ohlcv(symbol, period="3mo", interval="1d")
            if not df.empty and len(df) >= 20:
                analyzer = TechnicalAnalyzer()
                tech = analyzer.compute(symbol, df)
                chart_data = [round(float(v), 2) for v in df["Close"].iloc[-20:].tolist()]
        except Exception as e:
            result.errors.append(f"Technical analysis: {e}")

        # Apply volume ratio from hot_stock if available
        if hot_volume_ratio is not None and tech is not None:
            tech.volume = tech.volume_sma20 * hot_volume_ratio

        # 3. News collection
        try:
            collector = NewsCollector(lookback_hours=24)
            news_items = collector.fetch_for_symbol(symbol, max_items=8)
        except Exception:
            news_items = []

        # 4. Sentiment analysis
        sentiment_summary = ""
        try:
            sent_analyzer = SentimentAnalyzer()
            sent = sent_analyzer.analyze(symbol, news_items)
            if sent:
                sentiment_summary = sent.summary
        except Exception:
            pass

        # 5. AI content generation (with quant data)
        pkg = generator.generate(
            symbol, price, prev_close,
            news_items, sentiment_summary,
            tech=tech,
            chart_data=chart_data,
        )
        if not pkg:
            result.errors.append("Content generation failed")
            return result
        result.content_ok = True

        # 6. Card news image
        card_path = self._out / f"{symbol}_{ts}_card.png"
        try:
            from stock_pilot.media.card_news import generate_card_news
            result.card_news_ok = generate_card_news(pkg, card_path)
            if result.card_news_ok:
                result.card_path = card_path
        except Exception as e:
            result.errors.append(f"Card news: {e}")

        # 7. TTS
        tts_path = self._out / f"{symbol}_{ts}_tts.mp3"
        try:
            from stock_pilot.media.tts import generate_tts
            result.tts_ok = generate_tts(pkg.script, tts_path)
        except Exception as e:
            result.errors.append(f"TTS: {e}")

        # 8. 30-second short-form video (Remotion)
        video_path = self._out / f"{symbol}_{ts}_reel.mp4"
        try:
            from stock_pilot.media.short_video import generate_short_video
            audio = tts_path if result.tts_ok else None
            result.video_ok = generate_short_video(pkg, video_path, audio)
            if result.video_ok:
                result.video_path = video_path
        except Exception as e:
            result.errors.append(f"Video: {e}")

        # 9. Upload
        if upload:
            # Instagram Reels upload (video first)
            if result.video_ok and result.video_path:
                try:
                    from stock_pilot.upload.instagram import instagram
                    # Try uploading video to catbox.moe for public URL
                    video_url = _upload_to_catbox(result.video_path, mime="video/mp4")
                    if not video_url:
                        # Fallback: litterbox (24h temporary)
                        video_url = _upload_to_litterbox(result.video_path)

                    if video_url:
                        result.video_public_url = video_url
                        result.instagram_reel_ok = instagram.upload_reel(
                            video_url=video_url,
                            caption=pkg.caption,
                        )
                    else:
                        result.errors.append("Instagram Reel: video temporary hosting failed")
                except Exception as e:
                    result.errors.append(f"Instagram Reel: {e}")

            # YouTube Shorts upload
            if result.video_ok and result.video_path:
                try:
                    from stock_pilot.upload.youtube import youtube
                    tags = [symbol, "stocks", "USstocks", "shorts", "YouTubeShorts", "stockmarket"]
                    vid_id = youtube.upload_short(result.video_path, pkg.card_title, pkg.caption, tags)
                    result.youtube_ok = vid_id is not None
                except Exception as e:
                    result.errors.append(f"YouTube: {e}")

        return result

    def run_for_symbols(
        self,
        symbols: list[str],
        upload: bool = False,
    ) -> list[PipelineResult]:
        results = []
        for sym in symbols:
            logger.info("Running pipeline for %s", sym)
            r = self.run_for_symbol(sym, upload=upload)
            results.append(r)
            logger.info(
                "%s: content=%s card=%s video=%s tts=%s reel=%s",
                sym, r.content_ok, r.card_news_ok, r.video_ok, r.tts_ok, r.instagram_reel_ok,
            )
        return results
