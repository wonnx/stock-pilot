# Stock Pilot

Automated US stock analysis and short-form video content pipeline for Instagram Reels. Selects the hottest stock of the day, generates quant-driven analysis, and produces a 30-second narrated video — all fully automated.

## Features

- **Hot Stock Selection** — Scans 40+ US stocks (S&P 500, tech, fintech, biotech) by combining price change % and volume spike ratio into a composite "hot score"
- **Technical Analysis** — RSI, MACD, Bollinger Bands, SMA 5/20/60, EMA 9/21/50, pivot points, trendline fitting, support/resistance
- **AI Content Generation** — Claude API generates analysis text, narration script, and captions with quant perspective
- **Card News** — Puppeteer-rendered infographic images
- **Short-Form Video** — 30-second Remotion-rendered video with animated chart, quant gauge, motion graphics, and TTS narration
- **Instagram Reels Upload** — Automated upload via Instagram Graph API (system user permanent token)
- **News Aggregation** — Finnhub, Alpha Vantage, SEC EDGAR, Yahoo Finance RSS

## Architecture

```
Hot Stock Selection (yfinance)
        │
        ├── Quant Analysis (pandas-ta)
        │       RSI · MACD · Bollinger · SMA/EMA · Pivot · Trendline
        │
        ├── News Collection (Finnhub, Alpha Vantage, SEC, Yahoo RSS)
        │       Sentiment analysis
        │
        └── AI Content Generation (Claude API)
                │
                ├── Card News (Puppeteer)
                ├── TTS Narration (edge-tts / ElevenLabs)
                └── 30s Video (Remotion)
                        │
                        └── Instagram Reels Upload (Graph API)
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for Remotion video rendering)
- Chromium (for Puppeteer card news)

### Installation

```bash
git clone https://github.com/wonnx/stock-pilot.git
cd stock-pilot

# Python dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Remotion dependencies
cd remotion && npm install && cd ..
```

### Configuration

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

**Required:**
| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key for content generation |
| `INSTAGRAM_ACCESS_TOKEN` | Facebook system user permanent token |
| `INSTAGRAM_USER_ID` | Instagram business account ID |

**Optional:**
| Variable | Description |
|---|---|
| `FINNHUB_API_KEY` | Finnhub news API |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage data API |
| `KAKAO_ACCESS_TOKEN` | KakaoTalk alert token |
| `ELEVENLABS_API_KEY` | ElevenLabs TTS (defaults to edge-tts) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 |

## Usage

### Generate content for the hottest stock

```bash
# Dry run (generate only, no upload)
stock-pilot content --hot --dry-run

# Generate and upload to Instagram Reels
stock-pilot content --hot --upload
```

### Generate content for specific symbols

```bash
stock-pilot content NVDA TSLA --upload
```

### Market scan

```bash
# Scan watchlist for trade signals
stock-pilot scan

# Dry run (no alerts)
stock-pilot scan --dry-run
```

### Backtest

```bash
# Backtest all watchlist symbols
stock-pilot backtest

