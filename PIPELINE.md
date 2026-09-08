# Stock Pilot — Content Pipeline Guide

End-to-end process for generating short-form stock analysis videos and uploading to Instagram Reels.

## Architecture Overview

```
Hot Stock Selection → Quant Analysis → News Collection → Content Generation → Video Rendering → Upload
     (yfinance)        (pandas-ta)      (Finnhub/RSS)    (Claude API/Template)  (Remotion)    (Instagram)
```

## Agent Roles

| Agent | Role | Responsibility |
|-------|------|----------------|
| **CEO** (`9014cf52`) | Strategy | Coordinates pipeline, delegates tasks, reviews results |
| **CTO** (`bf374a0e`) | Architecture | System design, code reviews, technical decisions |
| **Video Designer** (`8ae29418`) | Production | Remotion template design, video rendering, upload execution |
| **Market Analyst** (`2a12958a`) | Research | Hot stock selection logic, news analysis, market sentiment |
| **Quant Analyst** (`38c427d1`) | Analysis | Technical indicators (RSI, MACD, BB, SMA/EMA), forecast models |

## Pipeline Steps

### 1. Hot Stock Selection
- **Module**: `src/stock_pilot/hot_stock.py`
- **Owner**: Market Analyst
- Scans 40+ US stocks (S&P 500 representatives + thematic stocks)
- Composite scoring: price change % (max 50pts) + volume spike ratio (max 50pts)
- 20-day average volume as baseline

### 2. Quant Analysis
- **Module**: `src/stock_pilot/analysis/indicators.py`
- **Owner**: Quant Analyst
- Computes: RSI(14), MACD(12/26/9), Bollinger Bands(20/2σ), SMA(5/20/60), EMA(9/21/50)
- Pivot points, 20-day trendline, golden/death cross detection
- Volume spike detection

### 3. News Collection
- **Module**: `src/stock_pilot/news/collector.py`
- **Owner**: Market Analyst
- Sources: Finnhub, Alpha Vantage, SEC EDGAR, Yahoo Finance RSS
- Lookback: 24 hours
- Sentiment analysis via `src/stock_pilot/news/sentiment.py`

### 4. Content Generation
- **Module**: `src/stock_pilot/content/generator.py`
- Two modes:
  - **Claude API mode**: Full AI-generated narration, captions, card news (requires `ANTHROPIC_API_KEY`)
  - **Template mode**: Pre-built templates using quant data (no API key needed, used in `run_live_short.py`)

### 5. Media Production
- **Card News**: `src/stock_pilot/media/card_news.py` — Static image with stock data overlay
- **TTS**: `src/stock_pilot/media/tts.py` — Edge TTS narration
- **Video**: `src/stock_pilot/media/short_video.py` — 30-second Remotion render
- **Owner**: Video Designer
- Remotion project: `remotion/` (Node.js, React-based animation)

### 6. Upload
- **Instagram**: `src/stock_pilot/upload/instagram.py`
  - Video → GitHub Release asset (public URL) → Instagram Graph API (Reels container → poll → publish)
  - Public URL host: `src/stock_pilot/upload/media_host.py` — release asset on CI, catbox.moe fallback locally
  - Requires: `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` in `.env`
- **YouTube** (Phase 2): `src/stock_pilot/upload/youtube.py`

## Running the Pipeline

All paths below are relative to the repository root.

### CLI (full pipeline with Claude API)
```bash
.venv/bin/stock-pilot content --hot --upload
```

### Template mode (no API key)
```bash
.venv/bin/python run_live_short.py

# generate only, skip uploads
.venv/bin/python run_live_short.py --dry-run
```

### Scheduled runs — GitHub Actions only
Scheduling lives entirely in `.github/workflows/`. **Local cron is not used**; running
both would publish the same content twice.

| Workflow | Schedule (UTC) | KST | Script |
|----------|----------------|-----|--------|
| `daily-short.yml` | `30 0 * * 1-5` | 평일 09:30 | `run_live_short.py` |
| `aftermarket.yml` | `15 21 * * 1-5` | 평일 06:15 (익일) | `run_aftermarket.py` |
| `weekly-review.yml` | `30 21 * * 5` | 토요일 06:30 | `run_weekly_review.py` |

- Manual trigger: `gh workflow run daily-short.yml -f dry_run=true`
- Logs: the workflow run itself (`gh run view --log`); on failure the `output/` directory
  is uploaded as an artifact and a Kakao message is sent.
- Schedules are auto-disabled by GitHub after 60 days of repository inactivity —
  check with `gh workflow list --all`, re-enable with `gh workflow enable <file>`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `INSTAGRAM_USER_ID` | Yes | Instagram Business account ID |
| `INSTAGRAM_ACCESS_TOKEN` | Yes | Meta system user permanent token |
| `ANTHROPIC_API_KEY` | For CLI mode | Claude API key for AI content generation |
| `FINNHUB_API_KEY` | Optional | Finnhub news API |
| `ALPHA_VANTAGE_API_KEY` | Optional | Alpha Vantage news API |

## Output

- Videos: `output/{SYMBOL}_{timestamp}_short.mp4`
- Card images: `output/{SYMBOL}_{timestamp}_card.png`
- TTS audio: `output/{SYMBOL}_{timestamp}_tts.mp3`
- Cron logs: `output/cron.log`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `npx not found` | Install Node.js (`nvm install 22`) |
| Remotion render fails | `cd remotion && npm install` |
| Instagram upload fails | Check token validity in `.env` |
| Hot stock returns None | Market may be closed; try during trading hours |
| Release asset upload fails (403) | The job needs `permissions: contents: write` and `GITHUB_TOKEN` in the step env |
| catbox.moe returns 412 | Expected on CI — catbox blocks runner IP ranges; the release host is used there instead |
