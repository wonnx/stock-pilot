# Stock Snap 숏폼 영상 파이프라인 — Test Case 체계

> 작성일: 2026-03-12
> 대상 버전: v12 (커밋 81ec333)

---

## TC-001 썸네일 검증

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-001 |
| **카테고리** | 썸네일 생성 |
| **목적** | 영상 생성 후 썸네일 이미지가 정상적으로 존재하는지 확인 |
| **관련 파일** | `src/stock_snap/media/short_video.py:generate_thumbnail()` |

### 사전 조건
- Node.js + `npx remotion` 설치됨
- `remotion/` 디렉토리 존재

### 테스트 단계
1. `generate_thumbnail(pkg, output_path)` 호출
2. 반환값 `True` 확인
3. `output_path` 파일 존재 여부 확인
4. 파일 크기 > 10KB 확인 (빈 파일이 아님)

### 합격 기준 (Pass Criteria)
- [ ] 반환값이 `True`
- [ ] `output_path` 파일 생성됨
- [ ] 파일 크기 > 10KB
- [ ] JPEG 포맷 (magic bytes: `FF D8 FF`)

### 실패 원인 추적
- `npx not found` → Node.js 미설치
- `Remotion still render failed` → Remotion 빌드 오류
- 반환값 `True`지만 파일 없음 → `output_path.exists()` 검사 우회 버그

---

## TC-002 TTS 종목코드 → 한글 이름 검증

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-002 |
| **카테고리** | TTS 음성 출력 |
| **목적** | TTS 스크립트에서 종목코드(티커) 대신 한글 기업명이 읽히는지 확인 |
| **관련 파일** | `run_live_short.py` (line 232, 246), `src/stock_snap/media/tts.py` |

### 사전 조건
- `COMPANY_NAMES_KO` 딕셔너리에 테스트 종목 등록됨 (예: NVDA → "엔비디아")

### 테스트 단계
1. `run_live_short.py` 내 `tts_name` 변수 확인 (`COMPANY_NAMES_KO.get(symbol, symbol)`)
2. `seg_news` 변수에 `tts_name` 이 포함되어 있는지 확인
3. TTS 생성된 MP3 파일을 STT로 역변환하여 한글 기업명 등장 확인 (optional)

### 테스트 케이스 매트릭스

| 입력 종목 | 기대 TTS 읽기 | 비고 |
|-----------|--------------|------|
| NVDA | "엔비디아 주가가..." | 딕셔너리 존재 |
| AAPL | "애플 주가가..." | 딕셔너리 존재 |
| XYZ | "XYZ 주가가..." | 딕셔너리 미등록 → 티커 fallback |

### 합격 기준 (Pass Criteria)
- [ ] `tts_name` = `"엔비디아"` (NVDA 입력 시)
- [ ] `seg_news` 텍스트에 `"NVDA"` 가 없고 `"엔비디아"` 포함됨
- [ ] `seg_news` fallback 텍스트에도 `"NVDA"` 없음 (line 246 수정 확인)
- [ ] TTS MP3 파일 생성 성공

### v12 수정 내용 (Before/After)
- **v11**: `f"{symbol} 주가가 급등/급락한..."` → 티커 읽음
- **v12**: `f"{tts_name} 주가가 급등/급락한..."` → 한글 기업명 읽음

---

## TC-003 BGM 연속 재생 검증

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-003 |
| **카테고리** | BGM / 오디오 |
| **목적** | BGM이 영상 전구간에서 끊김 없이 재생되는지 확인 |
| **관련 파일** | `remotion/src/StockShort.tsx` (line 610-613) |

### 사전 조건
- BGM 파일(`*.mp3`)이 `remotion/public/` 에 존재
- BGM 파일 길이 ≥ 영상 총 길이

### 테스트 단계
1. Remotion 컴포넌트 코드에서 BGM Audio 태그 확인
2. 생성된 영상의 오디오 트랙 스펙트럼 분석 (ffprobe/ffmpeg)
3. 영상 시작~끝 구간에서 BGM 음량 레벨 확인

### 합격 기준 (Pass Criteria)
- [ ] `<Audio src={staticFile(bgmPath)} volume={0.126} />` 형태 (loop 없음)
- [ ] `<Sequence>` 래퍼 없이 전체 영상 지속
- [ ] 영상 파일 내 BGM 오디오 채널 존재
- [ ] 장면 전환 시점에서 오디오 불연속성 없음

### v12 수정 내용 (Before/After)
- **v11**: `<Sequence from={0} durationInFrames={durationInFrames}><Audio ... loop /></Sequence>`
  - `loop=true`로 짧은 BGM 반복 시 미세한 끊김 발생 가능
- **v12**: `<Audio src={staticFile(bgmPath)} volume={0.126} />`
  - loop 제거 → BGM 파일 원본 길이만큼 한 번만 재생, 끊김 없음

### 주의사항
- BGM 파일이 영상보다 짧으면 BGM이 중간에 끊길 수 있음
- 현재 사용 BGM (Scott Buckley Moonlight): 커밋 8149ad9에서 교체됨

---

## TC-004 뉴스 일관성 검증 (LLM 방향 검증)

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-004 |
| **카테고리** | 뉴스 분석 / 콘텐츠 일관성 |
| **목적** | 제목(급등/급락)과 표시 뉴스 내용의 방향이 일치하는지 확인 |
| **관련 파일** | `run_live_short.py:analyze_news_direction()` |

