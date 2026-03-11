"""Generate 10 BGM sample variations for board review.

Each sample is 12–15 seconds, loop-capable, targeting -18 dBFS peak.
Chord progressions, BPM, and timbre vary across all 10 samples.
"""
from __future__ import annotations

import logging
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100
TARGET_AMPLITUDE = 10 ** (-18 / 20)  # -18 dBFS ≈ 0.1259

# ---------------------------------------------------------------------------
# 10 BGM variations
# ---------------------------------------------------------------------------
# Each entry: (name, bpm, beats_per_chord, chords_hz, style)
# chords_hz: list of [root, 3rd, 5th, 7th] in Hz
VARIATIONS = [
    {
        "id": 1,
        "label": "밝은 lofi (Cmaj7 loop)",
        "bpm": 80,
        "beats_per_chord": 4,
        "chords": [
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [110.00, 130.81, 164.81, 196.00],  # Am7
            [87.31,  110.00, 130.81, 164.81],  # Fmaj7
            [98.00,  123.47, 146.83, 174.61],  # G7
        ],
        "attack_ms": 15, "decay_ms": 80, "sustain": 0.55, "release_ms": 400,
        "harmonics": [0.50, 0.22, 0.07],
        "vibrato_depth": 0.002, "vibrato_rate": 0.3,
        "bass_weight": 0.14, "chord_weight": 0.13,
    },
    {
        "id": 2,
        "label": "차분한 시네마틱 (Dm minor)",
        "bpm": 65,
        "beats_per_chord": 4,
        "chords": [
            [146.83, 174.61, 220.00, 261.63],  # Dm7: D3,F3,A3,C4
            [98.00,  123.47, 146.83, 196.00],  # G7: G2,B2,D3,G3
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [87.31,  104.00, 130.81, 164.81],  # Fmaj7(add9)
        ],
        "attack_ms": 25, "decay_ms": 120, "sustain": 0.45, "release_ms": 600,
        "harmonics": [0.55, 0.18, 0.05],
        "vibrato_depth": 0.001, "vibrato_rate": 0.2,
        "bass_weight": 0.12, "chord_weight": 0.11,
    },
    {
        "id": 3,
        "label": "재즈 피아노 (ii-V-I-VI)",
        "bpm": 95,
        "beats_per_chord": 4,
        "chords": [
            [146.83, 174.61, 220.00, 261.63],  # Dm7
            [98.00,  123.47, 146.83, 174.61],  # G7
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [110.00, 138.59, 164.81, 207.65],  # A7
        ],
        "attack_ms": 10, "decay_ms": 60, "sustain": 0.50, "release_ms": 300,
        "harmonics": [0.45, 0.28, 0.12, 0.04],
        "vibrato_depth": 0.003, "vibrato_rate": 4.5,
        "bass_weight": 0.16, "chord_weight": 0.12,
    },
    {
        "id": 4,
        "label": "미니멀 앰비언트 (Fmaj7-Cmaj7)",
        "bpm": 60,
        "beats_per_chord": 8,
        "chords": [
            [87.31,  110.00, 130.81, 164.81],  # Fmaj7
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
        ],
        "attack_ms": 200, "decay_ms": 300, "sustain": 0.70, "release_ms": 800,
        "harmonics": [0.60, 0.15, 0.03],
        "vibrato_depth": 0.0005, "vibrato_rate": 0.1,
        "bass_weight": 0.10, "chord_weight": 0.12,
    },
    {
        "id": 5,
        "label": "업비트 lofi (G장조)",
        "bpm": 90,
        "beats_per_chord": 4,
        "chords": [
            [196.00, 246.94, 293.66, 369.99],  # Gmaj7: G3,B3,D4,F#4
            [164.81, 196.00, 246.94, 293.66],  # Em7: E3,G3,B3,D4
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [146.83, 185.00, 220.00, 277.18],  # D7: D3,F#3,A3,C4
        ],
        "attack_ms": 12, "decay_ms": 70, "sustain": 0.60, "release_ms": 350,
        "harmonics": [0.48, 0.24, 0.09],
        "vibrato_depth": 0.002, "vibrato_rate": 0.4,
        "bass_weight": 0.15, "chord_weight": 0.14,
    },
    {
        "id": 6,
        "label": "감성 시네마틱 (Am 시작)",
        "bpm": 70,
        "beats_per_chord": 4,
        "chords": [
            [110.00, 130.81, 164.81, 196.00],  # Am7
            [87.31,  110.00, 130.81, 164.81],  # Fmaj7
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [98.00,  123.47, 146.83, 174.61],  # G7
        ],
        "attack_ms": 20, "decay_ms": 100, "sustain": 0.50, "release_ms": 500,
        "harmonics": [0.52, 0.20, 0.06],
        "vibrato_depth": 0.0015, "vibrato_rate": 0.25,
        "bass_weight": 0.13, "chord_weight": 0.12,
    },
    {
        "id": 7,
        "label": "따뜻한 재즈 (Eb장조)",
        "bpm": 85,
        "beats_per_chord": 4,
        "chords": [
            [155.56, 195.00, 233.08, 293.66],  # Ebmaj7: Eb3,G3,Bb3,D4
            [123.47, 155.56, 185.00, 233.08],  # Cm7: C3,Eb3,G3,Bb3
            [103.83, 130.81, 155.56, 195.00],  # Abmaj7: Ab2,C3,Eb3,G3
            [116.54, 146.83, 174.61, 220.00],  # Bb7: Bb2,D3,F3,Ab3
        ],
        "attack_ms": 18, "decay_ms": 90, "sustain": 0.52, "release_ms": 420,
        "harmonics": [0.46, 0.25, 0.10, 0.03],
        "vibrato_depth": 0.0025, "vibrato_rate": 4.0,
        "bass_weight": 0.15, "chord_weight": 0.13,
    },
    {
        "id": 8,
        "label": "차가운 앰비언트 (Bm)",
        "bpm": 72,
        "beats_per_chord": 4,
        "chords": [
            [123.47, 146.83, 185.00, 220.00],  # Bm7: B2,D3,F#3,A3
            [98.00,  123.47, 146.83, 196.00],  # Gmaj7
            [146.83, 185.00, 220.00, 277.18],  # Dmaj7: D3,F#3,A3,C#4
            [110.00, 138.59, 164.81, 207.65],  # A7
        ],
        "attack_ms": 30, "decay_ms": 150, "sustain": 0.40, "release_ms": 700,
        "harmonics": [0.55, 0.16, 0.04],
        "vibrato_depth": 0.001, "vibrato_rate": 0.15,
        "bass_weight": 0.11, "chord_weight": 0.11,
    },
    {
        "id": 9,
        "label": "신나는 lofi (빠른 Cmaj)",
        "bpm": 100,
        "beats_per_chord": 4,
        "chords": [
            [130.81, 164.81, 196.00, 246.94],  # Cmaj7
            [87.31,  110.00, 130.81, 164.81],  # F (treated as Fmaj7)
            [110.00, 130.81, 164.81, 196.00],  # Am7
            [98.00,  123.47, 146.83, 174.61],  # G7
        ],
        "attack_ms": 8, "decay_ms": 50, "sustain": 0.65, "release_ms": 280,
        "harmonics": [0.44, 0.26, 0.11, 0.05],
        "vibrato_depth": 0.003, "vibrato_rate": 5.0,
        "bass_weight": 0.17, "chord_weight": 0.14,
    },
    {
        "id": 10,
        "label": "스무스 재즈 (Fmaj 계열)",
        "bpm": 78,
        "beats_per_chord": 4,
        "chords": [
            [87.31,  110.00, 130.81, 164.81],  # Fmaj7
            [146.83, 174.61, 220.00, 261.63],  # Dm7
            [98.00,  123.47, 146.83, 174.61],  # Gm7: G2,Bb2,D3,F3  (approx)
            [130.81, 164.81, 196.00, 233.08],  # C7: C3,E3,G3,Bb3
        ],
        "attack_ms": 14, "decay_ms": 75, "sustain": 0.58, "release_ms": 450,
        "harmonics": [0.50, 0.22, 0.08, 0.03],
        "vibrato_depth": 0.002, "vibrato_rate": 3.8,
        "bass_weight": 0.14, "chord_weight": 0.13,
    },
]


