"""Full content generation pipeline: signals → content → media → upload."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    symbol: str
    content_ok: bool = False
    card_news_ok: bool = False
    video_ok: bool = False
    tts_ok: bool = False
    instagram_ok: bool = False
    youtube_ok: bool = False
    errors: list[str] = field(default_factory=list)


class ContentPipeline:
    """Orchestrate the full content generation and upload pipeline."""

    def __init__(self, output_dir: str = "output") -> None:
        self._out = Path(output_dir)
        self._out.mkdir(parents=True, exist_ok=True)

    def run_for_symbol(
        self,
        symbol: str,
        upload: bool = False,
    ) -> PipelineResult:
        """Run full pipeline for one symbol."""
        result = PipelineResult(symbol=symbol)

        # Imports inside to avoid circular deps
        from stock_pilot.data.fetcher import fetcher
        from stock_pilot.news.collector import NewsCollector
        from stock_pilot.news.sentiment import SentimentAnalyzer
        from stock_pilot.content.generator import generator

        # 1. Fetch price
        try:
            quote = fetcher.get_realtime_quote(symbol)
            price = float(quote.get("price", 0))
            prev_close = float(quote.get("prev_close", price))
        except Exception as e:
            result.errors.append(f"Price fetch failed: {e}")
            return result

        # 2. Fetch news
        try:
            collector = NewsCollector(lookback_hours=24)
            news_items = collector.fetch_for_symbol(symbol, max_items=8)
        except Exception:
            news_items = []

        # 3. Sentiment
        sentiment_summary = ""
        try:
            analyzer = SentimentAnalyzer()
            sent = analyzer.analyze(symbol, news_items)
            if sent:
                sentiment_summary = sent.summary
        except Exception:
            pass

        # 4. Generate content
        pkg = generator.generate(symbol, price, prev_close, news_items, sentiment_summary)
        if not pkg:
            result.errors.append("Content generation failed")
            return result
        result.content_ok = True

        # 5. Card news image
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        card_path = self._out / f"{symbol}_{ts}_card.png"
        try:
            from stock_pilot.media.card_news import generate_card_news
            result.card_news_ok = generate_card_news(pkg, card_path)
        except Exception as e:
            result.errors.append(f"Card news: {e}")

        # 6. TTS
        tts_path = self._out / f"{symbol}_{ts}_tts.mp3"
        try:
            from stock_pilot.media.tts import generate_tts
            result.tts_ok = generate_tts(pkg.script, tts_path)
        except Exception as e:
            result.errors.append(f"TTS: {e}")

        # 7. Short video
        video_path = self._out / f"{symbol}_{ts}_short.mp4"
        try:
            from stock_pilot.media.short_video import generate_short_video
            audio = tts_path if result.tts_ok else None
            result.video_ok = generate_short_video(pkg, video_path, audio)
        except Exception as e:
            result.errors.append(f"Video: {e}")

        # 8. Upload (optional)
        if upload:
            if result.card_news_ok:
                # Instagram requires a public URL for image upload
                # For now, log the card path for manual upload
                logger.info("Card news ready for upload: %s", card_path)

            if result.video_ok:
                try:
                    from stock_pilot.upload.youtube import youtube
                    yt_desc = pkg.caption
                    tags = [symbol, "주식", "미국주식", "숏폼", "YouTubeShorts"]
                    vid_id = youtube.upload_short(video_path, pkg.card_title, yt_desc, tags)
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
                "%s: content=%s card=%s video=%s tts=%s",
                sym, r.content_ok, r.card_news_ok, r.video_ok, r.tts_ok
            )
        return results