# Backtest a single symbol
stock-pilot backtest NVDA
```

### Watchlist management

```bash
stock-pilot watchlist                    # Show current watchlist
stock-pilot watchlist --add SOFI PLTR    # Add symbols
stock-pilot watchlist --remove INTC      # Remove symbols
```

### Scheduled posting (GitHub Actions)

Scheduled publishing runs **only** on GitHub Actions. Do not add a local cron job —
running both double-posts to the same accounts.

| Workflow | Schedule (UTC) | KST | Script |
|---|---|---|---|
| `daily-short.yml` | `30 0 * * 1-5` | 평일 09:30 | `run_live_short.py` |
| `aftermarket.yml` | `15 21 * * 1-5` | 평일 06:15 (익일) | `run_aftermarket.py` |
| `weekly-review.yml` | `30 21 * * 5` | 토요일 06:30 | `run_weekly_review.py` |

Each run selects the hottest stock by volume spike + price change, runs quant analysis,
generates narration and video, and uploads to Instagram Reels (@stock.snap) + YouTube Shorts.

Secrets are configured under **Settings → Secrets and variables → Actions**; the required
names are the env keys listed in each workflow's `Run pipeline` step.

Manual run (including a no-upload dry run):

```bash
gh workflow run daily-short.yml -f dry_run=true    # generate only
gh workflow run daily-short.yml                    # generate and publish
gh run watch
```

If a scheduled workflow stops firing, check that it is still enabled — GitHub auto-disables
schedules after 60 days without repository activity:

```bash
gh workflow list --all
gh workflow enable daily-short.yml
```

## Project Structure

```
stock-pilot/
├── src/stock_pilot/
│   ├── cli.py                 # CLI entry point
│   ├── hot_stock.py           # Hot stock selection (volume + price scoring)
│   ├── scanner.py             # Market scanner
│   ├── analysis/
│   │   └── indicators.py      # Technical indicators (RSI, MACD, BB, SMA, pivot, trendline)
│   ├── content/
│   │   ├── generator.py       # AI content generation (Claude API)
│   │   └── pipeline.py        # Full pipeline orchestrator
│   ├── data/
│   │   ├── fetcher.py         # yfinance data fetcher
│   │   └── watchlist.py       # Watchlist management
│   ├── media/
│   │   ├── card_news.py       # Puppeteer card news generator
│   │   ├── short_video.py     # Remotion video renderer
│   │   └── tts.py             # TTS (edge-tts / ElevenLabs)
│   ├── news/
│   │   ├── collector.py       # Multi-source news aggregation
│   │   └── sentiment.py       # Sentiment analysis
│   ├── upload/
│   │   ├── instagram.py       # Instagram Graph API (photo + Reels)
│   │   └── youtube.py         # YouTube Shorts upload
│   ├── alerts/
│   │   ├── kakao.py           # KakaoTalk alerts
│   │   └── telegram.py        # Telegram alerts
│   ├── signals/
│   │   └── scorer.py          # Trade signal scoring
│   ├── backtest/
│   │   └── engine.py          # Backtesting engine
│   └── utils/
│       └── config.py          # Environment config loader
├── remotion/                   # Remotion video templates
│   └── src/
│       ├── Root.tsx
│       └── StockShort.tsx     # 30s short-form video template
├── tests/                     # Test suite
├── output/                    # Generated content output
├── pyproject.toml
└── .env.example
```

## Technical Indicators

| Indicator | Description | Usage |
|---|---|---|
| RSI (14) | Relative Strength Index | Overbought (>70) / Oversold (<30) |
| MACD (12/26/9) | Moving Average Convergence Divergence | Trend momentum |
| Bollinger Bands (20, 2σ) | Volatility bands | Squeeze detection, band position |
| SMA 5/20/60 | Simple Moving Averages | Trend alignment, golden cross |
| EMA 9/21/50 | Exponential Moving Averages | Short-term trend |
| Pivot Points | Classic H/L/C pivot | Support/Resistance levels |
| Trendline | 20-day linear regression | Trend direction and strength (R²) |
| Volume Ratio | Current vs 20-day avg volume | Volume spike detection (>2x) |

## Testing

```bash
# Unit tests (no secrets required)
pytest
pytest --cov=stock_pilot

# E2E dry-run — full pipeline with mock fixtures, no API keys needed
pytest tests/test_e2e_dry_run.py -v
# or via npm script:
pnpm test:e2e:dry-run
```

### E2E Dry-Run

`tests/test_e2e_dry_run.py` validates the complete pipeline flow end-to-end using mock fixtures:

| What is mocked | Why |
|---|---|
| `select_hot_stock()` | replaces yfinance live data |
| `MarketDataFetcher.get_ohlcv()` | replaces yfinance OHLCV download |
| `NewsCollector.fetch_for_symbol()` | replaces Finnhub + Alpha Vantage API calls |
| `generate_tts_with_timing()` / `generate_tts()` | replaces edge-tts / OpenAI TTS |
| `generate_short_video()` / `generate_thumbnail()` | replaces Remotion render |
| `publish_media()` | replaces the public-URL upload (GitHub Release asset / catbox) |

Fixture JSON files live in `tests/fixtures/`:
- `finnhub_news.json` — sample Finnhub company-news API response
- `alphavantage_news.json` — sample Alpha Vantage news sentiment API response

## License

Private — © 2026 wonnx
