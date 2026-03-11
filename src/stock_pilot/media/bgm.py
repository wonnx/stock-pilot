"""Lofi ambient BGM generation for stock short videos.

Generates a Cmaj7→Am7→Fmaj7→G7 chord progression lofi pad using numpy and saves as WAV.
Remotion supports WAV audio natively via staticFile().
"""
from __future__ import annotations
import logging
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _generate_lofi_progression(output_wav: Path, duration_secs: float = 120.0) -> None:
    """Generate a lofi chord progression pad and save as WAV.

    Uses a Cmaj7 → Am7 → Fmaj7 → G7 loop at 80 BPM.
    Each chord lasts 4 beats (3 seconds). One full loop = 12 seconds.
    """
    sample_rate = 44100
    bpm = 80.0
    beat_secs = 60.0 / bpm          # 0.75 s per beat
    chord_secs = beat_secs * 4      # 3.0 s per chord

    # Chord note frequencies (Hz): root, 3rd, 5th, 7th
    CHORDS = [
        # Cmaj7: C3, E3, G3, B3
        [130.81, 164.81, 196.00, 246.94],
        # Am7: A2, C3, E3, G3
        [110.00, 130.81, 164.81, 196.00],
        # Fmaj7: F2, A2, C3, E3
        [87.31, 110.00, 130.81, 164.81],
        # G7: G2, B2, D3, F3
        [98.00, 123.47, 146.83, 174.61],
    ]

    num_samples = int(sample_rate * duration_secs)
    audio = np.zeros(num_samples, dtype=np.float64)

    rng = np.random.default_rng(42)

    chord_n = int(chord_secs * sample_rate)
    progression_n = chord_n * len(CHORDS)  # 12s per loop

    # Piano ADSR parameters
    attack_n = int(0.015 * sample_rate)   # 15 ms
    decay_n = int(0.08 * sample_rate)     # 80 ms
    sustain_level = 0.55
    release_n = int(0.40 * sample_rate)   # 400 ms

    for loop_start in range(0, num_samples, progression_n):
        for chord_idx, freqs in enumerate(CHORDS):
            block_start = loop_start + chord_idx * chord_n
            if block_start >= num_samples:
                break
            block_end = min(block_start + chord_n, num_samples)
            block_len = block_end - block_start

            t_block = np.linspace(0.0, chord_secs, chord_n, endpoint=False)[:block_len]

            # Build ADSR envelope
            a = min(attack_n, block_len)
            d = min(decay_n, max(0, block_len - a))
            r = min(release_n, max(0, block_len - a - d))
            s = max(0, block_len - a - d - r)

            env = np.concatenate([
                np.linspace(0.0, 1.0, a) if a > 0 else np.array([]),
                np.linspace(1.0, sustain_level, d) if d > 0 else np.array([]),
                np.full(s, sustain_level),
                np.linspace(sustain_level, 0.0, r) if r > 0 else np.array([]),
            ])[:block_len]
            if len(env) < block_len:
                env = np.pad(env, (0, block_len - len(env)))

            chord_audio = np.zeros(block_len)

            # Upper-voice chord tones (piano-like timbre)
            for freq in freqs:
                vib_phase = rng.uniform(0, 2 * np.pi)
                vibrato = 1.0 + 0.002 * np.sin(2 * np.pi * 0.3 * t_block + vib_phase)
                tone = (
                    0.50 * np.sin(2 * np.pi * freq * t_block * vibrato)
                    + 0.22 * np.sin(2 * np.pi * freq * 2 * t_block)
                    + 0.07 * np.sin(2 * np.pi * freq * 3 * t_block)
                )
                chord_audio += tone * env * 0.13

            # Bass note (root, one octave below)
            root_freq = freqs[0] / 2.0
            bass_a = min(int(0.02 * sample_rate), block_len)
            bass_r = min(int(0.60 * sample_rate), max(0, block_len - bass_a))
            bass_s = max(0, block_len - bass_a - bass_r)
            bass_env = np.concatenate([
                np.linspace(0.0, 0.85, bass_a) if bass_a > 0 else np.array([]),
                np.full(bass_s, 0.85),
                np.linspace(0.85, 0.0, bass_r) if bass_r > 0 else np.array([]),
            ])[:block_len]
            if len(bass_env) < block_len:
                bass_env = np.pad(bass_env, (0, block_len - len(bass_env)))

            bass = np.sin(2 * np.pi * root_freq * t_block)
            bass += 0.15 * np.sin(2 * np.pi * root_freq * 2 * t_block)
            chord_audio += bass * bass_env * 0.14

            audio[block_start:block_end] += chord_audio

    # Soft fade-in and fade-out (3 seconds each)
    fade_n = min(int(sample_rate * 3.0), num_samples // 4)
    audio[:fade_n] *= np.linspace(0.0, 1.0, fade_n)
    audio[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)

    # Normalize to ~40% of peak
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.40

    # Convert to 16-bit stereo PCM
    pcm_mono = (audio * 32767).astype(np.int16)
    pcm_stereo = np.column_stack([pcm_mono, pcm_mono])

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
        logger.info("Generating lofi BGM progression (%.0fs)...", duration_secs)
        _generate_lofi_progression(bgm_wav_path, duration_secs)
        logger.info("BGM generated: %s (%.1f MB)", bgm_wav_path, bgm_wav_path.stat().st_size / 1024 ** 2)
        return bgm_wav_path.exists()
    except Exception as e:
        logger.error("BGM generation failed: %s", e)
        return False
