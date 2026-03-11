"""TTS narration generation using edge-tts (free)."""
from __future__ import annotations
import asyncio, logging
from pathlib import Path

logger = logging.getLogger(__name__)
KOREAN_VOICE = "ko-KR-SunHiNeural"  # Natural Korean female voice


def get_audio_duration(path: Path) -> float:
    """Return duration of an MP3 file in seconds. Returns 0.0 on failure."""
    try:
        from mutagen.mp3 import MP3  # type: ignore[import-untyped]
        return float(MP3(str(path)).info.length)
    except Exception:
        pass
    return 0.0


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
