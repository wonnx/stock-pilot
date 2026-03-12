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
  CalculateMetadataFunction,
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
  chartData?: number[];     // last 20 days close
  companyNameKo?: string;   // Korean company name (e.g. "바이오엔텍")
  newsHeadlines?: string[]; // Top news headlines explaining the move
  audioSegments?: string[]; // Per-scene audio file names (5 segments)
  scriptSegments?: string[]; // Per-scene subtitle text (5 segments)
  bgmPath?: string;         // Background music file name (in public/)
  totalFrames?: number;     // Override composition duration (default 1350)
  sceneDurations?: number[]; // Per-scene frame counts [s1,s2,s3,s4,s5]
  subtitleTimings?: number[][][]; // Per-scene, per-sentence [start_sec, end_sec]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const calculateMetadata: CalculateMetadataFunction<any> = ({ props }: { props: Props }) => {
  return { durationInFrames: props.totalFrames ?? 1350 };
};

// ─── Color palette ────────────────────────────────────────────────────────────
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

// ─── Helper: smooth count-up ────────────────────────────────────────────────
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

// ─── Helper: SVG smooth cubic bezier path ────────────────────────────────────
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

// ─── Mini chart component ──────────────────────────────────────────────────────
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

  // Animation progress (0→1)
  const progress = interpolate(frame, [0, 50], [0, 1], {
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const clipW = progress * (innerW + pad.left + pad.right);

  // Last visible point
  const lastVisibleIdx = Math.min(
    Math.floor(progress * (data.length - 1)),
    data.length - 1,
  );
  const lastPt = pts[lastVisibleIdx] ?? pts[pts.length - 1];

  // Grid price labels
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

      {/* Grid lines & price labels */}
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

      {/* X-axis dates (5-day intervals) */}
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

      {/* Area gradient */}
      <path d={areaPath} fill="url(#chartAreaGrad)" clipPath="url(#chartClip)" />

      {/* Chart line (glow) */}
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

      {/* Current price marker */}
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

// ─── RSI gauge ──────────────────────────────────────────────────────────────
const RsiGauge: React.FC<{ rsi: number; animatedRsi: number }> = ({ rsi, animatedRsi }) => {
  const color = rsi >= 70 ? RED : rsi <= 30 ? GREEN : YELLOW;
  const label = rsi >= 70 ? '과매수' : rsi <= 30 ? '과매도' : '중립';
  const pct = Math.min(Math.max(animatedRsi / 100, 0), 1);

  // 30/70 zone display
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
        <span style={{ fontSize: 24, color: DIM, fontWeight: 600 }}>RSI (14)</span>
        <span style={{ fontSize: 52, fontWeight: 900, color, fontVariantNumeric: 'tabular-nums' }}>
          {animatedRsi.toFixed(1)}
          <span style={{ fontSize: 22, color: DIM, marginLeft: 10, fontWeight: 500 }}>{label}</span>
        </span>
      </div>
      {/* Track */}
      <div style={{ position: 'relative', height: 12, background: BORDER, borderRadius: 6 }}>
        {/* Oversold zone (0-30) */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: '30%', background: `${GREEN}30`, borderRadius: '6px 0 0 6px',
        }} />
        {/* Overbought zone (70-100) */}
        <div style={{
          position: 'absolute', right: 0, top: 0, bottom: 0,
          width: '30%', background: `${RED}30`, borderRadius: '0 6px 6px 0',
        }} />
        {/* Current value bar */}
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct * 100}%`, background: color,
          borderRadius: 6, transition: 'none',
          boxShadow: `0 0 12px ${color}80`,
        }} />
        {/* 30/70 boundary lines */}
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

// ─── Metric badge ───────────────────────────────────────────────────────────────
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

// ─── Scene wrapper (enter/exit animation) ────────────────────────────────────────
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

  if (opacity < 0.01) return null;

  return (
    <div style={{
      position: 'absolute', inset: 0,
      opacity,
      transform: `translateY(${translateY}px)`,
      background: BG,
      pointerEvents: opacity < 0.05 ? 'none' : 'auto',
    }}>
      {children}
    </div>
  );
};

// ─── Korean line-wrapping helper ──────────────────────────────────────────────
const wrapKoreanText = (text: string, maxCharsPerLine = 18): string => {
  if (text.length <= maxCharsPerLine) return text;
  const words = text.split(' ');
  const lines: string[] = [];
  let line = '';
  for (const word of words) {
    if (!line) {
      line = word;
    } else if (line.length + 1 + word.length <= maxCharsPerLine) {
      line += ' ' + word;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  return lines.join('\n');
};

// ─── Scene-aware subtitle overlay ────────────────────────────────────────────────
const SubtitleOverlay: React.FC<{
  script: string;
  frame: number;
  fps: number;
  totalFrames?: number;
  scriptSegments?: string[];
  sceneDurations?: number[];
  subtitleTimings?: number[][][]; // [segment][sentence][start_sec, end_sec]
}> = ({ script, frame, fps, totalFrames = 1350, scriptSegments, sceneDurations, subtitleTimings }) => {
  // Compute scene ranges from durations (same logic as main component)
  const DEFAULT_DURATIONS = [
    Math.round(fps * 5), Math.round(fps * 12), Math.round(fps * 9),
    Math.round(fps * 11), Math.round(fps * 8),
  ];
  const dur = sceneDurations && sceneDurations.length === 5 ? sceneDurations : DEFAULT_DURATIONS;
  let cursor = 0;
  const sceneRanges = dur.map((d) => {
    const range = { start: cursor, end: cursor + d };
    cursor += d;
    return range;
  });

  // Determine which text to show based on scene timing
  let currentText = '';
  let segmentOpacity = 0;

  if (scriptSegments && scriptSegments.length === 5) {
    for (let i = 0; i < sceneRanges.length; i++) {
      const { start, end } = sceneRanges[i];
      if (frame >= start && frame < end) {
        const sentences = scriptSegments[i]
          .split(/(?<=[.!?。])\s+/)
          .map(s => s.trim())
          .filter(Boolean);
        if (sentences.length === 0) break;

        const localFrame = frame - start;
        const localSec = localFrame / fps;

        // ── TTS-synced mode: use word-boundary timing data ──
        const segTimings = subtitleTimings && subtitleTimings.length > i ? subtitleTimings[i] : null;
        if (segTimings && segTimings.length > 0) {
          for (let j = 0; j < Math.min(sentences.length, segTimings.length); j++) {
            const [startSec, endSec] = segTimings[j];
            if (localSec >= startSec && localSec < endSec) {
              const startFr = Math.floor(startSec * fps);
              const endFr = Math.floor(endSec * fps);
              const span = endFr - startFr;
              segmentOpacity = interpolate(
                localFrame,
                [startFr, startFr + 5, endFr - 5, endFr],
                [0, 1, 1, 0],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              );
              // Also show last sentence at scene end if no next sentence covers this frame
              if (span < 3) segmentOpacity = 1;
              currentText = wrapKoreanText(sentences[j]);
              break;
            }
          }
        } else {
          // ── Fallback: equal-time distribution (char-weighted) ──
          const totalChars = sentences.reduce((s, t) => s + t.length, 0) || 1;
          const sceneDur = end - start;
          let sentStart = 0;
          for (let j = 0; j < sentences.length; j++) {
            const sentFrames = Math.round(sceneDur * sentences[j].length / totalChars);
            const sentEnd = sentStart + sentFrames;
            if (localFrame >= sentStart && localFrame < sentEnd) {
              const span = sentEnd - sentStart;
              segmentOpacity = interpolate(
                localFrame - sentStart,
                [0, 6, span - 8, span],
                [0, 1, 1, 0],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
              );
              currentText = wrapKoreanText(sentences[j]);
              break;
            }
            sentStart = sentEnd;
          }
        }
        break;
      }
    }
  } else {
    // Fallback: evenly distributed across total frames
    const sentences = script.split(/(?<=[.!?。])\s+/).map(s => s.trim()).filter(Boolean);
    if (sentences.length === 0) return null;
    const totalChars = sentences.reduce((s, t) => s + t.length, 0) || 1;
    let sentStart = 0;
    for (let j = 0; j < sentences.length; j++) {
      const sentFrames = Math.round(totalFrames * sentences[j].length / totalChars);
      const sentEnd = sentStart + sentFrames;
      if (frame >= sentStart && frame < sentEnd) {
        const span = sentEnd - sentStart;
        segmentOpacity = interpolate(
          frame - sentStart,
          [0, 6, span - 8, span],
          [0, 1, 1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
        );
        currentText = wrapKoreanText(sentences[j]);
        break;
      }
      sentStart = sentEnd;
    }
  }

  if (!currentText || segmentOpacity < 0.01) return null;

  return (
    <div style={{
      position: 'absolute',
      bottom: 280,
      left: 40,
      right: 40,
      opacity: segmentOpacity,
      pointerEvents: 'none',
      zIndex: 50,
    }}>
      <div style={{
        background: 'rgba(8, 12, 24, 0.88)',
        borderRadius: 16,
        padding: '18px 28px',
        border: `1px solid ${BORDER}`,
        backdropFilter: 'blur(10px)',
      }}>
        <p style={{
          margin: 0,
          fontSize: 34,
          fontWeight: 700,
          color: WHITE,
          lineHeight: 1.55,
          textAlign: 'center',
          fontFamily: "'Noto Sans KR', sans-serif",
          textShadow: '0 2px 6px rgba(0,0,0,0.9)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'keep-all',
          overflowWrap: 'break-word',
        }}>
          {currentText}
        </p>
      </div>
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────
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
  companyNameKo = '',
  newsHeadlines = [],
  audioSegments = [],
  scriptSegments = [],
  bgmPath = '',
  sceneDurations = [],
  subtitleTimings = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Default scene durations (frames): [Hero, News, Chart, Indicators, Conclusion]
  const DEFAULT_DURATIONS = [
    Math.round(fps * 5),   // 5s
    Math.round(fps * 12),  // 12s
    Math.round(fps * 9),   // 9s
    Math.round(fps * 11),  // 11s
    Math.round(fps * 8),   // 8s
  ];
  const dur = sceneDurations.length === 5 ? sceneDurations : DEFAULT_DURATIONS;

  // Compute scene enter/exit from durations (no overlap)
  const S1_ENTER = 0;
  const S1_EXIT  = dur[0];
  const S2_ENTER = dur[0];
  const S2_EXIT  = dur[0] + dur[1];
  const S3_ENTER = dur[0] + dur[1];
  const S3_EXIT  = dur[0] + dur[1] + dur[2];
  const S4_ENTER = dur[0] + dur[1] + dur[2];
  const S4_EXIT  = dur[0] + dur[1] + dur[2] + dur[3];
  const S5_ENTER = dur[0] + dur[1] + dur[2] + dur[3];
  const _S5_EXIT = S5_ENTER + dur[4]; // used for subtitle range

  const accentColor = changePct > 0 ? GREEN : changePct < 0 ? RED : YELLOW;
  const sign = changePct > 0 ? '▲' : changePct < 0 ? '▼' : '■';

  // Count-up animations
  const animatedChangePct = countUp(frame, S1_ENTER + 15, 30, 0, Math.abs(changePct));
  const animatedPrice = countUp(frame, S1_ENTER + 5, 35, price * 0.97, price);
  const animatedRsi = countUp(frame, S4_ENTER + 15, 40, 0, rsi);
  const animatedVol = countUp(frame, S4_ENTER + 20, 35, 0, volumeRatio);

  const macdBullish = macd > macdSignal;
  const macdColor = macdBullish ? GREEN : RED;
  const bbColor = bbPosition === 'upper' ? RED : bbPosition === 'lower' ? GREEN : YELLOW;
  const bbLabel = bbPosition === 'upper' ? '상단 돌파' : bbPosition === 'lower' ? '하단 지지' : '중간대';
  const emaTrendColor = emaTrend === 'bullish' ? GREEN : emaTrend === 'bearish' ? RED : YELLOW;
  const emaTrendLabel = emaTrend === 'bullish' ? '▲ 상승' : emaTrend === 'bearish' ? '▼ 하락' : '◆ 혼조';

  // Scene1 internal animations
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

      {/* Audio: per-scene TTS segments with dynamic timing */}
      {audioSegments.length === 5 ? (
        <>
          <Sequence from={S1_ENTER} durationInFrames={dur[0]}><Audio src={staticFile(audioSegments[0])} volume={1} /></Sequence>
          <Sequence from={S2_ENTER} durationInFrames={dur[1]}><Audio src={staticFile(audioSegments[1])} volume={1} /></Sequence>
          <Sequence from={S3_ENTER} durationInFrames={dur[2]}><Audio src={staticFile(audioSegments[2])} volume={1} /></Sequence>
          <Sequence from={S4_ENTER} durationInFrames={dur[3]}><Audio src={staticFile(audioSegments[3])} volume={1} /></Sequence>
          <Sequence from={S5_ENTER} durationInFrames={dur[4]}><Audio src={staticFile(audioSegments[4])} volume={1} /></Sequence>
        </>
      ) : audioPath ? (
        <Audio src={staticFile(audioPath)} volume={1} />
      ) : null}

      {/* BGM: subtle background music at -18dB (volume ≈ 0.126), full video duration */}
      {bgmPath ? (
        <Sequence from={0} durationInFrames={durationInFrames}>
          <Audio src={staticFile(bgmPath)} volume={0.126} loop />
        </Sequence>
      ) : null}

      {/* Background glow */}
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

      {/* Top brand bar */}
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
          LIVE
        </div>
      </div>

      {/* Bottom disclaimer */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: `linear-gradient(0deg, ${BG} 60%, transparent)`,
        fontSize: 18, color: `${GRAY}88`,
        zIndex: 100,
      }}>
        본 콘텐츠는 투자 조언이 아닙니다. 투자의 책임은 본인에게 있습니다.
      </div>

      {/* ══ Scene1: Hero — Symbol + Price ══════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S1_ENTER} exitAt={S1_EXIT} slideFrom="top">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          {/* Symbol */}
          {companyNameKo && (
            <div style={{
              fontSize: 40, fontWeight: 700, color: DIM,
              marginBottom: 8,
              transform: `scale(${symbolSpring})`,
              transformOrigin: 'left center',
            }}>
              {companyNameKo}
            </div>
          )}
          <div style={{
            fontSize: 110, fontWeight: 900, color: WHITE,
            letterSpacing: -3, lineHeight: 1,
            transform: `scale(${symbolSpring})`,
            transformOrigin: 'left center',
          }}>
            {symbol}
          </div>

          {/* Price */}
          <div style={{
            fontSize: 76, fontWeight: 800, color: WHITE,
            marginTop: 16,
            transform: `translateY(${priceSlide}px)`,
            fontVariantNumeric: 'tabular-nums',
          }}>
            ${animatedPrice.toFixed(2)}
          </div>

          {/* Change badge */}
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

          {/* EMA trend */}
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

          {/* Divider */}
          <div style={{
            marginTop: 48, height: 2,
            background: `linear-gradient(90deg, ${accentColor}80, transparent)`,
            width: '60%',
          }} />

          {/* Interpretation */}
          <div style={{
            marginTop: 32, fontSize: 24, color: DIM, lineHeight: 1.8,
            background: SURFACE, border: `1px solid ${BORDER}`,
            borderRadius: 16, padding: '20px 24px',
          }}>
            {changePct > 0
              ? `${symbol}이 오늘 ${Math.abs(changePct).toFixed(1)}% 급등했습니다. ${emaTrend === 'bullish' ? '강한 상승' : '혼조'} 모멘텀과 함께 거래량이 평균 대비 ${volumeRatio.toFixed(1)}배로 ${volumeRatio >= 2 ? '높은 확신' : '보통 수준'}의 참여를 보이고 있습니다.`
              : `${symbol}이 오늘 ${Math.abs(changePct).toFixed(1)}% 급락했습니다. ${emaTrend === 'bearish' ? '지속적인 하방' : '불확실한'} 압력과 함께 거래량이 평균 대비 ${volumeRatio.toFixed(1)}배로 ${volumeRatio >= 2 ? '강한 매도세' : '보통 수준'}의 활동을 보이고 있습니다.`
            }
          </div>

          {/* Ticker info */}
          <div style={{
            marginTop: 16, fontSize: 22, color: DIM, lineHeight: 2,
          }}>
            <span style={{ color: GRAY, marginRight: 16 }}>NASDAQ</span>
            실시간 시장 분석
          </div>
        </div>
      </Scene>

      {/* ══ Scene2: News / Reason ═══════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S2_ENTER} exitAt={S2_EXIT} slideFrom="bottom">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: DIM, marginBottom: 8 }}>
            {changePct > 0 ? '급등 배경' : '급락 배경'}
          </div>
          <div style={{
            fontSize: 48, fontWeight: 900, color: WHITE, marginBottom: 40, lineHeight: 1.3,
          }}>
            {companyNameKo ? `${companyNameKo}(${symbol})` : symbol} {changePct > 0 ? '왜 올랐나?' : '왜 떨어졌나?'}
          </div>

          {/* News items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {newsHeadlines.length > 0 ? newsHeadlines.slice(0, 3).map((headline, i) => {
              const parts = headline.split('\n');
              const title = parts[0];
              const detail = parts.slice(1).join(' ').trim();
              return (
                <div key={i} style={{
                  background: SURFACE,
                  border: `1px solid ${BORDER}`,
                  borderRadius: 16, padding: '24px 28px',
                  display: 'flex', gap: 16, alignItems: 'flex-start',
                }}>
                  <div style={{
                    minWidth: 36, height: 36, borderRadius: 8,
                    background: `${accentColor}20`, border: `1px solid ${accentColor}40`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20, fontWeight: 800, color: accentColor,
                  }}>{i + 1}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ fontSize: 26, color: WHITE, lineHeight: 1.4, fontWeight: 700 }}>
                      {title}
                    </div>
                    {detail && (
                      <div style={{ fontSize: 22, color: DIM, lineHeight: 1.5, fontWeight: 400 }}>
                        {detail}
                      </div>
                    )}
                  </div>
                </div>
              );
            }) : (
              <div style={{
                background: SURFACE,
                border: `1px solid ${BORDER}`,
                borderRadius: 16, padding: '32px 28px',
                fontSize: 26, color: DIM, lineHeight: 1.6, textAlign: 'center',
              }}>
                {changePct > 0
                  ? '시장 전반의 매수세와 기술적 반등이 주요 요인으로 분석됩니다.'
                  : '시장 전반의 매도 압력과 투자 심리 위축이 주요 원인으로 분석됩니다.'}
              </div>
            )}
          </div>
        </div>
      </Scene>

      {/* ══ Scene3: Chart ══════════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S3_ENTER} exitAt={S3_EXIT} slideFrom="bottom">
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

          {/* Chart card */}
          <div style={{
            background: SURFACE,
            border: `1px solid ${BORDER}`,
            borderRadius: 24, padding: '32px 28px',
            boxShadow: `0 0 60px ${accentColor}10`,
          }}>
            <AdvancedChart
              data={chartData}
              frame={frame - S3_ENTER}
              color={accentColor}
              width={920}
              height={320}
            />
          </div>

          {/* Price summary */}
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

          {/* Chart interpretation */}
          <div style={{
            marginTop: 20, fontSize: 22, color: DIM, lineHeight: 1.7,
            background: `${accentColor}08`, border: `1px solid ${accentColor}25`,
            borderRadius: 14, padding: '16px 20px',
          }}>
            {(() => {
              if (chartData.length < 2) return '추세 분석을 위한 데이터가 부족합니다.';
              const pctChange20d = ((chartData[chartData.length - 1] / chartData[0]) - 1) * 100;
              const trend = pctChange20d > 5 ? '강한 상승추세' : pctChange20d > 0 ? '완만한 상승' : pctChange20d > -5 ? '완만한 하락' : '급격한 하락';
              return `20일 차트에서 ${trend} (${pctChange20d > 0 ? '+' : ''}${pctChange20d.toFixed(1)}%)가 관찰됩니다. ${pctChange20d > 5 ? '매수세가 우위 — 저항선 돌파 여부를 주목하세요.' : pctChange20d > 0 ? '점진적 회복 중 — 주요 지지선이 유지되고 있습니다.' : pctChange20d > -5 ? '약세 지속 — 지지선 이탈 여부를 모니터링하세요.' : '큰 폭의 매도세 — 안정화 확인 후 진입을 검토하세요.'}`;
            })()}
          </div>
        </div>
      </Scene>

      {/* ══ Scene4: Indicators ═════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S4_ENTER} exitAt={S4_EXIT} slideFrom="bottom">
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
            핵심 지표
          </div>

          {/* RSI card */}
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
              value={macdBullish ? '골든크로스' : '데드크로스'}
              color={macdColor}
            />
            <MetricBadge
              label="볼린저밴드"
              value={`${bbLabel}`}
              color={bbColor}
            />
            <MetricBadge
              label="거래량"
              value={`${animatedVol.toFixed(1)}x`}
              color={animatedVol >= 2 ? RED : animatedVol >= 1.5 ? YELLOW : GREEN}
            />
          </div>

          {/* Indicator interpretation */}
          <div style={{
            marginTop: 24, fontSize: 22, color: DIM, lineHeight: 1.7,
            background: SURFACE2, border: `1px solid ${BORDER}`,
            borderRadius: 14, padding: '16px 20px',
          }}>
            {`RSI ${rsi.toFixed(0)} — ${rsi >= 70 ? '과매수 구간으로 조정 위험이 높습니다' : rsi <= 30 ? '과매도 구간으로 반등 가능성이 있습니다' : '중립 구간으로 극단적 신호는 없습니다'}. `}
            {`MACD는 ${macdBullish ? '골든크로스(매수 신호)로 상승 모멘텀을 시사합니다' : '데드크로스(매도 신호)로 하방 압력을 나타냅니다'}. `}
            {`거래량은 평균 대비 ${volumeRatio.toFixed(1)}배로 ${volumeRatio >= 2 ? '강한 확신을 동반한 움직임입니다' : '보통 수준의 참여를 보이고 있습니다'}.`}
          </div>
        </div>
      </Scene>

      {/* ══ Scene5: Conclusion ══════════════════════════════════════════════════════════ */}
      <Scene frame={frame} enterAt={S5_ENTER} slideFrom="bottom">
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center',
          padding: '100px 60px',
        }}>
          {/* Conclusion card */}
          <div style={{
            background: `linear-gradient(135deg, ${accentColor}18 0%, ${SURFACE} 60%)`,
            border: `1.5px solid ${accentColor}50`,
            borderRadius: 28, padding: '52px 48px',
            boxShadow: `0 0 80px ${accentColor}20`,
          }}>
            <div style={{ fontSize: 28, color: accentColor, fontWeight: 600, marginBottom: 16 }}>
              오늘의 분석
            </div>
            <div style={{ fontSize: 56, fontWeight: 900, color: WHITE, lineHeight: 1.2, marginBottom: 24 }}>
              {cardTitle}
            </div>
            <div style={{ height: 2, background: `${accentColor}40`, marginBottom: 28 }} />
            <div style={{ fontSize: 30, color: DIM, lineHeight: 1.7 }}>
              {cardSubtitle}
            </div>
          </div>

          {/* Summary badges */}
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

          {/* Follow CTA */}
          <div style={{
            marginTop: 48, textAlign: 'center',
            fontSize: 30, fontWeight: 700, color: WHITE,
          }}>
            @stock.snap 팔로우하고 매일 분석 받기
          </div>
        </div>
      </Scene>

      {/* Subtitle overlay */}
      {script && (
        <SubtitleOverlay
          script={script}
          frame={frame}
          fps={fps}
          totalFrames={_S5_EXIT}
          scriptSegments={scriptSegments.length === 5 ? scriptSegments : undefined}
          sceneDurations={sceneDurations.length === 5 ? sceneDurations : undefined}
          subtitleTimings={subtitleTimings.length === 5 ? subtitleTimings : undefined}
        />
      )}

    </AbsoluteFill>
  );
};
