from dataclasses import dataclass
from typing import Optional
import json, logging
import anthropic
from stock_pilot.news.collector import NewsItem
from stock_pilot.utils.config import config

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
    ) -> Optional[ContentPackage]:
        # Calculate change
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        direction = "상승" if change_pct > 0 else ("하락" if change_pct < 0 else "보합")

        # Format news
        news_text = "\n".join(
            f"- {item.title}" for item in news_items[:5]
        ) if news_items else "(최근 주요 뉴스 없음)"

        prompt = f"""당신은 한국의 금융 전문 숏폼 채널 콘텐츠 제작자입니다.

주식 정보:
- 종목: {symbol}
- 현재가: ${price:.2f}
- 등락률: {change_pct:+.2f}%
- 방향: {direction}
- 오늘의 주요 뉴스:
{news_text}
{f"- 시장 분석: {sentiment_summary}" if sentiment_summary else ""}

다음 JSON 형식으로 콘텐츠를 생성하세요 (마크다운 없이 순수 JSON):
{{
  "script": "60초 이내 숏폼 영상 나레이션. 자연스럽고 임팩트 있는 한국어. AI 느낌 최소화. 끝에 '본 콘텐츠는 투자 조언이 아닙니다.' 포함.",
  "card_title": "카드뉴스 헤드라인 (15자 이내, 임팩트 있게)",
  "card_subtitle": "서브타이틀 (30자 이내, 핵심 이유)",
  "card_body": "카드뉴스 본문 3줄. 숫자와 팩트 위주.",
  "caption": "SNS 캡션 (인스타/유튜브). 이모지 적절히. 관련 해시태그 5개. 끝에 '⚠️ 본 콘텐츠는 투자 조언이 아닙니다.' 포함."
}}

임팩트 있고 전문적인 금융 채널 느낌으로 작성하세요."""

        try:
            client = self._get_client()
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            data = json.loads(msg.content[0].text.strip())
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
            )
        except Exception:
            logger.exception("Content generation failed for %s", symbol)
            return None


generator = ContentGenerator()
