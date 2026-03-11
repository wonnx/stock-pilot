"""Short-form video generation via Remotion."""
from __future__ import annotations
import json, logging, shutil, subprocess
from pathlib import Path
from stock_pilot.content.generator import ContentPackage

logger = logging.getLogger(__name__)
REMOTION_DIR = Path(__file__).parent.parent.parent.parent / "remotion"


def generate_thumbnail(pkg: ContentPackage, output_path: Path) -> bool:
    """Render a still thumbnail image via Remotion CLI. Returns True on success."""
    if not REMOTION_DIR.exists():
        logger.error("Remotion project not found at %s", REMOTION_DIR)
        return False

    props = {
        "symbol": pkg.symbol,
        "price": pkg.price,
        "changePct": pkg.change_pct,
        "cardTitle": pkg.card_title,
        "cardSubtitle": pkg.card_subtitle,
        "rsi": pkg.rsi,
        "macd": pkg.macd,
        "macdSignal": pkg.macd_signal,
        "volumeRatio": pkg.volume_ratio,
        "bbPosition": pkg.bb_position,
        "emaTrend": pkg.ema_trend,
        "chartData": pkg.chart_data,
        "companyNameKo": getattr(pkg, "company_name_ko", ""),
    }

    cmd = [
        "npx", "remotion", "still",
        "StockThumbnail",
        str(output_path),
        "--props", json.dumps(props),
        "--image-format", "jpeg",
        "--jpeg-quality", "92",
        "--scale", "2",
        "--height", "1920",
        "--width", "1080",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("Remotion still render failed: %s", result.stderr[-500:])
            return False
        return output_path.exists()
    except FileNotFoundError:
        logger.error("npx not found — install Node.js")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Remotion still render timed out")
        return False


def generate_short_video(
    pkg: ContentPackage,
    output_path: Path,
    audio_path: Path | None = None,
    audio_segment_paths: list[Path] | None = None,
    script_segments: list[str] | None = None,
    bgm_path: Path | None = None,
    total_frames: int = 1350,
    scene_durations: list[int] | None = None,
    subtitle_timings: list[list[tuple[float, float]]] | None = None,
) -> bool:
    """Render a short-form video via Remotion CLI. Returns True on success."""
    if not REMOTION_DIR.exists():
        logger.error("Remotion project not found at %s", REMOTION_DIR)
        return False

    public_dir = REMOTION_DIR / "public"
    public_dir.mkdir(exist_ok=True)

    # Copy audio segment files to Remotion public dir
    audio_segment_names: list[str] = []
    if audio_segment_paths:
        for seg_path in audio_segment_paths:
            if Path(seg_path).exists():
                dest = public_dir / Path(seg_path).name
                shutil.copy2(seg_path, dest)
                audio_segment_names.append(Path(seg_path).name)
                logger.info("Copied audio segment to remotion/public/%s", dest.name)

    # Fallback: single audio file
    audio_prop = ""
    if not audio_segment_names and audio_path and Path(audio_path).exists():
        dest = public_dir / Path(audio_path).name
        shutil.copy2(audio_path, dest)
        audio_prop = Path(audio_path).name
        logger.info("Copied audio to remotion/public/%s", audio_prop)

    # Copy BGM file to Remotion public dir
    bgm_name = ""
    if bgm_path and Path(bgm_path).exists():
        dest = public_dir / Path(bgm_path).name
        shutil.copy2(bgm_path, dest)
        bgm_name = Path(bgm_path).name
        logger.info("Copied BGM to remotion/public/%s", bgm_name)

    props = {
        "symbol": pkg.symbol,
        "price": pkg.price,
        "changePct": pkg.change_pct,
        "direction": pkg.direction,
        "cardTitle": pkg.card_title,
        "cardSubtitle": pkg.card_subtitle,
        "script": pkg.script,
        "audioPath": audio_prop,
        # Quant analysis data
        "rsi": pkg.rsi,
        "macd": pkg.macd,
        "macdSignal": pkg.macd_signal,
        "volumeRatio": pkg.volume_ratio,
        "bbPosition": pkg.bb_position,
        "emaTrend": pkg.ema_trend,
        "quantSummary": pkg.quant_summary,
        "chartData": pkg.chart_data,
        "companyNameKo": getattr(pkg, "company_name_ko", ""),
        "newsHeadlines": getattr(pkg, "news_headlines", []),
        # Scene-synced audio and subtitles
        "audioSegments": audio_segment_names,
        "scriptSegments": script_segments or [],
        # BGM
        "bgmPath": bgm_name,
        # Dynamic duration
        "totalFrames": total_frames,
        "sceneDurations": scene_durations or [],
        # Subtitle timing data: [segment][sentence][start_sec, end_sec]
        "subtitleTimings": [
            [[s, e] for s, e in seg] for seg in subtitle_timings
        ] if subtitle_timings else [],
    }

    cmd = [
        "npx", "remotion", "render",
        "StockShort",
        str(output_path),
        "--props", json.dumps(props),
        "--codec", "h264",
        "--crf", "10",
        "--scale", "2",
        "--height", "1920",
        "--width", "1080",
        "--image-format", "png",
        "--enforce-audio-track",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("Remotion render failed: %s", result.stderr[-500:])
            return False
        return output_path.exists()
    except FileNotFoundError:
        logger.error("npx not found — install Node.js")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Remotion render timed out")
        return False
