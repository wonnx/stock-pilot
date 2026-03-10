"""핫 주식 자동 선정 모듈.

yfinance 실시간 데이터를 활용해 미국 주식 중 가장 주목받는 종목 1개를 자동 선정한다.
기준: 등락률 + 거래량 스파이크 복합 점수.
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


@dataclass
class HotStockResult:
    symbol: str
    price: float
    prev_close: float
    change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float  # 현재 거래량 / 평균 거래량
    hot_score: float     # 종합 핫 점수 (0~100)
    direction: str       # "상승" | "하락" | "보합"


def _score(change_pct: float, volume_ratio: float) -> float:
    """등락률과 거래량 비율로 핫 점수 계산 (0~100)."""
    # 절대 등락률 점수 (최대 50점, 5% 이상이면 만점)
    price_score = min(abs(change_pct) / 5.0 * 50, 50)
    # 거래량 스파이크 점수 (최대 50점, 3배 이상이면 만점)
    vol_score = min((volume_ratio - 1.0) / 2.0 * 50, 50) if volume_ratio > 1.0 else 0
    return round(price_score + vol_score, 2)


def select_hot_stock(universe: list[str] | None = None) -> HotStockResult | None:
    """
    스캔 유니버스에서 가장 핫한 주식 1개를 선정한다.

    Args:
        universe: 스캔할 종목 리스트. None이면 기본 SCAN_UNIVERSE 사용.

    Returns:
        HotStockResult or None (데이터 부족 시)
    """
    symbols = universe or SCAN_UNIVERSE
    logger.info("핫 주식 스캔 시작: %d 종목", len(symbols))

    results: list[HotStockResult] = []

    try:
        # yfinance bulk download로 오늘 데이터 한 번에 가져오기
        raw = yf.download(
            symbols,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error("yfinance bulk download 실패: %s", e)
        return None

    for sym in symbols:
        try:
            # 단일 종목 vs 복수 종목 DataFrame 구조 차이 처리
            if len(symbols) == 1:
                df = raw
            else:
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym]

            if df is None or df.empty or len(df) < 2:
                continue

            df = df.dropna(subset=["Close", "Volume"])
            if len(df) < 2:
                continue

            close_today = float(df["Close"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            vol_today = int(df["Volume"].iloc[-1])
            # 평균 거래량: 최근 5일 평균
            avg_vol = int(df["Volume"].mean())

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
            continue

    if not results:
        logger.warning("스캔 결과 없음")
        return None

    # 핫 점수 기준 내림차순 정렬
    results.sort(key=lambda r: r.hot_score, reverse=True)

    top = results[0]
    logger.info(
        "핫 주식 선정: %s | 등락률 %+.2f%% | 거래량비율 %.1fx | 점수 %.1f",
        top.symbol, top.change_pct, top.volume_ratio, top.hot_score,
    )

    # 상위 5개 로그
    for r in results[:5]:
        logger.debug("  %s: %+.2f%% vol×%.1f score=%.1f", r.symbol, r.change_pct, r.volume_ratio, r.hot_score)

    return top
