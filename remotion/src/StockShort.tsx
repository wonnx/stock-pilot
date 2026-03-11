import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
  Audio,
  staticFile,
  Easing,
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
const BG = '#080c18';
const SURFACE = '#0f1623';
const SURFACE2 = '#141d2e';
const BORDER = '#1e2d47';
const GREEN = '#00e5a0';
const RED = '#ff4d6d';
const YELLOW = '#ffd166';
const BLUE = '#4da6ff';
const GRAY = '#4a5a7a';
const WHITE = '#f0f4ff';
const DIM = '#8896b0';

// ─── 헬퍼: 부드러운 카운트업 ────────────────────────────────────────────────
const countUp = (
  frame: number,
  startFrame: number,
  durationFrames: number,
  from: number,
  to: number,
): number => {
  return interpolate(frame, [startFrame, startFrame + durationFrames], [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
};

// ─── 헬퍼: SVG smooth cubic bezier path ────────────────────────────────────
const smoothPath = (pts: [number, number][]): string => {
  if (pts.length < 2) return '';
  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i++) {
    const p0 = pts[i - 1];
    const p1 = pts[i];
    const cpx = p0[0] + (p1[0] - p0[0]) * 0.5;
    d += ` C ${cpx.toFixed(1)} ${p0[1].toFixed(1)}, ${cpx.toFixed(1)} ${p1[1].toFixed(1)}, ${p1[0].toFixed(1)} ${p1[1].toFixed(1)}`;
  }
  return d;
};

// ─── 미니 차트 컴포넌트 ──────────────────────────────────────────────────────
const AdvancedChart: React.FC<{
  data: number[];
  frame: number;
  color: string;
  width?: number;
  height?: number;
}> = ({ data, frame, color, width = 920, height = 300 }) => {
  if (!data || data.length < 2) return null;

  const pad = { top: 20, bottom: 40, left: 60, right: 20 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const pts: [number, number][] = data.map((v, i) => [
    pad.left + (i / (data.length - 1)) * innerW,
    pad.top + innerH - ((v - min) / range) * innerH,
  ]);

  // 애니메이션 진행도 (0→1)
  const progress = interpolate(frame, [0, 50], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const clipW = progress * (innerW + pad.left + pad.right);

  // 마지막 표시 포인트
  const lastVisibleIdx = Math.min(
    Math.floor(progress * (data.length - 1)),
    data.length - 1,
  );
  const lastPt = pts[lastVisibleIdx] ?? pts[pts.length - 1];

  // 그리드 가격 레이블
  const gridLevels = [0, 0.25, 0.5, 0.75, 1];
  const linePath = smoothPath(pts);
  const areaPath = `${linePath} L ${pts[pts.length - 1][0].toFixed(1)} ${(pad.top + innerH).toFixed(1)} L ${pad.left.toFixed(1)} ${(pad.top + innerH).toFixed(1)} Z`;

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      <defs>
        <clipPath id="chartClip">
          <rect x={0} y={0} width={clipW} height={height} />
        </clipPath>
        <linearGradient id="chartAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.35} />
          <stop offset="80%" stopColor={color} stopOpacity={0.04} />
        </linearGradient>
        <filter id="glowLine">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="dotGlow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* 그리드 라인 & 가격 레이블 */}
      {gridLevels.map((v) => {
        const y = pad.top + innerH * (1 - v);
        const price = min + range * v;
        return (
          <React.Fragment key={v}>
            <line
              x1={pad.left} y1={y}
              x2={pad.left + innerW} y2={y}
              stroke={BORDER} strokeWidth={1} strokeDasharray="4 4"
            />
            <text
              x={pad.left - 8} y={y + 5}
              textAnchor="end" fill={GRAY}
              fontSize={18} fontFamily="'Noto Sans KR', monospace"
            >
              {price.toFixed(0)}
            </text>
          </React.Fragment>
        );
      })}

      {/* X축 날짜 (5일 간격) */}
      {[0, 4, 9, 14, 19].filter(i => i < data.length).map((i) => (
        <text
          key={i}
          x={pts[i][0]} y={pad.top + innerH + 28}
          textAnchor="middle" fill={GRAY}
          fontSize={16} fontFamily="'Noto Sans KR', monospace"
        >
          -{data.length - 1 - i}d
        </text>
      ))}

      {/* 영역 그라디언트 */}
      <path d={areaPath} fill="url(#chartAreaGrad)" clipPath="url(#chartClip)" />

      {/* 차트 라인 (글로우) */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeOpacity={0.4}
        clipPath="url(#chartClip)"
      />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#glowLine)"
        clipPath="url(#chartClip)"
      />

      {/* 현재 가격 마커 */}
      {progress > 0.1 && (
        <>
          <circle cx={lastPt[0]} cy={lastPt[1]} r={10} fill={color} fillOpacity={0.2} filter="url(#dotGlow)" />
          <circle cx={lastPt[0]} cy={lastPt[1]} r={5} fill={color} />
          <circle cx={lastPt[0]} cy={lastPt[1]} r={2} fill={WHITE} />
        </>
      )}
    </svg>
  );
};

// ─── RSI 게이지 ──────────────────────────────────────────────────────────────
const RsiGauge: React.FC<{ rsi: number; animatedRsi: number }> = ({ rsi, animatedRsi }) => {
  const color = rsi >= 70 ? RED : rsi <= 30 ? GREEN : YELLOW;
  const label = rsi >= 70 ? '과매수 구간' : rsi <= 30 ? '과매도 구간' : '중립 구간';
  const pct = Math.min(Math.max(animatedRsi / 100, 0), 1);

  // 30/70 영역 표시
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
        <span style={{ fontSize: 24, color: DIM, fontWeight: 600 }}>RSI (14)</span>
        <span style={{ fontSize: 52, fontWeight: 900, color, fontVariantNumeric: 'tabular-nums' }}>
          {animatedRsi.toFixed(1)}
          <span style={{ fontSize: 22, color: DIM, marginLeft: 10, fontWeight: 500 }}>{label}</span>
        </span>
      </div>
      {/* 트랙 */}
      <div style={{ position: 'relative', height: 12, background: BORDER, borderRadius: 6 }}>
        {/* 과매도 구간 (0-30) */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: '30%', background: `${GREEN}30`, borderRadius: '6px 0 0 6px',
        }} />
        {/* 과매수 구간 (70-100) */}
        <div style={{
          position: 'absolute', right: 0, top: 0, bottom: 0,
          width: '30%', background: `${RED}30`, borderRadius: '0 6px 6px 0',
        }} />
        {/* 현재값 바 */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct * 100}%`, background: color,
          borderRadius: 6, transition: 'none',
          boxShadow: `0 0 12px ${color}80`,
        }} />
        {/* 30/70 경계선 */}
        <div style={{ position: 'absolute', left: '30%', top: -4, bottom: -4, width: 1, background: `${GREEN}80` }} />
        <div style={{ position: 'absolute', left: '70%', top: -4, bottom: -4, width: 1, background: `${RED}80` }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 18, color: GRAY }}>
        <span style={{ color: GREEN }}>30 과매도</span>
        <span>50</span>
        <span style={{ color: RED }}>70 과매수</span>
      </div>
    </div>
  );
};

// ─── 수치 뱃지 ───────────────────────────────────────────────────────────────
const MetricBadge: React.FC<{
  label: string;
  value: string;
  color: string;
  icon?: string;
}> = ({ label, value, color, icon }) => (
  <div style={{
    flex: 1, background: `${color}10`,
    border: `1px solid ${color}40`,
    borderRadius: 16, padding: '20px 24px',
    display: 'flex', flexDirection: 'column', gap: 8,
  }}>
    <div style={{ fontSize: 20, color: DIM, fontWeight: 500 }}>
      {icon && <span style={{ marginRight: 6 }}>{icon}</span>}
      {label}
    </div>
    <div style={{ fontSize: 36, fontWeight: 800, color }}>{value}</div>
  </div>
);

// ─── 씬 래퍼 (enter/exit 애니메이션) ────────────────────────────────────────
const Scene: React.FC<{
  children: React.ReactNode;
  frame: number;
  enterAt: number;
  exitAt?: number;
  enterDuration?: number;
  exitDuration?: number;
  slideFrom?: 'bottom' | 'top' | 'right';
}> = ({
  children,
  frame,
  enterAt,
  exitAt,
  enterDuration = 20,
  exitDuration = 15,
  slideFrom = 'bottom',
}) => {
  const slideDir = slideFrom === 'bottom' ? 1 : slideFrom === 'top' ? -1 : 0;

  const enterProgress = interpolate(frame, [enterAt, enterAt + enterDuration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const exitProgress = exitAt != null
    ? interpolate(frame, [exitAt, exitAt + exitDuration], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic),
    })
    : 0;

  const opacity = Math.min(enterProgress, 1 - exitProgress);
  const slideEnter = (1 - enterProgress) * 60 * slideDir;
  const slideExit = exitProgress * -60 * slideDir;
  const translateY = slideEnter + slideExit;

  return (
    <div style={{
      position: 'absolute', inset: 0,
      opacity,
      transform: `translateY(${translateY}px)`,
      pointerEvents: opacity < 0.05 ? 'none' : 'auto',
    }}>
      {children}
    </div>
  );
};

// ─── 자막 오버레이 ────────────────────────────────────────────────────────────
const SubtitleOverlay: React.FC<{
  script: string;
  frame: number;
  totalFrames?: number;
}> = ({ script, frame, totalFrames = 900 }) => {
  // Split into sentences
  const sentences = script
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(Boolean);

  if (sentences.length === 0) return null;

  const framesPerSentence = Math.floor(totalFrames / sentences.length);
  const currentIdx = Math.min(
    Math.floor(frame / framesPerSentence),
    sentences.length - 1,
  );
  const sentenceFrame = frame - currentIdx * framesPerSentence;

  const opacity = interpolate(sentenceFrame, [0, 8, framesPerSentence - 10, framesPerSentence], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const currentText = sentences[currentIdx];

  return (
    <div style={{
      position: 'absolute',
      bottom: 72,
      left: 40,
      right: 40,
      opacity,
      pointerEvents: 'none',
      zIndex: 50,
    }}>
      <div style={{
        background: 'rgba(8, 12, 24, 0.82)',
        borderRadius: 14,
        padding: '14px 24px',
        border: `1px solid ${BORDER}`,
        backdropFilter: 'blur(8px)',
      }}>
        <p style={{
          margin: 0,
          fontSize: 28,
          fontWeight: 600,
          color: WHITE,
          lineHeight: 1.5,
          textAlign: 'center',
          fontFamily: "'Noto Sans KR', sans-serif",
          textShadow: '0 1px 4px rgba(0,0,0,0.8)',
        }}>
          {currentText}
        </p>
      </div>
    </div>
  );
};

// ─── 메인 컴포넌트 ───────────────────────────────────────────────────────────
export const StockShort: React.FC<Props> = ({
  symbol,
  price,
  changePct,
  cardTitle,
  cardSubtitle,
  script = '',
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

  // 씬 타이밍 (30fps 기준)
  // 씬1: 0-5s (0-150f)   — 히어로
  // 씬2: 4-13s (120-390f) — 차트
  // 씬3: 12-23s (360-690f) — 퀀트 지표
  // 씬4: 22-30s (660-900f) — 결론

  const S1_ENTER = 0;
  const S1_EXIT = fps * 4.5;
  const S2_ENTER = fps * 4;
  const S2_EXIT = fps * 12.5;
  const S3_ENTER = fps * 12;
  const S3_EXIT = fps * 22.5;
  const S4_ENTER = fps * 22;

  const accentColor = changePct > 0 ? GREEN : changePct < 0 ? RED : YELLOW;
  const sign = changePct > 0 ? '▲' : changePct < 0 ? '▼' : '■';

  // 카운트업 애니메이션
  const animatedChangePct = countUp(frame, S1_ENTER + 15, 30, 0, Math.abs(changePct));
  const animatedPrice = countUp(frame, S1_ENTER + 5, 35, price * 0.97, price);
  const animatedRsi = countUp(frame, S3_ENTER + 15, 40, 0, rsi);
  const animatedVol = countUp(frame, S3_ENTER + 20, 35, 0, volumeRatio);

  const macdBullish = macd > macdSignal;
  const macdColor = macdBullish ? GREEN : RED;
  const bbColor = bbPosition === 'upper' ? RED : bbPosition === 'lower' ? GREEN : YELLOW;
  const bbLabel = bbPosition === 'upper' ? '상단 돌파' : bbPosition === 'lower' ? '하단 지지' : '중간대';
  const emaTrendColor = emaTrend === 'bullish' ? GREEN : emaTrend === 'bearish' ? RED : YELLOW;
  const emaTrendLabel = emaTrend === 'bullish' ? '▲ 상승추세' : emaTrend === 'bearish' ? '▼ 하락추세' : '◆ 혼조';

  // 씬1 내부 세부 애니메이션
  const symbolSpring = spring({ frame, fps, from: 0, to: 1, config: { damping: 14, stiffness: 70 } });
  const priceSlide = interpolate(frame, [8, 28], [40, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
    easing: Easing.out(Easing.back(1.2)),
  });
  const badgeSpring = spring({ frame: Math.max(0, frame - 20), fps, from: 0, to: 1, config: { damping: 16, stiffness: 80 } });

  return (
    <AbsoluteFill style={{
      background: BG,
      fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      overflow: 'hidden',
    }}>

      {audioPath && (
        <Audio src={audioPath.startsWith('/') ? `file://${audioPath}` : staticFile(audioPath)} />
      )}

      {/* 배경 글로우 - 항상 표시 */}
      <div style={{
        position: 'absolute', top: -300, left: -200,
        width: 800, height: 800,
        background: `radial-gradient(circle, ${accentColor}12 0%, transparent 65%)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: -200, right: -100,
        width: 600, height: 600,
        background: `radial-gradient(circle, ${BLUE}0a 0%, transparent 65%)`,
        pointerEvents: 'none',
      }} />

      {/* 상단 브랜드 바 - 항상 표시 */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 80, display: 'flex', alignItems: 'center',
        padding: '0 60px', justifyContent: 'space-between',
        background: `linear-gradient(180deg, ${BG} 60%, transparent)`,
        zIndex: 100,
      }}>
        <div style={{ fontSize: 22, color: GRAY, letterSpacing: 8, fontWeight: 700 }}>
          STOCK·SNAP
        </div>
        <div style={{
          fontSize: 18, color: GRAY,
          background: SURFACE, border: `1px solid ${BORDER}`,
          borderRadius: 20, padding: '6px 18px',
        }}>
          실시간 분석
        </div>
      </div>

      {/* 하단 면책고지 - 항상 표시 */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: `linear-gradient(0deg, ${BG} 60%, transparent)`,
        fontSize: 18, color: `${GRAY}88`,
        zIndex: 100,
      }}>
        본 콘텐츠는 투자 조언이 아닙니다. 투자의 책임은 본인에게 있습니다.
      </div>

      {/* ══ 씬1: 히어로 — 심볼 + 가격 ══════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S1_ENTER} exitAt={S1_EXIT} slideFrom="top">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          {/* 심볼 */}
          <div style={{
            fontSize: 110, fontWeight: 900, color: WHITE,
            letterSpacing: -3, lineHeight: 1,
            transform: `scale(${symbolSpring})`,
            transformOrigin: 'left center',
          }}>
            {symbol}
          </div>

          {/* 가격 */}
          <div style={{
            fontSize: 76, fontWeight: 800, color: WHITE,
            marginTop: 16,
            transform: `translateY(${priceSlide}px)`,
            fontVariantNumeric: 'tabular-nums',
          }}>
            ${animatedPrice.toFixed(2)}
          </div>

          {/* 변동률 뱃지 */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 12,
            marginTop: 32,
            transform: `scale(${badgeSpring})`,
            transformOrigin: 'left center',
          }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              fontSize: 52, fontWeight: 900, color: accentColor,
              background: `${accentColor}15`,
              border: `2px solid ${accentColor}50`,
              borderRadius: 16, padding: '12px 32px',
              boxShadow: `0 0 32px ${accentColor}30`,
              fontVariantNumeric: 'tabular-nums',
            }}>
              {sign} {animatedChangePct.toFixed(2)}%
            </div>
          </div>

          {/* EMA 추세 */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            marginTop: 28, fontSize: 26, fontWeight: 700,
            color: emaTrendColor,
            background: SURFACE, border: `1px solid ${BORDER}`,
            borderRadius: 12, padding: '10px 24px',
            width: 'fit-content',
          }}>
            EMA {emaTrendLabel}
          </div>

          {/* 구분선 */}
          <div style={{
            marginTop: 48, height: 2,
            background: `linear-gradient(90deg, ${accentColor}80, transparent)`,
            width: '60%',
          }} />

          {/* 티커 정보 */}
          <div style={{
            marginTop: 24, fontSize: 22, color: DIM, lineHeight: 2,
          }}>
            <span style={{ color: GRAY, marginRight: 16 }}>NASDAQ</span>
            시가총액 상위 종목 · 실시간 퀀트 분석
          </div>
        </div>
      </Scene>

      {/* ══ 씬2: 차트 ══════════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S2_ENTER} exitAt={S2_EXIT} slideFrom="bottom">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: DIM, marginBottom: 8 }}>
            가격 추이
          </div>
          <div style={{
            fontSize: 52, fontWeight: 900, color: WHITE, marginBottom: 40,
          }}>
            최근 20거래일
          </div>

          {/* 차트 카드 */}
          <div style={{
            background: SURFACE,
            border: `1px solid ${BORDER}`,
            borderRadius: 24, padding: '32px 28px',
            boxShadow: `0 0 60px ${accentColor}10`,
          }}>
            <AdvancedChart
              data={chartData}
              frame={frame - S2_ENTER}
              color={accentColor}
              width={920}
              height={320}
            />
          </div>

          {/* 가격 요약 */}
          {chartData.length >= 2 && (
            <div style={{
              display: 'flex', gap: 20, marginTop: 28,
            }}>
              <div style={{
                flex: 1, background: SURFACE2, border: `1px solid ${BORDER}`,
                borderRadius: 16, padding: '20px 24px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 20, color: GRAY, marginBottom: 8 }}>20일 전</div>
                <div style={{ fontSize: 38, fontWeight: 800, color: WHITE, fontVariantNumeric: 'tabular-nums' }}>
                  ${chartData[0].toFixed(2)}
                </div>
              </div>
              <div style={{
                flex: 1, background: `${accentColor}10`, border: `1px solid ${accentColor}40`,
                borderRadius: 16, padding: '20px 24px', textAlign: 'center',
                boxShadow: `0 0 24px ${accentColor}15`,
              }}>
                <div style={{ fontSize: 20, color: GRAY, marginBottom: 8 }}>현재가</div>
                <div style={{ fontSize: 38, fontWeight: 800, color: accentColor, fontVariantNumeric: 'tabular-nums' }}>
                  ${chartData[chartData.length - 1].toFixed(2)}
                </div>
              </div>
              <div style={{
                flex: 1, background: SURFACE2, border: `1px solid ${BORDER}`,
                borderRadius: 16, padding: '20px 24px', textAlign: 'center',
              }}>
                <div style={{ fontSize: 20, color: GRAY, marginBottom: 8 }}>20일 변동</div>
                <div style={{
                  fontSize: 38, fontWeight: 800, fontVariantNumeric: 'tabular-nums',
                  color: chartData[chartData.length - 1] > chartData[0] ? GREEN : RED,
                }}>
                  {((chartData[chartData.length - 1] / chartData[0] - 1) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}
        </div>
      </Scene>

      {/* ══ 씬3: 퀀트 지표 ═════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S3_ENTER} exitAt={S3_EXIT} slideFrom="bottom">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: DIM, marginBottom: 8 }}>
            기술적 분석
          </div>
          <div style={{ fontSize: 52, fontWeight: 900, color: WHITE, marginBottom: 40 }}>
            퀀트 시그널
          </div>

          {/* RSI 카드 */}
          <div style={{
            background: SURFACE, border: `1px solid ${BORDER}`,
            borderRadius: 24, padding: '36px 36px', marginBottom: 24,
          }}>
            <RsiGauge rsi={rsi} animatedRsi={animatedRsi} />
          </div>

          {/* MACD + BB + Volume */}
          <div style={{ display: 'flex', gap: 16 }}>
            <MetricBadge
              label="MACD"
              value={macdBullish ? '골든크로스 ↑' : '데드크로스 ↓'}
              color={macdColor}
              icon="📊"
            />
            <MetricBadge
              label="볼린저밴드"
              value={`${bbLabel}`}
              color={bbColor}
              icon="📉"
            />
            <MetricBadge
              label="거래량"
              value={`${animatedVol.toFixed(1)}x`}
              color={animatedVol >= 2 ? RED : animatedVol >= 1.5 ? YELLOW : GREEN}
              icon="📦"
            />
          </div>
        </div>
      </Scene>

      {/* ══ 씬4: 결론 ══════════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S4_ENTER} slideFrom="bottom">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          {/* 결론 카드 */}
          <div style={{
            background: `linear-gradient(135deg, ${accentColor}18 0%, ${SURFACE} 60%)`,
            border: `1.5px solid ${accentColor}50`,
            borderRadius: 28, padding: '52px 48px',
            boxShadow: `0 0 80px ${accentColor}20`,
          }}>
            <div style={{ fontSize: 28, color: accentColor, fontWeight: 600, marginBottom: 16 }}>
              오늘의 분석 결론
            </div>
            <div style={{ fontSize: 56, fontWeight: 900, color: WHITE, lineHeight: 1.2, marginBottom: 24 }}>
              {cardTitle}
            </div>
            <div style={{ height: 2, background: `${accentColor}40`, marginBottom: 28 }} />
            <div style={{ fontSize: 30, color: DIM, lineHeight: 1.7 }}>
              {cardSubtitle}
            </div>
          </div>

          {/* 퀀트 요약 뱃지 */}
          <div style={{
            display: 'flex', gap: 16, marginTop: 36, flexWrap: 'wrap',
          }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: SURFACE, border: `1px solid ${BORDER}`,
              borderRadius: 40, padding: '12px 28px',
              fontSize: 24, color: DIM,
            }}>
              <span style={{ color: rsi >= 70 ? RED : rsi <= 30 ? GREEN : YELLOW }}>●</span>
              RSI {rsi.toFixed(0)}
            </div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: SURFACE, border: `1px solid ${BORDER}`,
              borderRadius: 40, padding: '12px 28px',
              fontSize: 24, color: DIM,
            }}>
              <span style={{ color: macdBullish ? GREEN : RED }}>●</span>
              MACD {macdBullish ? '↑' : '↓'}
            </div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: SURFACE, border: `1px solid ${BORDER}`,
              borderRadius: 40, padding: '12px 28px',
              fontSize: 24, color: DIM,
            }}>
              <span style={{ color: emaTrendColor }}>●</span>
              EMA {emaTrendLabel}
            </div>
          </div>

          {/* 팔로우 CTA */}
          <div style={{
            marginTop: 48, textAlign: 'center',
            fontSize: 30, fontWeight: 700, color: WHITE,
          }}>
            @stock.snap 팔로우하고 매일 분석 받기 📈
          </div>
        </div>
      </Scene>

      {/* 자막 오버레이 */}
      {script && (
        <SubtitleOverlay script={script} frame={frame} totalFrames={fps * 30} />
      )}

    </AbsoluteFill>
  );
};
