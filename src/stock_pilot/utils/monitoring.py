"""Pipeline monitoring — Sentry error capture + JSON execution report."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

_sentry_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry SDK if SENTRY_DSN is set. Returns True on success."""
    global _sentry_initialized
    if _sentry_initialized:
        return True

    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.debug("SENTRY_DSN not set — Sentry disabled")
        return False

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.0,  # no performance tracing — errors only
            environment=os.getenv("ENVIRONMENT", "production"),
            release=os.getenv("GITHUB_SHA", "unknown"),
        )
        _sentry_initialized = True
        logger.info("Sentry initialized (DSN configured)")
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry disabled. Run: pip install sentry-sdk")
        return False
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)
        return False


def capture_exception(exc: Exception, context: dict[str, Any] | None = None) -> None:
    """Send *exc* to Sentry with optional extra context."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except Exception as e:
        logger.debug("Sentry capture failed: %s", e)


def set_sentry_tag(key: str, value: str) -> None:
    """Set a tag on all subsequent Sentry events (e.g. symbol)."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        sentry_sdk.set_tag(key, value)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Pipeline execution report (JSON)
# ---------------------------------------------------------------------------

_REPORT_DIR = Path(os.getenv("CONTENT_OUTPUT_DIR", "output"))
_REPORT_FILE = _REPORT_DIR / "pipeline_report.json"
_MAX_HISTORY = 30  # keep last N runs


def _load_report() -> dict[str, Any]:
    if _REPORT_FILE.exists():
        try:
            return json.loads(_REPORT_FILE.read_text())
        except Exception:
            pass
    return {"runs": []}


def _save_report(data: dict[str, Any]) -> None:
    try:
        _REPORT_DIR.mkdir(parents=True, exist_ok=True)
        _REPORT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as exc:
        logger.warning("Could not write pipeline report: %s", exc)


def record_pipeline_run(
    *,
    status: str,  # "success" | "failure"
    symbol: str = "",
    change_pct: float = 0.0,
    platforms: list[str] | None = None,
    error: str = "",
    duration_secs: float = 0.0,
    run_id: str = "",
) -> None:
    """Append a pipeline run record to *output/pipeline_report.json*."""
    data = _load_report()
    runs: list[dict[str, Any]] = data.get("runs", [])

    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": status,
        "symbol": symbol,
        "change_pct": round(change_pct, 2),
        "platforms": platforms or [],
        "duration_secs": round(duration_secs, 1),
    }
    if error:
        entry["error"] = error
    if run_id:
        entry["github_run_id"] = run_id

    runs.append(entry)
    # Trim to keep only the most recent runs
    data["runs"] = runs[-_MAX_HISTORY:]
    data["last_updated"] = entry["timestamp"]
    data["summary"] = _compute_summary(data["runs"])
    _save_report(data)
    logger.info("Pipeline report updated: %s (status=%s)", _REPORT_FILE, status)


def _compute_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {}
    total = len(runs)
    successes = sum(1 for r in runs if r.get("status") == "success")
    return {
        "total_runs": total,
        "success_count": successes,
        "failure_count": total - successes,
        "success_rate_pct": round(successes / total * 100, 1),
        "last_status": runs[-1].get("status"),
        "last_symbol": runs[-1].get("symbol"),
    }
