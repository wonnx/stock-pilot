"""Tests for retry utility and pipeline monitoring."""

from __future__ import annotations

import json
import sys

import pytest

sys.path.insert(0, "src")

from stock_snap.utils.retry import with_retry

# ---------------------------------------------------------------------------
# retry tests
# ---------------------------------------------------------------------------


def test_retry_succeeds_on_first_attempt():
    calls = []

    def func():
        calls.append(1)
        return "ok"

    result = with_retry(func, max_attempts=3, base_delay=0.0)
    assert result == "ok"
    assert len(calls) == 1


def test_retry_succeeds_after_failures():
    calls = []

    def func():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("transient")
        return "done"

    result = with_retry(func, max_attempts=3, base_delay=0.0, exceptions=(ValueError,))
    assert result == "done"
    assert len(calls) == 3


def test_retry_raises_after_max_attempts():
    calls = []

    def func():
        calls.append(1)
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        with_retry(func, max_attempts=3, base_delay=0.0, exceptions=(RuntimeError,))
    assert len(calls) == 3


def test_retry_does_not_catch_unspecified_exceptions():
    def func():
        raise TypeError("not caught")

    with pytest.raises(TypeError):
        with_retry(func, max_attempts=3, base_delay=0.0, exceptions=(ValueError,))


# ---------------------------------------------------------------------------
# monitoring tests
# ---------------------------------------------------------------------------


def test_record_pipeline_run_creates_report(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTENT_OUTPUT_DIR", str(tmp_path))
    # Re-import to pick up monkeypatched env
    import importlib

    import stock_snap.utils.monitoring as mon
    importlib.reload(mon)

    mon.record_pipeline_run(
        status="success",
        symbol="NVDA",
        change_pct=5.2,
        platforms=["Instagram"],
        duration_secs=42.0,
    )

    report_file = tmp_path / "pipeline_report.json"
    assert report_file.exists()
    data = json.loads(report_file.read_text())
    assert len(data["runs"]) == 1
    run = data["runs"][0]
    assert run["status"] == "success"
    assert run["symbol"] == "NVDA"
    assert run["change_pct"] == 5.2
    assert run["platforms"] == ["Instagram"]
    assert data["summary"]["success_count"] == 1


def test_record_pipeline_run_trims_to_max_history(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTENT_OUTPUT_DIR", str(tmp_path))
    import importlib

    import stock_snap.utils.monitoring as mon
    importlib.reload(mon)
    mon._MAX_HISTORY = 5

    for i in range(7):
        mon.record_pipeline_run(status="success", symbol=f"SYM{i}", duration_secs=1.0)

    data = json.loads((tmp_path / "pipeline_report.json").read_text())
    assert len(data["runs"]) == 5
    assert data["runs"][-1]["symbol"] == "SYM6"


def test_init_sentry_no_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    import importlib

    import stock_snap.utils.monitoring as mon
    importlib.reload(mon)

    result = mon.init_sentry()
    assert result is False
