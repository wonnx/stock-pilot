"""Short-form video generation via Remotion."""
from __future__ import annotations
import json, logging, subprocess
from pathlib import Path
from stock_pilot.content.generator import ContentPackage

logger = logging.getLogger(__name__)
REMOTION_DIR = Path(__file__).parent.parent.parent.parent / "remotion"


def generate_short_video(
    pkg: ContentPackage,
    output_path: Path,
    audio_path: Path | None = None,
) -> bool:
    """Render a short-form video via Remotion CLI. Returns True on success."""
    if not REMOTION_DIR.exists():
        logger.error("Remotion project not found at %s", REMOTION_DIR)
        return False

    props = {
        "symbol": pkg.symbol,
        "price": pkg.price,
        "changePct": pkg.change_pct,
        "direction": pkg.direction,
        "cardTitle": pkg.card_title,
        "cardSubtitle": pkg.card_subtitle,
        "script": pkg.script,
        "audioPath": str(audio_path) if audio_path else "",
        # 퀀트 분석 데이터
        "rsi": pkg.rsi,
        "macd": pkg.macd,
        "macdSignal": pkg.macd_signal,
        "volumeRatio": pkg.volume_ratio,
        "bbPosition": pkg.bb_position,
        "emaTrend": pkg.ema_trend,
        "quantSummary": pkg.quant_summary,
        "chartData": pkg.chart_data,
    }

    cmd = [
        "npx", "remotion", "render",
        "StockShort",
        str(output_path),
        "--props", json.dumps(props),
        "--codec", "h264",
        "--crf", "23",
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
