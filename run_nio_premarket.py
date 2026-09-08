"""One-off: produce NIO pre-market short video from Market Analyst WON-46 report."""
import sys
import logging

sys.path.insert(0, "src")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run():
    import stock_snap.hot_stock as _hs_mod
    from stock_snap.hot_stock import HotStockResult

    # NIO data from Market Analyst WON-46 report (2026-03-12 pre-market)
    nio = HotStockResult(
        symbol="NIO",
        price=5.62,
        prev_close=5.47,
        change_pct=2.74,
        volume=77843900,         # yesterday's volume
        avg_volume=45256150,     # 3-month average
        volume_ratio=3.27,       # earnings day ratio (peak institutional activity)
        hot_score=abs(2.74) * 10 + 50,  # price score + volume spike bonus
        direction="rising",
    )

    _original = _hs_mod.select_hot_stock
    _hs_mod.select_hot_stock = lambda *a, **kw: nio

    try:
        import run_live_short
        run_live_short.run()
    finally:
        _hs_mod.select_hot_stock = _original


if __name__ == "__main__":
    run()
