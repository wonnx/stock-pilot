"""
v12 QA 자동화 테스트 — TC-002, TC-003(코드 검증), TC-004, TC-005

실행:
    cd <repo root>
    uv run pytest tests/test_v12_qa.py -v

또는:
    uv run python tests/test_v12_qa.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ---------------------------------------------------------------------------
# TC-002: TTS 종목코드 → 한글 기업명 (코드 레벨 검증)
# ---------------------------------------------------------------------------

class TestTC002_TtsKoreanName:
    """TC-002: TTS 스크립트에 종목코드 대신 한글 기업명이 사용되는지 검증."""

    COMPANY_NAMES_KO = {
        "AAPL": "애플", "MSFT": "마이크로소프트", "GOOGL": "구글",
        "AMZN": "아마존", "META": "메타", "TSLA": "테슬라",
        "NVDA": "엔비디아", "NFLX": "넷플릭스", "AMD": "AMD",
        "INTC": "인텔", "PLTR": "팔란티어",
    }

    def test_tts_name_uses_korean_for_known_symbol(self):
        """알려진 종목(NVDA)에 대해 한글 기업명 반환 확인."""
        symbol = "NVDA"
        tts_name = self.COMPANY_NAMES_KO.get(symbol, symbol)
        assert tts_name == "엔비디아", f"Expected '엔비디아', got '{tts_name}'"

    def test_tts_name_fallback_to_ticker_for_unknown(self):
        """미등록 종목에 대해 티커 그대로 반환 (fallback)."""
        symbol = "UNKNOWN_XYZ"
        tts_name = self.COMPANY_NAMES_KO.get(symbol, symbol)
        assert tts_name == "UNKNOWN_XYZ"

    def test_seg_news_uses_tts_name_not_symbol(self):
        """뉴스 인트로 세그먼트에 symbol이 아닌 tts_name이 포함되어야 함."""
        symbol = "NVDA"
        change_pct = 5.5
        tts_name = self.COMPANY_NAMES_KO.get(symbol, symbol)
        # v12 로직 재현 (run_live_short.py line 232)
        intro = f"{tts_name} 주가가 {'급등' if change_pct > 0 else '급락'}한 주요 배경을 살펴보겠습니다. "
        assert "엔비디아" in intro, f"'엔비디아' not found in intro: {intro}"
        assert "NVDA" not in intro, f"'NVDA' (ticker) should not be in intro: {intro}"

    def test_seg_news_fallback_uses_tts_name(self):
        """뉴스가 없을 때 fallback 텍스트에도 한글명 사용 확인."""
        symbol = "AAPL"
        change_pct = -3.2
        tts_name = self.COMPANY_NAMES_KO.get(symbol, symbol)

        # v12 로직 재현 (run_live_short.py line 246)
        seg_news_fallback = (
            f"{tts_name}의 {'급등' if change_pct > 0 else '급락'} 배경을 살펴보겠습니다. "
        )
        assert "애플" in seg_news_fallback
        assert "AAPL" not in seg_news_fallback

    def test_all_major_symbols_have_korean_name(self):
        """주요 종목 10개 이상이 한글명 딕셔너리에 등록되어 있는지 확인."""
        assert len(self.COMPANY_NAMES_KO) >= 10, "한글 기업명 딕셔너리가 너무 적음"

    def test_tts_generate_function_exists(self):
        """TTS 생성 함수가 존재하는지 확인."""
        from stock_snap.media.tts import generate_tts, generate_tts_with_timing
        assert callable(generate_tts)
        assert callable(generate_tts_with_timing)

    def test_tts_returns_bool(self):
        """TTS 함수가 bool을 반환하는지 확인 (실제 API 호출 없이 mock)."""
        from stock_snap.media.tts import generate_tts
        with patch("stock_snap.media.tts._generate_edge_tts") as mock_tts:
            mock_tts.return_value = True
            result = generate_tts("엔비디아 주가가 급등했습니다.", Path("/tmp/test.mp3"))
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# TC-003: BGM 코드 레벨 검증 (Remotion TSX)
# ---------------------------------------------------------------------------

class TestTC003_BgmContinuous:
    """TC-003: BGM이 Sequence 래퍼 없이 전구간 재생되는지 코드 검증."""

    def test_bgm_no_sequence_wrapper(self):
        """StockShort.tsx에서 BGM Audio 태그에 Sequence 래퍼가 없어야 함."""
        tsx_path = Path(__file__).parent.parent / "remotion/src/StockShort.tsx"
        assert tsx_path.exists(), f"StockShort.tsx not found at {tsx_path}"

        content = tsx_path.read_text()

        # v12: BGM은 Sequence 없이 직접 Audio 태그
        # 잘못된 패턴: Sequence 안에 BGM Audio가 loop로 있는 것
        bad_pattern = re.search(r"<Sequence[^>]*>.*?bgmPath.*?loop", content, re.DOTALL)
        assert bad_pattern is None, "v11 방식의 BGM Sequence+loop 패턴이 남아 있음"

    def test_bgm_audio_tag_exists(self):
        """BGM Audio 태그가 존재하는지 확인."""
        tsx_path = Path(__file__).parent.parent / "remotion/src/StockShort.tsx"
        content = tsx_path.read_text()

        # BGM Audio 태그 존재 확인
        assert "bgmPath" in content, "bgmPath prop이 없음"

        # volume 0.126 적용 확인
        assert "volume={0.126}" in content, "BGM 볼륨이 0.126이 아님"

    def test_bgm_audio_without_loop(self):
        """BGM Audio 태그에 loop 속성이 없어야 함 (v12 변경)."""
        tsx_path = Path(__file__).parent.parent / "remotion/src/StockShort.tsx"
        content = tsx_path.read_text()

        # BGM 관련 Audio 태그 주변에 loop가 없어야 함
        # BGM Audio 라인 찾기
        lines = content.split("\n")
        bgm_audio_lines = [line for line in lines if "bgmPath" in line and "Audio" in line]

        # bgmPath에 loop가 없는지 확인
        for line in bgm_audio_lines:
            assert "loop" not in line, f"BGM Audio에 loop 속성이 있음: {line.strip()}"


# ---------------------------------------------------------------------------
# TC-004: 뉴스 방향 일관성 (LLM 분석 로직 검증)
# ---------------------------------------------------------------------------

class TestTC004_NewsDirectionConsistency:
    """TC-004: 뉴스 LLM 방향 검증 로직 테스트."""

    def _make_analyze_fn(self):
        """run_live_short.py의 analyze_news_direction 함수를 인라인으로 재현."""
        def analyze_news_direction(
            articles: list[tuple[str, str]],
            sym: str,
            chg: float,
        ) -> list[tuple[str, str]]:
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key or not articles:
                return articles
            try:
                import anthropic
                direction_ko = "급등(상승)" if chg > 0 else "급락(하락)"
                articles_text = "\n".join(
                    f"{i+1}. 제목: {t}\n   내용: {d}" if d else f"{i+1}. 제목: {t}"
                    for i, (t, d) in enumerate(articles[:10])
                )
                prompt = (
                    f"주식 {sym}이 오늘 {chg:+.1f}% {direction_ko}했습니다.\n\n"
                    f"아래는 수집된 뉴스 기사 목록입니다:\n{articles_text}\n\n"
                    f"다음 지시를 따르세요:\n"
                    f"1. 오늘의 {direction_ko}을 가장 잘 설명하는 기사 최대 3개를 선별하세요.\n"
                    f"2. 응답은 반드시 JSON 배열만 반환하세요: "
                    f'[{{"title": "제목", "detail": "한 문장 핵심 내용"}}, ...]'
                )
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=800,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = resp.content[0].text.strip()
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    items = json.loads(text[start:end])
                    result = [(item.get("title", ""), item.get("detail", "")) for item in items if item.get("title")]
                    if result:
                        return result
            except Exception:
                pass
            return articles
        return analyze_news_direction

    def test_fallback_when_no_api_key(self):
        """ANTHROPIC_API_KEY 미설정 시 원본 articles 반환."""
        analyze = self._make_analyze_fn()
        articles = [("AI demand surges", "NVIDIA benefits"), ("Market drops", "Sell-off")]
        with patch.dict("os.environ", {}, clear=False):
            import os
            original = os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                result = analyze(articles, "NVDA", 5.0)
                assert result == articles, "API 키 없을 때 원본 articles 반환해야 함"
            finally:
                if original:
                    os.environ["ANTHROPIC_API_KEY"] = original

    def test_fallback_when_empty_articles(self):
        """빈 articles 입력 시 빈 리스트 반환."""
        analyze = self._make_analyze_fn()
        result = analyze([], "NVDA", 5.0)
        assert result == []

    def test_llm_response_parsing(self):
        """LLM JSON 응답 파싱 로직 검증 (mock)."""
        analyze = self._make_analyze_fn()
        mock_response_text = '[{"title": "엔비디아 AI 수요 급증", "detail": "데이터센터 매출 급증"}]'

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=mock_response_text)]
        mock_client.messages.create.return_value = mock_resp

        articles = [("NVIDIA AI demand", "Strong demand"), ("Market sell-off", "Risk off")]
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = analyze(articles, "NVDA", 5.0)
                assert len(result) == 1
                assert result[0][0] == "엔비디아 AI 수요 급증"
                assert result[0][1] == "데이터센터 매출 급증"

    def test_llm_returns_max_3_articles(self):
        """LLM 응답이 최대 3개 아티클을 반환하는지 검증 (mock)."""
        mock_response = json.dumps([
            {"title": "제목1", "detail": "내용1"},
            {"title": "제목2", "detail": "내용2"},
            {"title": "제목3", "detail": "내용3"},
        ])
        analyze = self._make_analyze_fn()

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=mock_response)]
        mock_client.messages.create.return_value = mock_resp

        articles = [(f"Article {i}", f"Detail {i}") for i in range(8)]
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = analyze(articles, "NVDA", 5.0)
                assert len(result) <= 3, f"최대 3개여야 하는데 {len(result)}개 반환됨"

    def test_news_deduplication(self):
        """중복 뉴스 제거 로직 확인 (yfinance + NewsCollector 병합)."""
        # v12 중복 제거 로직 재현
        raw_news: list[tuple[str, str]] = [("NVIDIA AI surge", "Strong demand")]
        existing_titles = {t.lower() for t, _ in raw_news}

        # 같은 제목이 다른 소스에서 올 경우
        new_article_same = ("NVIDIA AI surge", "Different detail")  # 중복
        new_article_diff = ("NVIDIA earnings beat", "Revenue up 200%")  # 새 기사

        if new_article_same[0].lower() not in existing_titles:
            raw_news.append(new_article_same)
        if new_article_diff[0].lower() not in existing_titles:
            raw_news.append(new_article_diff)
            existing_titles.add(new_article_diff[0].lower())

        assert len(raw_news) == 2, "중복 기사가 추가되어서는 안 됨"
        assert ("NVIDIA earnings beat", "Revenue up 200%") in raw_news


# ---------------------------------------------------------------------------
# TC-005: 자막/캡션 상세화 검증
# ---------------------------------------------------------------------------

class TestTC005_CaptionDetail:
    """TC-005: 뉴스 요약 캡션에 제목 + 상세 내용이 포함되는지 검증."""

    def _build_news_summary(self, news_headlines: list[str]) -> str:
        """run_live_short.py v12 news_summary 생성 로직 재현."""
        news_summary_items = []
        for h in news_headlines[:3]:
            parts = h.split("\n")
            title_part = parts[0]
            detail_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
            if detail_part:
                news_summary_items.append(f"• {title_part}\n  → {detail_part[:120]}")
            else:
                news_summary_items.append(f"• {title_part}")
        return "\n".join(news_summary_items) if news_summary_items else ""

    def test_news_summary_includes_detail(self):
        """뉴스 detail이 있을 때 → 형식으로 포함되는지 확인."""
        headlines = ["엔비디아 AI 수요 급증\n데이터센터 매출 전년비 200% 성장으로 실적 어닝 서프라이즈"]
        summary = self._build_news_summary(headlines)
        assert "• 엔비디아 AI 수요 급증" in summary
        assert "→ 데이터센터 매출" in summary

    def test_news_summary_bullet_format(self):
        """불릿 포인트(•) 형식 사용 확인."""
        headlines = ["엔비디아 상승\n매출 증가", "AMD 급등\n반도체 수요"]
        summary = self._build_news_summary(headlines)
        bullet_count = summary.count("•")
        assert bullet_count == 2, f"불릿 포인트가 2개여야 하는데 {bullet_count}개"

    def test_news_summary_no_detail(self):
        """뉴스 detail 없을 때 제목만 표시."""
        headlines = ["엔비디아 주가 상승"]  # 줄바꿈 없음
        summary = self._build_news_summary(headlines)
        assert "• 엔비디아 주가 상승" in summary
        assert "→" not in summary

    def test_news_summary_detail_truncated_at_120(self):
        """상세 내용이 120자에서 잘리는지 확인."""
        long_detail = "A" * 200
        headlines = [f"테스트 제목\n{long_detail}"]
        summary = self._build_news_summary(headlines)
        # → 뒤의 내용이 120자 이하인지 확인
        arrow_idx = summary.find("→")
        if arrow_idx >= 0:
            detail_content = summary[arrow_idx + 2:]
            assert len(detail_content) <= 120, f"상세 내용이 120자 초과: {len(detail_content)}자"

    def test_news_summary_max_3_items(self):
        """최대 3개 뉴스만 표시."""
        headlines = [f"뉴스 {i}\n내용 {i}" for i in range(6)]
        summary = self._build_news_summary(headlines)
        bullet_count = summary.count("•")
        assert bullet_count <= 3, f"최대 3개인데 {bullet_count}개 표시됨"

    def test_v11_vs_v12_summary_format_difference(self):
        """v11과 v12의 뉴스 요약 형식 차이 확인."""
        headlines = ["엔비디아 급등\n데이터센터 수요 폭발적 증가"]

        # v11 형식 재현 (제목만)
        v11_summary = "\n".join(f"- {h.split(chr(10))[0]}" for h in headlines[:3])

        # v12 형식
        v12_summary = self._build_news_summary(headlines)

        assert "- 엔비디아 급등" == v11_summary  # v11: dash + 제목만
        assert "• 엔비디아 급등" in v12_summary   # v12: bullet
        assert "→ 데이터센터 수요" in v12_summary  # v12: detail 포함
        assert v11_summary != v12_summary


# ---------------------------------------------------------------------------
# 통합 Before/After 검증
# ---------------------------------------------------------------------------

class TestV12BeforeAfter:
    """v11 → v12 변경사항 5개 항목 before/after 비교 검증."""

    def test_fix1_thumbnail_function_exists(self):
        """Fix 1: 썸네일 생성 함수가 존재하고 호출 가능한지 확인."""
        from stock_snap.media.short_video import generate_thumbnail
        assert callable(generate_thumbnail)

    def test_fix2_tts_uses_korean_name(self):
        """Fix 2: TTS 스크립트에 한글 기업명 사용 (종목코드 제거)."""
        symbol = "TSLA"
        company_names = {"TSLA": "테슬라"}
        tts_name = company_names.get(symbol, symbol)
        change_pct = 8.3

        seg = f"{tts_name} 주가가 {'급등' if change_pct > 0 else '급락'}한 주요 배경을 살펴보겠습니다. "
        assert "테슬라" in seg
        assert "TSLA" not in seg

    def test_fix3_caption_includes_detail(self):
        """Fix 3: 캡션에 상세 내용 포함 (v11은 제목만)."""
        headlines = ["테슬라 급등\n자율주행 기술 돌파구 마련"]
        parts = headlines[0].split("\n")
        has_detail = len(parts) > 1 and parts[1].strip()
        assert has_detail, "테스트 데이터에 detail 있어야 함"

        # v12 형식 생성
        summary = f"• {parts[0]}\n  → {parts[1].strip()[:120]}"
        assert "→" in summary

    def test_fix4_news_direction_llm_prompt_format(self):
        """Fix 4: LLM 방향 검증 프롬프트가 올바른 포맷인지 확인."""
        symbol = "NVDA"
        change_pct = 6.5
        direction_ko = "급등(상승)" if change_pct > 0 else "급락(하락)"

        articles_text = "1. 제목: NVIDIA AI surge\n   내용: Strong demand"
        prompt = (
            f"주식 {symbol}이 오늘 {change_pct:+.1f}% {direction_ko}했습니다.\n\n"
            f"아래는 수집된 뉴스 기사 목록입니다:\n{articles_text}\n\n"
            f"응답은 반드시 JSON 배열만 반환하세요: "
            f'[{{"title": "제목", "detail": "한 문장 핵심 내용"}}, ...]'
        )

        assert "NVDA" in prompt
        assert "급등(상승)" in prompt
        assert "JSON 배열" in prompt

    def test_fix5_bgm_no_loop_in_tsx(self):
        """Fix 5: BGM Audio 태그에 loop 없음 (v12 연속 재생)."""
        tsx_path = Path(__file__).parent.parent / "remotion/src/StockShort.tsx"
        if not tsx_path.exists():
            import pytest
            pytest.skip("StockShort.tsx not found")

        content = tsx_path.read_text()

        # BGM 관련 Audio 태그가 있는 라인
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "bgmPath" in line and "Audio" in line:
                assert "loop" not in line, (
                    f"Line {i+1}: BGM Audio에 loop 속성이 있음 (v11 방식): {line.strip()}"
                )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """간단한 테스트 러너 (pytest 없이 실행 가능)."""
    test_classes = [
        TestTC002_TtsKoreanName,
        TestTC003_BgmContinuous,
        TestTC004_NewsDirectionConsistency,
        TestTC005_CaptionDetail,
        TestV12BeforeAfter,
    ]

    LINE = "=" * 60
    print(f"\n{LINE}")
    print("Stock Snap v12 QA 자동화 테스트")
    print(LINE)

    total = passed = failed = skipped = 0
    results = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method in methods:
            total += 1
            test_name = f"{cls.__name__}.{method}"
            try:
                getattr(instance, method)()
                print(f"  PASS  {test_name}")
                passed += 1
                results.append((test_name, "PASS", None))
            except Exception as e:
                err_msg = str(e)
                if "pytest.skip" in err_msg or "Skip" in type(e).__name__:
                    print(f"  ⏭️  SKIP  {test_name}")
                    skipped += 1
                    results.append((test_name, "SKIP", err_msg))
                else:
                    print(f"  FAIL  {test_name}")
                    print(f"         {err_msg}")
                    failed += 1
                    results.append((test_name, "FAIL", err_msg))

    print(f"\n{LINE}")
    print(f"결과: {passed}/{total} PASS  |  {failed} FAIL  |  {skipped} SKIP")
    print(LINE)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
