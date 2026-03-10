from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import json, logging
import anthropic
from stock_pilot.news.collector import NewsItem
from stock_pilot.utils.config import config

if TYPE_CHECKING:
    from stock_pilot.analysis.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class ContentPackage:
    symbol: str
    price: float
    change_pct: float
    direction: str
    script: str
    card_title: str
    card_subtitle: str
    card_body: str
    caption: str
    # 퀀트 분석 데이터 (Remotion 템플릿용)
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    volume_ratio: float = 1.0
    bb_position: str = "middle"  # "upper" | "middle" | "lower"
    ema_trend: str = "mixed"     # "bullish" | "bearish" | "mixed"
    quant_summary: str = ""      # 퀀트 분석 요약 텍스트
    # 전망/예측 텍스트 (Quant Analyst 산출물)
    forecast: str = ""           # 영상 말미 삽입용 단문 전망 (1~2줄)
    forecast_detail: str = ""    # 게시글(캡션) 포함용 상세 전망 (3~5줄)
    # 차트 데이터 포인트 (최근 20일 종가, Remotion 애니메이션용)
    chart_data: list[float] = field(default_factory=list)


class ContentGenerator:
    def __init__(self):
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    def generate(
        self,
        symbol: str,
        price: float,
        prev_close: float,
        news_items: list[NewsItem],
        sentiment_summary: str = "",
        tech: "TechnicalIndicators | None" = None,
        chart_data: list[float] | None = None,
    ) -> Optional[ContentPackage]:
        # Calculate change
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        direction = "상승" if change_pct > 0 else ("하락" if change_pct < 0 else "보합")

        # Format news
        news_text = "\n".join(
            f"- {item.title}" for item in news_items[:5]
        ) if news_items else "(최근 주요 뉴스 없음)"

        # 퀀트 분석 텍스트 (신규 지표 포함)
        quant_text = ""
        if tech:
            rsi_zone = tech.rsi_zone
            ema_trend = tech.ema_trend
            sma_trend = tech.sma_trend
            bb_pos = tech.bb_position
            vol_spike = "거래량 스파이크 발생" if tech.volume_spike else "거래량 정상"
            trend_dir = tech.trendline.direction if tech.trendline else "flat"
            trend_r2 = tech.trendline.r_squared if tech.trendline else 0.0
            quant_text = f"""
퀀트 분석:
- RSI(14): {tech.rsi14:.1f} ({rsi_zone})
- MACD: {tech.macd:.3f} / Signal: {tech.macd_signal:.3f} (히스토그램: {tech.macd_hist:.3f})
- 볼린저밴드: {bb_pos} ({tech.bb_lower:.2f} ~ {tech.bb_upper:.2f}){" [스퀴즈]" if tech.bb_squeeze else ""}
- 이동평균선: SMA5={tech.sma5:.2f} / SMA20={tech.sma20:.2f} / SMA60={tech.sma60:.2f} → {sma_trend} ({"골든크로스" if tech.golden_cross else "데드크로스"})
- EMA 추세: {ema_trend} (EMA9={tech.ema9:.2f} / EMA21={tech.ema21:.2f} / EMA50={tech.ema50:.2f})
- {vol_spike}
- 20일 추세선: {trend_dir} (R²={trend_r2:.2f})
- 피벗포인트: P={tech.pivot:.2f} / R1={tech.pivot_r1:.2f} / S1={tech.pivot_s1:.2f}
- 지지선: {tech.support:.2f} / 저항선: {tech.resistance:.2f}"""

        prompt = f"""당신은 한국의 금융 전문 숏폼 채널 퀀트 애널리스트 겸 콘텐츠 제작자입니다.

주식 정보:
- 종목: {symbol}
- 현재가: ${price:.2f}
- 등락률: {change_pct:+.2f}%
- 방향: {direction}
- 오늘의 주요 뉴스:
{news_text}
{f"- 시장 분석: {sentiment_summary}" if sentiment_summary else ""}
{quant_text}

다음 JSON 형식으로 콘텐츠를 생성하세요 (마크다운 없이 순수 JSON):
{{
  "script": "30초 숏폼 영상 나레이션 (200자 이내). 자연스럽고 임팩트 있는 한국어. 퀀트 지표 자연스럽게 언급. 영상 말미에 전망 1~2줄 포함. AI 느낌 최소화. 끝에 '본 콘텐츠는 투자 조언이 아닙니다.' 포함.",
  "card_title": "카드뉴스 헤드라인 (15자 이내, 임팩트 있게)",
  "card_subtitle": "서브타이틀 (30자 이내, 핵심 이유)",
  "card_body": "카드뉴스 본문 3줄. 숫자와 팩트 위주. 퀀트 지표 포함.",
  "caption": "SNS 게시글 (인스타/유튜브). 이모지 적절히. 뉴스 분석 요약 + 퀀트 전망을 함께 상세히 서술 (6~8줄). 관련 해시태그 5개. 끝에 '⚠️ 본 콘텐츠는 투자 조언이 아닙니다.' 포함.",
  "quant_summary": "퀀트 관점 2~3줄 요약. RSI 과매수/과매도 여부, MACD 추세, 볼린저밴드 위치, 이동평균선 정렬 등 전문적 분석.",
  "forecast": "향후 전망 단문 (1~2줄, 영상 말미 삽입용). 기술적 지표 기반 단기 방향성. '~할 가능성', '~에 주목' 등 신중한 표현 사용. 투자 조언 금지.",
  "forecast_detail": "향후 전망 상세 (3~5줄, 게시글 포함용). 기술적 근거(SMA/EMA/RSI/피벗 등) + 뉴스 흐름 + 단기 시나리오(bull/bear) 제시. 신중하고 전문적인 어조. 투자 조언 금지."
}}

임팩트 있고 전문적인 금융 채널 느낌으로 작성하세요."""

        try:
            client = self._get_client()
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            # JSON 블록 추출 (```json ... ``` 래핑 가능)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())

            return ContentPackage(
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                direction=direction,
                script=data.get("script", ""),
                card_title=data.get("card_title", f"{symbol} {direction}"),
                card_subtitle=data.get("card_subtitle", f"{change_pct:+.2f}%"),
                card_body=data.get("card_body", ""),
                caption=data.get("caption", ""),
                quant_summary=data.get("quant_summary", ""),
                forecast=data.get("forecast", ""),
                forecast_detail=data.get("forecast_detail", ""),
                rsi=tech.rsi14 if tech else 0.0,
                macd=tech.macd if tech else 0.0,
                macd_signal=tech.macd_signal if tech else 0.0,
                volume_ratio=(tech.volume / tech.volume_sma20) if (tech and tech.volume_sma20 > 0) else 1.0,
                bb_position=tech.bb_position if tech else "middle",
                ema_trend=tech.ema_trend if tech else "mixed",
                chart_data=chart_data or [],
            )
        except Exception:
            logger.exception("Content generation failed for %s", symbol)
            return None


generator = ContentGenerator()
