import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
  Audio,
  staticFile,
} from 'remotion';

interface Props {
  symbol: string;
  price: number;
  changePct: number;
  direction: string;
  cardTitle: string;
  cardSubtitle: string;
  script: string;
  audioPath?: string;
  rsi?: number;
  macd?: number;
  macdSignal?: number;
  volumeRatio?: number;
  bbPosition?: string;      // "upper" | "middle" | "lower"
  emaTrend?: string;        // "bullish" | "bearish" | "mixed"
  quantSummary?: string;
  chartData?: number[];     // 최근 20일 종가
}

// ─── 색상 팔레트 ────────────────────────────────────────────────────────────
const BG = '#0a0e1a';
const SURFACE = '#111827';
const BORDER = '#1f2937';
const GREEN = '#10b981';
const RED = '#ef4444';
const YELLOW = '#f59e0b';
const GRAY = '#6b7280';
const WHITE = '#f9fafb';
const DIM = '#9ca3af';

// ─── RSI 게이지 ─────────────────────────────────────────────────────────────
const RsiGauge: React.FC<{ rsi: number; frame: number }> = ({ rsi, frame }) => {
  const color = rsi >= 70 ? RED : rsi <= 30 ? GREEN : YELLOW;
  const label = rsi >= 70 ? '과매수' : rsi <= 30 ? '과매도' : '중립';
  const pct = Math.min(Math.max(rsi / 100, 0), 1);
  const barWidth = interpolate(frame, [0, 30], [0, pct * 200], { extrapolateRight: 'clamp' });

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 20, color: DIM, marginBottom: 4 }}>
        <span>RSI(14)</span>
        <span style={{ color, fontWeight: 700 }}>{rsi.toFixed(1)} <span style={{ fontSize: 16 }}>{label}</span></span>
      </div>
      <div style={{ height: 6, background: BORDER, borderRadius: 3 }}>
        <div style={{ height: 6, width: barWidth, background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
};

// ─── 미니 차트 ──────────────────────────────────────────────────────────────
const MiniChart: React.FC<{ data: number[]; frame: number; color: string }> = ({ data, frame, color }) => {
  if (!data || data.length < 2) return null;

  const w = 880;
  const h = 120;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h * 0.85 - h * 0.075;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const progress = interpolate(frame, [0, 40], [0, 1], { extrapolateRight: 'clamp' });
  const clipWidth = progress * w;
  const lastPt = points[points.length - 1].split(',');

  return (
    <svg width={w} height={h} style={{ overflow: 'visible' }}>
      <defs>
        <clipPath id="chartClip">
          <rect x={0} y={0} width={clipWidth} height={h} />
        </clipPath>
        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((v, i) => (
        <line key={i} x1={0} y1={h * v} x2={w} y2={h * v} stroke={BORDER} strokeWidth={1} />
      ))}
      <polygon
        points={`0,${h} ${points.join(' ')} ${w},${h}`}
        fill="url(#chartGrad)"
        clipPath="url(#chartClip)"
      />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeLinejoin="round"
        clipPath="url(#chartClip)"
      />
      {progress > 0.95 && (
        <circle cx={Number(lastPt[0])} cy={Number(lastPt[1])} r={5} fill={color} />
      )}
    </svg>
  );
};

// ─── MACD 뱃지 ──────────────────────────────────────────────────────────────
const MacdBadge: React.FC<{ macd: number; signal: number }> = ({ macd, signal }) => {
  const bullish = macd > signal;
  const color = bullish ? GREEN : RED;
  const label = bullish ? 'MACD ↑ 골든크로스' : 'MACD ↓ 데드크로스';
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center',
      background: `${color}18`, border: `1px solid ${color}44`,
      borderRadius: 8, padding: '6px 16px', fontSize: 20, color,
    }}>
      {label}
    </div>
  );
};

