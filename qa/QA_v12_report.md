# v12 QA 검증 보고서 — Before/After 비교

> 작성일: 2026-03-12
> 담당: QA Engineer
> 비교 범위: v11 (커밋 d4e5f39) → v12 (커밋 81ec333)
> 변경 파일: `run_live_short.py`, `remotion/src/StockShort.tsx`

---

## 요약

| # | 수정 항목 | Before (v11) | After (v12) | TC | 결과 |
|---|-----------|-------------|------------|-----|------|
| 1 | 썸네일 누락 | v7에서 수정됨 | 유지 | TC-001 | ✅ |
| 2 | TTS 종목코드→한글 | 티커(NVDA) 읽음 | 한글명(엔비디아) 읽음 | TC-002 | ✅ |
| 3 | 캡션 상세화 | 제목만 표시 | 제목 + 상세내용 | TC-005 | ✅ |
| 4 | 뉴스 분석 정확도 | yfinance 단일 소스, 방향 미검증 | 다중 소스 + LLM 방향 검증 | TC-004 | ✅ |
| 5 | BGM 연속 재생 | Sequence+loop (반복 끊김) | 직접 Audio 태그 (연속 재생) | TC-003 | ✅ |

**자동화 테스트 결과: 26/26 PASS**

---

## 상세 Before/After 분석

### Fix 1: 썸네일 누락 (v7에서 이미 수정됨)

| | Before (v7 이전) | After (현재 v12) |
|--|-----------------|-----------------|
| 함수 | 없음 | `generate_thumbnail()` 존재 |
| 파일 | `short_video.py` | `short_video.py:11` |
| 처리 | 썸네일 없음 | Remotion Still 렌더링 |

**v12 상태**: `generate_thumbnail()` 함수가 `src/stock_pilot/media/short_video.py:11`에 정상 존재.
TC-001 자동화는 부분적 (Node.js 환경 필요). 함수 존재 여부는 TC-001 smoke test로 확인 완료.

---

### Fix 2: TTS 종목코드 → 한글 기업명

**코드 변경** (`run_live_short.py`):

```python
# v11 (bug)
intro = f"{symbol} 주가가 {'급등' if change_pct > 0 else '급락'}한..."
# → "NVDA 주가가 급등한..."

# v12 (fixed)
intro = f"{tts_name} 주가가 {'급등' if change_pct > 0 else '급락'}한..."
# → "엔비디아 주가가 급등한..."
```

동일 패턴이 `seg_news` fallback 텍스트(line 246)에도 적용됨.

**TC-002 결과**: 26개 테스트 모두 PASS
- `tts_name = COMPANY_NAMES_KO.get(symbol, symbol)` 로직 정상
- 미등록 종목은 티커로 fallback (정상 동작)
- seg_news 인트로/fallback 모두 한글명 사용 확인

---

### Fix 3: 캡션 상세화

**코드 변경** (`run_live_short.py`):

```python
# v11 (제목만)
news_summary = "\n".join(f"- {h.split(chr(10))[0]}" for h in news_headlines[:3])
# 출력: "- 엔비디아 AI 수요 급증"

# v12 (제목 + 상세)
for h in news_headlines[:3]:
    parts = h.split("\n")
    title_part = parts[0]
    detail_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""
    if detail_part:
        news_summary_items.append(f"• {title_part}\n  → {detail_part[:120]}")
    else:
        news_summary_items.append(f"• {title_part}")
# 출력:
# "• 엔비디아 AI 수요 급증
#    → 데이터센터 매출 전년비 200% 성장"
```

**TC-005 결과**: 6/6 PASS
- 불릿(•) 형식 적용 확인
- detail 120자 truncation 확인
- v11 dash(-) 형식과 명확히 구분됨

---

### Fix 4: 뉴스 분석 정확도 (다중 소스 + LLM 방향 검증)

**주요 변경**:
1. **다중 소스 수집**: yfinance(10개) + NewsCollector(8개), 중복 제거
2. **LLM 방향 검증**: Claude Haiku를 사용해 주가 방향에 맞는 뉴스만 선별
3. **한국어 재작성**: 영문 뉴스를 번역 대신 LLM이 직접 한국어로 재작성

**TC-004 결과**: 5/5 PASS
- API 키 없을 때 원본 articles graceful fallback 확인
- LLM JSON 응답 파싱 로직 정상 (mock test)
- 중복 제거 로직 (소문자 비교) 정상 작동
- 최대 3개 아티클 반환 확인

**주의사항**: LLM 방향 검증은 `ANTHROPIC_API_KEY` 필요. 미설정 시 원본 번역 방식으로 자동 fallback.

---

### Fix 5: BGM 연속 재생

**코드 변경** (`remotion/src/StockShort.tsx`):

```tsx
// v11 (loop 반복 — 짧은 BGM에서 끊김 가능)
{bgmPath ? (
  <Sequence from={0} durationInFrames={durationInFrames}>
    <Audio src={staticFile(bgmPath)} volume={0.126} loop />
  </Sequence>
) : null}

// v12 (직접 전체 재생 — 끊김 없음)
{bgmPath ? (
  <Audio src={staticFile(bgmPath)} volume={0.126} />
) : null}
```

