"""TTS narration generation using edge-tts (free)."""
from __future__ import annotations
import asyncio, logging
from pathlib import Path

logger = logging.getLogger(__name__)
KOREAN_VOICE = "ko-KR-SunHiNeural"  # Natural Korean female voice


def generate_tts(text: str, output_path: Path, voice: str = KOREAN_VOICE) -> bool:
    """Generate TTS audio file via edge-tts. Returns True on success."""
    try:
        import edge_tts  # type: ignore[import-untyped]

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        return output_path.exists()
    except ImportError:
        logger.warning("edge-tts not installed. Run: pip install edge-tts")
        return False
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return False
