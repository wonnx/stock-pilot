"""Watchlist management — persistent list of tickers to monitor."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from stock_pilot.utils.config import config

logger = logging.getLogger(__name__)

WATCHLIST_PATH = Path(__file__).parent.parent.parent.parent / "data" / "watchlist.json"


class Watchlist:
    """Manage the list of symbols to scan."""

    def __init__(self, path: Path = WATCHLIST_PATH) -> None:
        self._path = path
        self._symbols: list[str] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open() as f:
                    self._symbols = json.load(f)
                logger.info("Loaded %d symbols from watchlist", len(self._symbols))
            except Exception:
                logger.exception("Failed to load watchlist, using defaults")
                self._symbols = list(config.DEFAULT_WATCHLIST)
        else:
            self._symbols = list(config.DEFAULT_WATCHLIST)
            self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._symbols, f, indent=2)

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    def add(self, symbol: str) -> None:
        symbol = symbol.upper().strip()
        if symbol not in self._symbols:
            self._symbols.append(symbol)
            self._save()
            logger.info("Added %s to watchlist", symbol)

    def remove(self, symbol: str) -> None:
        symbol = symbol.upper().strip()
        if symbol in self._symbols:
            self._symbols.remove(symbol)
            self._save()
            logger.info("Removed %s from watchlist", symbol)

    def __contains__(self, symbol: str) -> bool:
        return symbol.upper() in self._symbols

    def __len__(self) -> int:
        return len(self._symbols)


watchlist = Watchlist()