def _make_envelope(block_len: int, attack_n: int, decay_n: int, sustain: float, release_n: int) -> np.ndarray:
    a = min(attack_n, block_len)
    d = min(decay_n, max(0, block_len - a))
    r = min(release_n, max(0, block_len - a - d))
    s = max(0, block_len - a - d - r)
    parts = []
    if a > 0:
        parts.append(np.linspace(0.0, 1.0, a))
    if d > 0:
        parts.append(np.linspace(1.0, sustain, d))
    if s > 0:
        parts.append(np.full(s, sustain))
    if r > 0:
        parts.append(np.linspace(sustain, 0.0, r))
    env = np.concatenate(parts) if parts else np.array([])
    env = env[:block_len]
    if len(env) < block_len:
        env = np.pad(env, (0, block_len - len(env)))
    return env


def _generate_variation(v: dict, output_wav: Path) -> None:
    bpm: float = v["bpm"]
    beats_per_chord: int = v["beats_per_chord"]
    chords = v["chords"]

    beat_secs = 60.0 / bpm
    chord_secs = beat_secs * beats_per_chord
    loop_secs = chord_secs * len(chords)

    # Target 12–15 s: repeat full loops until >= 12s, then cap at 15s
    reps = max(1, int(np.ceil(12.0 / loop_secs)))
    total_secs = min(loop_secs * reps, 15.0)

    num_samples = int(SAMPLE_RATE * total_secs)
    audio = np.zeros(num_samples, dtype=np.float64)

    rng = np.random.default_rng(v["id"] * 17)

    attack_n = int(v["attack_ms"] / 1000 * SAMPLE_RATE)
    decay_n = int(v["decay_ms"] / 1000 * SAMPLE_RATE)
    sustain_level: float = v["sustain"]
    release_n = int(v["release_ms"] / 1000 * SAMPLE_RATE)
    harmonics: list[float] = v["harmonics"]
    vib_depth: float = v["vibrato_depth"]
    vib_rate: float = v["vibrato_rate"]
    bass_w: float = v["bass_weight"]
    chord_w: float = v["chord_weight"]

    chord_n = int(chord_secs * SAMPLE_RATE)
    progression_n = chord_n * len(chords)

    for loop_start in range(0, num_samples, progression_n):
        for chord_idx, freqs in enumerate(chords):
            block_start = loop_start + chord_idx * chord_n
            if block_start >= num_samples:
                break
            block_end = min(block_start + chord_n, num_samples)
            block_len = block_end - block_start

            t = np.linspace(0.0, chord_secs, chord_n, endpoint=False)[:block_len]

            env = _make_envelope(block_len, attack_n, decay_n, sustain_level, release_n)
            chord_audio = np.zeros(block_len)

            for freq in freqs:
                vib_phase = rng.uniform(0, 2 * np.pi)
                vibrato = 1.0 + vib_depth * np.sin(2 * np.pi * vib_rate * t + vib_phase)
                tone = sum(
                    amp * np.sin(2 * np.pi * freq * (h + 1) * t * vibrato)
                    for h, amp in enumerate(harmonics)
                )
                chord_audio += tone * env * chord_w

            # Bass (root, one octave below)
            root_freq = freqs[0] / 2.0
            bass_a = min(int(0.02 * SAMPLE_RATE), block_len)
            bass_r = min(int(0.60 * SAMPLE_RATE), max(0, block_len - bass_a))
            bass_s = max(0, block_len - bass_a - bass_r)
            bass_env_parts = []
            if bass_a > 0:
                bass_env_parts.append(np.linspace(0.0, 0.85, bass_a))
            if bass_s > 0:
                bass_env_parts.append(np.full(bass_s, 0.85))
            if bass_r > 0:
                bass_env_parts.append(np.linspace(0.85, 0.0, bass_r))
            bass_env = np.concatenate(bass_env_parts) if bass_env_parts else np.array([])
            bass_env = bass_env[:block_len]
            if len(bass_env) < block_len:
                bass_env = np.pad(bass_env, (0, block_len - len(bass_env)))

            bass = np.sin(2 * np.pi * root_freq * t) + 0.15 * np.sin(2 * np.pi * root_freq * 2 * t)
            chord_audio += bass * bass_env * bass_w

            audio[block_start:block_end] += chord_audio

    # Short fade-in / fade-out for clean loop points (1s)
    fade_n = min(int(SAMPLE_RATE * 1.0), num_samples // 4)
    audio[:fade_n] *= np.linspace(0.0, 1.0, fade_n)
    audio[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)

    # Normalize to -18 dBFS
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * TARGET_AMPLITUDE

    pcm_mono = (audio * 32767).astype(np.int16)
    pcm_stereo = np.column_stack([pcm_mono, pcm_mono])

    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_stereo.tobytes())

    logger.info("  [%02d] %s → %s (%.1fs, %.2f MB)",
                v["id"], v["label"], output_wav.name,
                total_secs, output_wav.stat().st_size / 1024 ** 2)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    output_dir = Path("/Users/jwkim/stock-pilot/output/bgm_samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("BGM 샘플 10종 생성 시작 → %s", output_dir)
    for v in VARIATIONS:
        fname = output_dir / f"bgm_sample_{v['id']:02d}.wav"
        _generate_variation(v, fname)
    logger.info("완료: 10개 파일 생성됨")

    # Print summary table
    print("\n=== BGM 샘플 목록 ===")
    for v in VARIATIONS:
        fname = output_dir / f"bgm_sample_{v['id']:02d}.wav"
        beat_secs = 60.0 / v["bpm"]
        chord_secs = beat_secs * v["beats_per_chord"]
        loop_secs = chord_secs * len(v["chords"])
        total = loop_secs if loop_secs >= 12.0 else loop_secs * 2
        print(f"  {fname.name}  {total:.1f}s  BPM={v['bpm']}  {v['label']}")


if __name__ == "__main__":
    main()
