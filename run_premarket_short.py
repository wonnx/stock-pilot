"""Generate a short-form video based on pre-market (프리마켓/프장) hot stock data."""
import sys
import logging
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def select_premarket_hot_stock():
    """Select the hottest stock based on current pre-market data using yfinance fast_info."""
    import yfinance as yf

    UNIVERSE = [
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "GOOG",
        "AMD", "INTC", "QCOM", "AVGO", "CRM", "SNOW", "PLTR",
        "SOFI", "HOOD", "COIN", "MRNA", "BNTX", "LLY",
        "NFLX", "DIS", "UBER", "LYFT", "SMCI", "MSTR", "ARM", "RIVN", "LCID",
    ]

    def _fetch(sym):
        try:
            tk = yf.Ticker(sym)
            fi = tk.fast_info
            pm_price = getattr(fi, "pre_market_price", None)
            prev_close = getattr(fi, "previous_close", None)
            last_price = getattr(fi, "last_price", None)

            # Use pre-market price if available; fall back to last price
            price = pm_price if pm_price else last_price
            if not price or not prev_close or prev_close <= 0:
                return None

            chg_pct = (price - prev_close) / prev_close * 100
            return {"symbol": sym, "price": price, "prev_close": prev_close, "change_pct": round(chg_pct, 2)}
        except Exception:
            return None

    logger.info("Fetching pre-market data for %d symbols...", len(UNIVERSE))
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(filter(None, ex.map(_fetch, UNIVERSE)))

    if not results:
        logger.warning("No pre-market data available")
        return None

    # Sort by absolute change
    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)

    logger.info("=== Pre-Market Top 5 ===")
    for r in results[:5]:
        arrow = "▲" if r["change_pct"] > 0 else "▼"
        logger.info("  %s %s%.2f%%  $%.2f", r["symbol"], arrow, abs(r["change_pct"]), r["price"])

    best = results[0]

    # Build a HotStockResult from pre-market data
    from stock_snap.hot_stock import HotStockResult

    direction = "rising" if best["change_pct"] > 0 else ("falling" if best["change_pct"] < 0 else "flat")
    # volume_ratio not available in pre-market — use 1.0 as neutral placeholder
    return HotStockResult(
        symbol=best["symbol"],
        price=best["price"],
        prev_close=best["prev_close"],
        change_pct=best["change_pct"],
        volume=0,
        avg_volume=0,
        volume_ratio=1.0,
        hot_score=abs(best["change_pct"]) * 10,
        direction=direction,
    )


def run():
    # Patch select_hot_stock with our pre-market version BEFORE importing run_live_short
    import stock_snap.hot_stock as _hs_mod
    _original = _hs_mod.select_hot_stock

    hot = select_premarket_hot_stock()
    if not hot:
        logger.error("Pre-market hot stock selection failed")
        sys.exit(1)

    logger.info("Pre-market hot stock: %s %+.2f%%", hot.symbol, hot.change_pct)

    # Monkey-patch select_hot_stock for the pipeline
    _hs_mod.select_hot_stock = lambda *a, **kw: hot

    try:
        import run_live_short
        run_live_short.run()
    finally:
        _hs_mod.select_hot_stock = _original


if __name__ == "__main__":
    run()
