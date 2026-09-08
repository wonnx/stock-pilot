"""Exponential backoff retry utility."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def with_retry[T](
    func: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    label: str = "",
) -> T:
    """Call *func* with exponential backoff on failure.

    Args:
        func: Zero-argument callable to invoke.
        max_attempts: Maximum number of total attempts.
        base_delay: Initial delay in seconds (doubles each retry).
        max_delay: Cap on delay between retries.
        exceptions: Exception types that trigger a retry.
        label: Human-readable label for log messages.

    Returns:
        Return value of *func* on success.

    Raises:
        Last exception from *func* if all attempts fail.
    """
    name = label or getattr(func, "__name__", repr(func))
    last_exc: Exception | None = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                logger.error("[retry] %s failed after %d attempts: %s", name, max_attempts, exc)
                break
            actual_delay = min(delay, max_delay)
            logger.warning(
                "[retry] %s attempt %d/%d failed (%s) — retrying in %.1fs",
                name,
                attempt,
                max_attempts,
                exc,
                actual_delay,
            )
            time.sleep(actual_delay)
            delay *= 2

    raise last_exc  # type: ignore[misc]
