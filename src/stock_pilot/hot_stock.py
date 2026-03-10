"""핫 주식 자동 선정 모듈.

yfinance 실시간 데이터를 활용해 미국 주식 중 가장 주목받는 종목 1개를 자동 선정한다.
기준: 등락률 + 거래량 스파이크 복합 점수 (업계 표준 20일 평균 거래량 기반).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# 스캔 대상 종목 풀 (S&P500 대표 + 인기 테마주)
SCAN_UNIVERSE: list[str] = [
    # 대형 기술주
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "GOOG",
    "AMD", "INTC", "QCOM", "AVGO", "ORCL", "CRM", "SNOW", "PLTR",
    # 핀테크/바이오/AI
    "SOFI", "HOOD", "COIN", "MRNA", "BNTX", "LLY", "ABBV", "PFE",
    # ETF (레버리지 포함)
    "SPY", "QQQ", "TQQQ", "SQQQ", "ARKK",
    # 에너지/소재
    "XOM", "CVX", "FCX", "NEM",
    # 소비재/엔터
    "NFLX", "DIS", "SBUX", "NKE", "UBER", "LYFT",
]

# 20일 평균 거래량 계산에 필요한 최소 데이터 일수
_MIN_ROWS = 2
# 평균 거래량 계산 윈도우 (업계 표준)
_VOL_AVG_WINDOW = 20


@dataclass
class HotStockResult:
    symbol: str
    price: float
    prev_close: float
    change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float  # 현재 거래량 / 20일 평균 거래량
    hot_score: float     # 종합 핫 점수 (0~100)
    direction: str       # "상승" | "하락" | "보합"


def _score(change_pct: float, volume_ratio: float) -> float:
    """등락률과 거래량 비율로 핫 점수 계산 (0~100).

    - 등락률 점수: 절대값 기준 최대 50점 (5% 이상 = 만점)
    - 거래량 스파이크 점수: 최대 50점 (3배 이상 = 만점, 1배 미만 = 0점)
    """
    price_score = min(abs(change_pct) / 5.0 * 50, 50)
    vol_score = min((volume_ratio - 1.0) / 2.0 * 50, 50) if volume_ratio > 1.0 else 0
    return round(price_score + vol_score, 2)


def _build_results(raw: pd.DataFrame, symbols: list[str]) -> list[HotStockResult]:
    """yfinance 다운로드 결과에서 HotStockResult 리스트 생성."""
    results: list[HotStockResult] = []
    single = len(symbols) == 1

    for sym in symbols:
        try:
            if single:
                df = raw
            else:
                # yfinance MultiIndex: (ticker, price_type)
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym]

            if df is None or df.empty or len(df) < _MIN_ROWS:
                continue

            df = df.dropna(subset=["Close", "Volume"])
            if len(df) < _MIN_ROWS:
                continue

            close_today = float(df["Close"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            vol_today = int(df["Volume"].iloc[-1])

            # 20일 평균 거래량 (오늘 제외) — 표준 볼륨 기준선
            vol_series = df["Volume"].iloc[:-1]  # 오늘 제외
            avg_vol = int(vol_series.tail(_VOL_AVG_WINDOW).mean()) if len(vol_series) > 0 else int(df["Volume"].mean())

            if close_prev <= 0 or avg_vol <= 0:
                continue

            change_pct = (close_today - close_prev) / close_prev * 100
            vol_ratio = vol_today / avg_vol
            score = _score(change_pct, vol_ratio)
            direction = "상승" if change_pct > 0 else ("하락" if change_pct < 0 else "보합")

            results.append(
                HotStockResult(
                    symbol=sym,
                    price=close_today,
                    prev_close=close_prev,
                    change_pct=round(change_pct, 2),
                    volume=vol_today,
                    avg_volume=avg_vol,
                    volume_ratio=round(vol_ratio, 2),
                    hot_score=score,
                    direction=direction,
                )
            )
        except Exception as e:
            logger.debug("종목 처리 실패 %s: %s", sym, e)

    return results


def _download(symbols: list[str]) -> pd.DataFrame | None:
    """yfinance bulk download. 1달치 데이터로 20일 평균 거래량 확보."""
    try:
        return yf.download(
            symbols,
            period="1mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error("yfinance bulk download 실패: %s", e)
        return None


def select_hot_stock(universe: list[str] | None = None) -> HotStockResult | None:
    """스캔 유니버스에서 가장 핫한 주식 1개를 선정한다.

    Args:
        universe: 스캔할 종목 리스트. None이면 기본 SCAN_UNIVERSE 사용.

    Returns:
        HotStockResult or None (데이터 부족 시)
    """
    top = select_top_n(n=1, universe=universe)
    return top[0] if top else None


def select_top_n(n: int = 5, universe: list[str] | None = None) -> list[HotStockResult]:
    """스캔 유니버스에서 핫 점수 상위 N개 종목을 반환한다.

    Args:
        n: 반환할 종목 수.
        universe: 스캔할 종목 리스트. None이면 기본 SCAN_UNIVERSE 사용.

    Returns:
        HotStockResult 리스트 (점수 내림차순). 결과 없으면 빈 리스트.
    """
    symbols = universe or SCAN_UNIVERSE
    logger.info("핫 주식 스캔 시작: %d 종목 (상위 %d개 선정)", len(symbols), n)

    raw = _download(symbols)
    if raw is None or raw.empty:
        logger.warning("데이터 다운로드 실패 또는 빈 결과")
        return []

    results = _build_results(raw, symbols)

    if not results:
        logger.warning("스캔 결과 없음")
        return []

    results.sort(key=lambda r: r.hot_score, reverse=True)

    top = results[:n]
    for i, r in enumerate(top, 1):
        logger.info(
            "[%d] %s | 등락률 %+.2f%% | 거래량비율 %.1fx | 점수 %.1f",
            i, r.symbol, r.change_pct, r.volume_ratio, r.hot_score,
        )

    return top