### 사전 조건
- `ANTHROPIC_API_KEY` 환경 변수 설정됨
- `anthropic` 패키지 설치됨

### 테스트 케이스

#### TC-004-A: 급등 종목 뉴스 일관성
- 입력: `change_pct = +5.0`, 혼재된 뉴스 (긍정/부정 혼합)
- 기대: LLM이 긍정 방향 뉴스만 선별 반환
- 검증: 반환된 뉴스 헤드라인에 "하락", "손실", "우려" 키워드가 없거나 최소화

#### TC-004-B: 급락 종목 뉴스 일관성
- 입력: `change_pct = -5.0`, 혼재된 뉴스
- 기대: LLM이 하락 방향 뉴스만 선별 반환
- 검증: 반환된 뉴스에 하락 원인 명시

#### TC-004-C: API 키 없을 때 fallback
- 입력: `ANTHROPIC_API_KEY` 미설정
- 기대: `analyze_news_direction()` 원본 articles 그대로 반환

#### TC-004-D: 다중 소스 수집 확인
- 검증: `raw_news`에 yfinance + NewsCollector 양쪽 소스 아티클이 혼합됨
- 중복 제거: 동일 제목 아티클이 중복 포함되지 않음 (소문자 비교)

### 합격 기준 (Pass Criteria)
- [ ] `analyze_news_direction()` JSON 파싱 성공
- [ ] 반환 아티클 수 1~3개 (max 3)
- [ ] 각 아티클에 `title`, `detail` 모두 존재
- [ ] 제목/내용이 한국어로 작성됨
- [ ] API 실패 시 원본 articles 반환 (graceful fallback)

### v12 수정 내용 (Before/After)
- **v11**: yfinance만 사용, 영문 직번역, 방향 필터링 없음
- **v12**: yfinance + NewsCollector 다중 소스, LLM 방향 검증 및 한국어 재작성

---

## TC-005 자막/캡션 상세화 검증

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-005 |
| **카테고리** | 자막 / 캡션 품질 |
| **목적** | 뉴스 요약 캡션이 제목뿐 아니라 상세 내용(detail)을 포함하는지 확인 |
| **관련 파일** | `run_live_short.py` (line 284-296) |

### 테스트 단계
1. `news_summary` 변수 생성 로직 확인
2. 뉴스 헤드라인에 `\n` 구분자로 detail이 포함된 경우 `→ detail` 형식으로 출력 확인
3. 생성된 영상의 자막 텍스트 확인

### 합격 기준 (Pass Criteria)
- [ ] `news_summary`에 `•` 불릿 포인트 사용
- [ ] detail이 있는 뉴스: `• 제목\n  → detail` 형식
- [ ] detail이 없는 뉴스: `• 제목` 형식
- [ ] detail 최대 120자 truncation 적용

### v12 수정 내용 (Before/After)
- **v11**: `"- {h.split(chr(10))[0]}"` → 제목만 표시
- **v12**: `"• {title}\n  → {detail[:120]}"` → 제목 + 상세 내용 표시

---

## TC-006 Instagram 업로드 검증

| 항목 | 내용 |
|------|------|
| **TC ID** | TC-006 |
| **카테고리** | Instagram 업로드 |
| **목적** | 영상 파일이 Instagram Reels에 정상 업로드되는지 확인 |
| **관련 파일** | `src/stock_snap/upload/instagram.py` |

### 사전 조건 (환경 설정 필요)
- `INSTAGRAM_ACCESS_TOKEN` 환경 변수 설정
- `INSTAGRAM_USER_ID` 환경 변수 설정
- 공개 접근 가능한 영상 URL (catbox.moe 업로드 완료)

### 테스트 단계
1. `upload_to_catbox()` 로 영상을 CDN에 업로드
2. 반환된 URL 유효성 확인 (`https://` 시작)
3. `instagram.upload_reel(video_url, caption)` 호출
4. 응답 container_id, publish_id 확인

### 합격 기준 (Pass Criteria)
- [ ] catbox 업로드 성공 → URL 반환
- [ ] Instagram media container 생성 성공
- [ ] media_publish 성공 → post_id 반환
- [ ] Instagram 피드에서 영상 조회 가능

### 경고 케이스 (Warning — 테스트 건너뜀)
- `INSTAGRAM_ACCESS_TOKEN` 미설정 → 업로드 건너뜀 (warning 로그)
- catbox 업로드 실패 → 업로드 불가 처리

---

## TC 실행 요약 시트

| TC ID | 이름 | 자동화 가능 | 환경 의존성 | 우선순위 |
|-------|------|------------|------------|---------|
| TC-001 | 썸네일 생성 | 부분 (파일 존재 확인) | Node.js, Remotion | High |
| TC-002 | TTS 한글 기업명 | 완전 자동화 | edge-tts 또는 OpenAI API | Critical |
| TC-003 | BGM 연속 재생 | 부분 (코드 검사) | ffprobe (심화) | High |
| TC-004 | 뉴스 방향 일관성 | 완전 자동화 | ANTHROPIC_API_KEY | High |
| TC-005 | 캡션 상세화 | 완전 자동화 | 없음 | Medium |
| TC-006 | Instagram 업로드 | 부분 (토큰 필요) | IG 계정 설정 | Low (수동 검증) |