**TC-003 결과**: 3/3 PASS
- `loop` 속성 제거 확인
- `<Sequence>` 래퍼 없음 확인
- `volume={0.126}` (-18dB) 유지 확인

**주의사항**: BGM 파일 길이가 영상보다 짧으면 BGM이 중간에 끊길 수 있음.
현재 BGM: Scott Buckley Moonlight (충분히 긴 파일 사용 권장).

---

## 실제 영상 생성 검증

### 환경 의존성
영상 생성(`run_live_short.py`)은 다음 외부 환경이 필요합니다:

| 의존성 | 필요 이유 | 확인 방법 |
|--------|---------|---------|
| Node.js + Remotion | 영상 렌더링 | `npx remotion --version` |
| `edge-tts` 또는 OpenAI API | TTS 생성 | `uv run python -c "import edge_tts"` |
| `yfinance` API | 주가 데이터 | 인터넷 연결 필요 |
| `ANTHROPIC_API_KEY` | LLM 뉴스 분석 (선택) | 미설정 시 번역 fallback |
| `INSTAGRAM_ACCESS_TOKEN` | 업로드 (선택) | 미설정 시 업로드 건너뜀 |

### 영상 생성 실행 방법

```bash
cd /Users/jwkim/stock-pilot
uv run python run_live_short.py
```

### 검증 체크리스트 (수동)

영상 생성 후 아래 항목 육안 확인:

- [ ] 영상 파일 생성 (`output/*.mp4`)
- [ ] 썸네일 생성 (`output/*.jpg`)
- [ ] 영상 길이 25~35초
- [ ] TTS 나레이션에서 "엔비디아", "테슬라" 등 한글명 청취
- [ ] BGM이 영상 시작부터 끝까지 연속 재생
- [ ] 뉴스 자막에 제목 + 상세 내용 표시 (• 형식)
- [ ] 뉴스 내용이 주가 방향(급등/급락)과 일치

---

## 자동화 TC 실행 결과 (2026-03-12)

```
Stock Pilot v12 QA 자동화 테스트
============================================================
  ✅ PASS  TestTC002_TtsKoreanName.test_all_major_symbols_have_korean_name
  ✅ PASS  TestTC002_TtsKoreanName.test_seg_news_fallback_uses_tts_name
  ✅ PASS  TestTC002_TtsKoreanName.test_seg_news_uses_tts_name_not_symbol
  ✅ PASS  TestTC002_TtsKoreanName.test_tts_generate_function_exists
  ✅ PASS  TestTC002_TtsKoreanName.test_tts_name_fallback_to_ticker_for_unknown
  ✅ PASS  TestTC002_TtsKoreanName.test_tts_name_uses_korean_for_known_symbol
  ✅ PASS  TestTC002_TtsKoreanName.test_tts_returns_bool
  ✅ PASS  TestTC003_BgmContinuous.test_bgm_audio_tag_exists
  ✅ PASS  TestTC003_BgmContinuous.test_bgm_audio_without_loop
  ✅ PASS  TestTC003_BgmContinuous.test_bgm_no_sequence_wrapper
  ✅ PASS  TestTC004_NewsDirectionConsistency.test_fallback_when_empty_articles
  ✅ PASS  TestTC004_NewsDirectionConsistency.test_fallback_when_no_api_key
  ✅ PASS  TestTC004_NewsDirectionConsistency.test_llm_response_parsing
  ✅ PASS  TestTC004_NewsDirectionConsistency.test_llm_returns_max_3_articles
  ✅ PASS  TestTC004_NewsDirectionConsistency.test_news_deduplication
  ✅ PASS  TestTC005_CaptionDetail.test_news_summary_bullet_format
  ✅ PASS  TestTC005_CaptionDetail.test_news_summary_detail_truncated_at_120
  ✅ PASS  TestTC005_CaptionDetail.test_news_summary_includes_detail
  ✅ PASS  TestTC005_CaptionDetail.test_news_summary_max_3_items
  ✅ PASS  TestTC005_CaptionDetail.test_news_summary_no_detail
  ✅ PASS  TestTC005_CaptionDetail.test_v11_vs_v12_summary_format_difference
  ✅ PASS  TestV12BeforeAfter.test_fix1_thumbnail_function_exists
  ✅ PASS  TestV12BeforeAfter.test_fix2_tts_uses_korean_name
  ✅ PASS  TestV12BeforeAfter.test_fix3_caption_includes_detail
  ✅ PASS  TestV12BeforeAfter.test_fix4_news_direction_llm_prompt_format
  ✅ PASS  TestV12BeforeAfter.test_fix5_bgm_no_loop_in_tsx

결과: 26/26 PASS  |  0 FAIL  |  0 SKIP
```

---

## TC-006 Instagram 업로드 (수동 검증 필요)

TC-006은 `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_USER_ID` 환경 변수 설정이 필요하여
자동화 테스트에서 제외됩니다. 업로드 테스트는 배포 전 수동으로 진행 권장.

```bash
# 업로드 포함 E2E 테스트
uv run python tests/test_reels_e2e.py --upload --symbol NVDA
```

---

## 결론

v12 변경사항 5개 항목 모두 코드 레벨에서 수정 확인됨.
자동화 테스트 26개 전부 통과.
실제 영상 품질 검증(TC-001, TC-006)은 Node.js/Instagram 환경 구성 후 수동 실행 필요.
