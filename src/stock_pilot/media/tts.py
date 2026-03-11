"""TTS narration generation.

Supports multiple backends (in priority order):
1. OpenAI TTS — highest quality, requires OPENAI_API_KEY in env
2. edge-tts (HyunsuMultilingualNeural) — free, no API key, best free option
3. edge-tts (SunHiNeural / InJoonNeural) — fallback voices

TTS comparison results (2026-03-11):
  ko-KR-HyunsuMultilingualNeural  — 가장 자연스럽고 속도감 있음 (추천)
  ko-KR-InJoonNeural              — 안정적인 남성 뉴스 음성
  ko-KR-SunHiNeural               — 여성 음성, 다소 기계적
  gTTS (Google)                   — 가장 기계적, 비추천
"""
from __future__ import annotations
import asyncio
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Default voice — HyunsuMultilingualNeural is newer and more natural than SunHiNeural
KOREAN_VOICE = "ko-KR-HyunsuMultilingualNeural"

# Sentence-ending patterns for Korean
_SENT_END_RE = re.compile(r'(?<=[.!?。])\s+')


def get_audio_duration(path: Path) -> float:
    """Return duration of an MP3 file in seconds. Returns 0.0 on failure."""
    try:
        from mutagen.mp3 import MP3  # type: ignore[import-untyped]
        return float(MP3(str(path)).info.length)
    except Exception:
        pass
    return 0.0


def generate_tts(text: str, output_path: Path, voice: str = KOREAN_VOICE) -> bool:
    """Generate TTS audio file. Returns True on success.

    Uses OpenAI TTS if OPENAI_API_KEY is set, otherwise falls back to edge-tts.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return _generate_openai_tts(text, output_path)
    return _generate_edge_tts(text, output_path, voice)


def generate_tts_with_timing(
    text: str,
    output_path: Path,
    voice: str = KOREAN_VOICE,
) -> tuple[bool, list[tuple[float, float]]]:
    """Generate TTS audio and return per-sentence timing data.

    Uses OpenAI TTS if OPENAI_API_KEY is set (with character-weighted timing),
    otherwise uses edge-tts WordBoundary events for accurate sentence timings.

    Returns:
        (success, sentence_timings) where sentence_timings is a list of
        (start_sec, end_sec) tuples, one per sentence in text.
    """
    if os.environ.get("OPENAI_API_KEY"):
        ok = _generate_openai_tts(text, output_path)
        if ok:
            sentences = [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]
            total_dur = get_audio_duration(output_path)
            timings = _char_weighted_timings(sentences, total_dur)
            return True, timings
        return False, []

    return _generate_edge_tts_with_timing(text, output_path, voice)


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

def _generate_openai_tts(text: str, output_path: Path) -> bool:
    """Generate TTS via OpenAI API (alloy voice, Korean-capable)."""
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
        client = OpenAI()
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",   # nova sounds most natural for Korean news
            input=text,
            response_format="mp3",
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(output_path))
        return output_path.exists() and output_path.stat().st_size > 0
    except ImportError:
        logger.warning("openai package not installed. Run: uv add openai")
        return False
    except Exception as e:
        logger.error("OpenAI TTS generation failed: %s", e)
        return False


def _generate_edge_tts(text: str, output_path: Path, voice: str) -> bool:
    """Generate TTS audio file via edge-tts. Returns True on success."""
    try:
        import edge_tts  # type: ignore[import-untyped]

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        return output_path.exists()
    except ImportError:
        logger.warning("edge-tts not installed. Run: uv add edge-tts")
        return False
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return False


def _generate_edge_tts_with_timing(
    text: str,
    output_path: Path,
    voice: str,
) -> tuple[bool, list[tuple[float, float]]]:
    """Generate TTS audio and return per-sentence timing data using edge-tts WordBoundary events."""
    sentences = [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]

    try:
        import edge_tts  # type: ignore[import-untyped]

        word_boundaries: list[dict] = []
        audio_chunks: list[bytes] = []

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, voice)
            async for event in communicate.stream():
                if event["type"] == "audio":
                    audio_chunks.append(event["data"])
                elif event["type"] == "WordBoundary":
                    word_boundaries.append({
                        "offset": event["offset"],    # 100-ns ticks from audio start
                        "duration": event["duration"],  # 100-ns ticks
                        "text": event["text"],
                    })

        asyncio.run(_run())

        with open(str(output_path), "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        if not output_path.exists() or output_path.stat().st_size == 0:
            return False, []

        timings = _sentence_timings_from_boundaries(sentences, word_boundaries)
        if not timings:
            # Fallback: character-weighted by total audio duration
            total_dur = get_audio_duration(output_path)
            timings = _char_weighted_timings(sentences, total_dur)

        return True, timings

    except ImportError:
        logger.warning("edge-tts not installed. Run: uv add edge-tts")
        return False, []
    except Exception as e:
        logger.error("TTS with timing failed: %s", e)
        return False, []


def _sentence_timings_from_boundaries(
    sentences: list[str],
    word_boundaries: list[dict],
) -> list[tuple[float, float]]:
    """Map edge-tts WordBoundary events to per-sentence (start_sec, end_sec) pairs."""
    if not word_boundaries or not sentences:
        return []

    TICKS = 10_000_000  # 100-ns ticks per second

    # Group word boundaries into sentence buckets.
    # A new sentence starts whenever a word ends a sentence (ends with .!?。).
    groups: list[list[dict]] = []
    current: list[dict] = []
    for wb in word_boundaries:
        current.append(wb)
        if wb.get("text", "").rstrip().endswith(('.', '!', '?', '。')):
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    if not groups:
        return []

    timings: list[tuple[float, float]] = []
    for i in range(len(sentences)):
        if i < len(groups) and groups[i]:
            grp = groups[i]
            start_sec = grp[0]["offset"] / TICKS
            last = grp[-1]
            end_sec = (last["offset"] + last.get("duration", 0)) / TICKS
            timings.append((start_sec, end_sec))
        else:
            # Extend beyond known boundaries
            last_end = timings[-1][1] if timings else 0.0
            timings.append((last_end, last_end + 1.5))

    return timings


def _char_weighted_timings(
    sentences: list[str],
    total_duration: float,
) -> list[tuple[float, float]]:
    """Distribute total_duration proportionally by sentence character count."""
    if not sentences or total_duration <= 0:
        return [(0.0, 0.0)] * len(sentences)

    total_chars = sum(len(s) for s in sentences) or 1
    timings: list[tuple[float, float]] = []
    cursor = 0.0
    for s in sentences:
        dur = total_duration * len(s) / total_chars
        timings.append((cursor, cursor + dur))
        cursor += dur
    return timings