// ─── 메인 컴포넌트 ──────────────────────────────────────────────────────────
export const StockShort: React.FC<Props> = ({
  symbol,
  price,
  changePct,
  cardTitle,
  cardSubtitle,
  audioPath = '',
  rsi = 50,
  macd = 0,
  macdSignal = 0,
  volumeRatio = 1,
  bbPosition = 'middle',
  emaTrend = 'mixed',
  chartData = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const accentColor = changePct > 0 ? GREEN : changePct < 0 ? RED : YELLOW;
  const sign = changePct > 0 ? '▲' : changePct < 0 ? '▼' : '■';

  // 씬1 (0~3s): 헤더 + 가격
  const headerOpacity = spring({ frame, fps, from: 0, to: 1, config: { damping: 18, stiffness: 80 } });
  const priceY = interpolate(frame, [0, 15], [30, 0], { extrapolateRight: 'clamp' });

  // 씬2 (3~8s): 차트
  const chartOpacity = interpolate(frame, [fps * 3, fps * 3 + 15], [0, 1], { extrapolateRight: 'clamp' });

  // 씬3 (8~20s): 퀀트 패널
  const quantOpacity = interpolate(frame, [fps * 8, fps * 8 + 20], [0, 1], { extrapolateRight: 'clamp' });
  const quantY = interpolate(frame, [fps * 8, fps * 8 + 20], [20, 0], { extrapolateRight: 'clamp' });

  // 씬4 (20~30s): 결론
  const conclusionOpacity = interpolate(frame, [fps * 20, fps * 20 + 15], [0, 1], { extrapolateRight: 'clamp' });

  const bbColor = bbPosition === 'upper' ? RED : bbPosition === 'lower' ? GREEN : YELLOW;
  const bbLabel = bbPosition === 'upper' ? '상단 돌파' : bbPosition === 'lower' ? '하단 지지' : '중간대';
  const volColor = volumeRatio >= 2 ? RED : volumeRatio >= 1.5 ? YELLOW : GREEN;

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: "'Noto Sans KR', sans-serif", overflow: 'hidden' }}>

      {audioPath && <Audio src={staticFile(audioPath)} />}

      {/* 배경 글로우 */}
      <div style={{
        position: 'absolute', top: -200, left: -200,
        width: 600, height: 600,
        background: `radial-gradient(circle, ${accentColor}18 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      {/* ══ 씬1: 브랜드 + 가격 ═══════════════════════════════════════════ */}
      <div style={{ opacity: headerOpacity }}>
        <div style={{
          position: 'absolute', top: 60, left: 60,
          fontSize: 22, color: GRAY, letterSpacing: 6, fontWeight: 600,
        }}>
          STOCK·SNAP
        </div>

        <div style={{
          position: 'absolute', top: 130, left: 60,
          transform: `translateY(${priceY}px)`,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
            <span style={{ fontSize: 88, fontWeight: 900, color: WHITE, letterSpacing: -2 }}>{symbol}</span>
          </div>
          <div style={{ fontSize: 64, fontWeight: 700, color: WHITE, marginTop: 4 }}>
            ${price.toFixed(2)}
          </div>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 16,
            fontSize: 40, fontWeight: 800, color: accentColor,
            background: `${accentColor}15`,
            border: `2px solid ${accentColor}44`,
            borderRadius: 12, padding: '8px 24px',
          }}>
            {sign} {Math.abs(changePct).toFixed(2)}%
          </div>
        </div>

        {/* EMA 추세 뱃지 */}
        <div style={{
          position: 'absolute', top: 130, right: 60,
          fontSize: 20, fontWeight: 700,
          color: emaTrend === 'bullish' ? GREEN : emaTrend === 'bearish' ? RED : YELLOW,
          background: SURFACE, border: `1px solid ${BORDER}`,
          borderRadius: 10, padding: '8px 18px',
        }}>
          EMA {emaTrend === 'bullish' ? '▲ 상승추세' : emaTrend === 'bearish' ? '▼ 하락추세' : '◆ 혼조'}
        </div>
      </div>

      {/* ══ 씬2: 미니 차트 ═══════════════════════════════════════════════ */}
      <div style={{
        position: 'absolute', top: 430, left: 60, right: 60,
        opacity: chartOpacity,
      }}>
        <div style={{ fontSize: 20, color: GRAY, marginBottom: 8 }}>20일 가격 추이</div>
        <div style={{
          background: SURFACE, border: `1px solid ${BORDER}`,
          borderRadius: 16, padding: '20px 24px',
        }}>
          <MiniChart data={chartData} frame={frame - fps * 3} color={accentColor} />
        </div>
      </div>

      {/* ══ 씬3: 퀀트 지표 ═══════════════════════════════════════════════ */}
      <Sequence from={fps * 8} durationInFrames={fps * 22}>
        <div style={{
          position: 'absolute', top: 690, left: 60, right: 60,
          opacity: quantOpacity,
          transform: `translateY(${quantY}px)`,
        }}>
          <div style={{
            background: SURFACE, border: `1px solid ${BORDER}`,
            borderRadius: 20, padding: '28px 32px',
          }}>
            <RsiGauge rsi={rsi} frame={frame - fps * 8} />
            <div style={{ display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' }}>
              <MacdBadge macd={macd} signal={macdSignal} />
              <div style={{
                display: 'inline-flex', alignItems: 'center',
                background: `${bbColor}18`, border: `1px solid ${bbColor}44`,
                borderRadius: 8, padding: '6px 16px', fontSize: 20, color: bbColor,
              }}>
                BB {bbLabel}
              </div>
              <div style={{
                display: 'inline-flex', alignItems: 'center',
                background: `${volColor}18`, border: `1px solid ${volColor}44`,
                borderRadius: 8, padding: '6px 16px', fontSize: 20, color: volColor,
              }}>
                거래량 {volumeRatio.toFixed(1)}x
              </div>
            </div>
          </div>
        </div>
      </Sequence>

      {/* ══ 씬4: 결론 카드 ═══════════════════════════════════════════════ */}
      <Sequence from={fps * 20} durationInFrames={fps * 10}>
        <div style={{
          position: 'absolute', top: 990, left: 60, right: 60,
          opacity: conclusionOpacity,
        }}>
          <div style={{
            background: `linear-gradient(135deg, ${accentColor}15, ${SURFACE})`,
            border: `1px solid ${accentColor}44`,
            borderRadius: 20, padding: '28px 32px',
          }}>
            <div style={{ fontSize: 40, fontWeight: 900, color: WHITE, marginBottom: 8 }}>
              {cardTitle}
            </div>
            <div style={{ fontSize: 26, color: DIM, lineHeight: 1.5 }}>
              {cardSubtitle}
            </div>
          </div>
        </div>
      </Sequence>

      {/* 면책고지 */}
      <div style={{
        position: 'absolute', bottom: 28, left: 0, right: 0,
        textAlign: 'center', fontSize: 18, color: `${GRAY}88`,
      }}>
        본 콘텐츠는 투자 조언이 아닙니다.
      </div>
    </AbsoluteFill>
  );
};
