"""Lofi ambient BGM generation for stock short videos.

Generates a simple Cmaj7 chord pad using numpy and saves as WAV.
Remotion supports WAV audio natively via staticFile().
"""
from __future__ import annotations
import logging
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _generate_lofi_pad(output_wav: Path, duration_secs: float = 120.0) -> None:
    """Generate a gentle lofi chord pad using numpy and save as WAV."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration_secs)
    t = np.linspace(0, duration_secs, num_samples, endpoint=False)

    # Cmaj7 chord: C3, E3, G3, B3, and sub-bass C2
    freqs = [65.41, 130.81, 164.81, 196.00, 246.94]
    audio = np.zeros(num_samples, dtype=np.float64)

    rng = np.random.default_rng(42)
    for i, freq in enumerate(freqs):
        weight = 0.18 if i == 0 else 0.22  # sub-bass softer
        tone = np.sin(2 * np.pi * freq * t) * weight
        tone += np.sin(2 * np.pi * freq * 2 * t) * 0.04  # 2nd harmonic
        # Gentle vibrato (~0.25Hz, ±0.25%)
        vibrato = 1 + 0.0025 * np.sin(2 * np.pi * 0.25 * t + rng.uniform(0, 2 * np.pi))
        tone *= vibrato
        audio += tone

    # Soft fade-in and fade-out (3 seconds each)
    fade_samples = int(sample_rate * 3.0)
    audio[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples)
    audio[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples)

    # Normalize to ~45% of peak
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.45

    # Convert to 16-bit stereo PCM (duplicate mono to stereo for Remotion compat)
    pcm_mono = (audio * 32767).astype(np.int16)
    pcm_stereo = np.column_stack([pcm_mono, pcm_mono])  # (N, 2)

    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_stereo.tobytes())


def ensure_bgm(bgm_wav_path: Path, duration_secs: float = 120.0) -> bool:
    """Ensure BGM WAV exists at bgm_wav_path. Generates if missing. Returns True on success."""
    if bgm_wav_path.exists():
        return True

    try:
        logger.info("Generating lofi BGM pad (%.0fs)...", duration_secs)
        _generate_lofi_pad(bgm_wav_path, duration_secs)
        logger.info("BGM generated: %s (%.1f MB)", bgm_wav_path, bgm_wav_path.stat().st_size / 1024 ** 2)
        return bgm_wav_path.exists()
    except Exception as e:
        logger.error("BGM generation failed: %s", e)
        return False
