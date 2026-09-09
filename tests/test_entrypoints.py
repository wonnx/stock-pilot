"""Entry point tests for the run_*.py pipelines.

run_aftermarket.py and run_weekly_review.py imported StockDataFetcher, a class that
never existed, from the day they were added. Nothing caught it: the import sits inside
run(), so it survives compilation, and no test imported either module. Both workflows
died on the first scheduled run that got far enough to execute them.

Two layers here. The first resolves every stock_snap symbol each entry point imports,
which catches that class of mistake across all of them for almost no runtime. The
second actually drives the two previously untested pipelines with the slow and
irreversible parts mocked out.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

ENTRY_POINTS = sorted(p.name for p in REPO_ROOT.glob("run_*.py"))


def _stock_snap_imports(path: Path) -> list[tuple[int, str, str]]:
    """Every (lineno, module, name) this file imports from the stock_snap package."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "stock_snap" or node.module.startswith("stock_snap."):
                for alias in node.names:
                    found.append((node.lineno, node.module, alias.name))
    return found


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_entrypoint_imports_resolve(entry_point):
    """Names imported from stock_snap must actually exist.

    These imports live inside run(), so nothing surfaces them until the pipeline is
    executed for real - which, on a schedule, means finding out the next morning.
    """
    path = REPO_ROOT / entry_point
    missing = []
    for lineno, module_name, symbol in _stock_snap_imports(path):
        module = importlib.import_module(module_name)
        if not hasattr(module, symbol):
            missing.append(f"{entry_point}:{lineno} {module_name}.{symbol}")
    assert not missing, "unresolvable imports: " + ", ".join(missing)


# ---------------------------------------------------------------------------
# Mocked pipeline runs
# ---------------------------------------------------------------------------


def _make_ohlcv(rows: int = 120) -> pd.DataFrame:
    """OHLCV with enough history for SMA60 and the 20-day trendline."""
    index = pd.date_range("2026-05-01", periods=rows, freq="B")
    close = np.linspace(100, 130, rows) + np.sin(np.arange(rows) / 3) * 2
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.5,
            "Low": close - 1.5,
            "Close": close,
            "Volume": np.linspace(1_000_000, 3_000_000, rows).astype(int),
        },
        index=index,
    )


def _fake_ticker(*_args, **_kwargs):
    ticker = MagicMock()
    ticker.history.return_value = _make_ohlcv(10)
    ticker.fast_info.previous_close = 120.0
    ticker.news = []
    return ticker


def _fake_tts(_text, out_path, *_args, **_kwargs):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(b"\x00" * 4096)
    return True, [(0.0, 2.0), (2.0, 4.0)]


def _fake_video(_pkg, out_path, *_args, **_kwargs):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(b"\x00" * 2048)
    return True


def _fake_thumbnail(_pkg, out_path, *_args, **_kwargs):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(b"\xff\xd8\xff" + b"\x00" * 2048)
    return True


@pytest.fixture
def mocked_externals():
    """Mock everything that costs money, time, or posts publicly.

    autospec is what makes this worth having. A plain MagicMock accepts any argument
    name, so it happily swallows a call like generate_short_video(..., tts_segment_paths=...)
    against a function whose parameter is audio_segment_paths - which is exactly the
    second bug these pipelines were carrying. autospec validates each call against the
    real signature, so a rename on either side fails here instead of on the runner.
    """
    from stock_snap.upload.instagram import instagram
    from stock_snap.upload.youtube import youtube

    patches = {
        "ohlcv": patch(
            "stock_snap.data.fetcher.MarketDataFetcher.get_ohlcv",
            autospec=True,
            return_value=_make_ohlcv(),
        ),
        "ticker": patch("yfinance.Ticker", side_effect=_fake_ticker),
        "news": patch(
            "stock_snap.news.collector.NewsCollector.fetch_for_symbol",
            autospec=True,
            return_value=[],
        ),
        "tts": patch(
            "stock_snap.media.tts.generate_tts_with_timing",
            autospec=True,
            side_effect=_fake_tts,
        ),
        "duration": patch(
            "stock_snap.media.tts.get_audio_duration", autospec=True, return_value=5.0
        ),
        "video": patch(
            "stock_snap.media.short_video.generate_short_video",
            autospec=True,
            side_effect=_fake_video,
        ),
        "thumbnail": patch(
            "stock_snap.media.short_video.generate_thumbnail",
            autospec=True,
            side_effect=_fake_thumbnail,
        ),
        "host": patch(
            "stock_snap.upload.media_host.publish_media",
            autospec=True,
            return_value="https://example.test/video.mp4",
        ),
        "reel": patch.object(instagram, "upload_reel", autospec=True, return_value=True),
        "short": patch.object(
            youtube, "upload_short", autospec=True, return_value="fake-video-id"
        ),
    }
    mocks = {name: p.start() for name, p in patches.items()}
    yield mocks
    for p in patches.values():
        p.stop()


@pytest.mark.parametrize("module_name", ["run_aftermarket", "run_weekly_review"])
def test_pipeline_runs_to_completion(module_name, mocked_externals, tmp_path, monkeypatch):
    """The pipeline must reach the upload step without raising or exiting non-zero."""
    module = importlib.import_module(module_name)
    # Both write to a cwd-relative output/ directory; keep that out of the repo.
    monkeypatch.chdir(tmp_path)

    module.run()

    assert mocked_externals["host"].called, "video was never given a public URL"
    assert mocked_externals["reel"].called, "Instagram upload was never attempted"
