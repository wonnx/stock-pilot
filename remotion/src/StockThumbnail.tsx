import React from 'react';
import { AbsoluteFill } from 'remotion';

interface ThumbnailProps {
  symbol: string;
  price: number;
  changePct: number;
  cardTitle: string;
  cardSubtitle: string;
  rsi?: number;
  macd?: number;
  macdSignal?: number;
  volumeRatio?: number;
  bbPosition?: string;
  emaTrend?: string;
  chartData?: number[];
  companyNameKo?: string;
}

// ─── Color palette (matches StockShort) ───────────────────────────────────────
const BG = '#080c18';
const SURFACE = '#0f1623';
const BORDER = '#1e2d47';
const GREEN = '#00e5a0';
const RED = '#ff4d6d';
const YELLOW = '#ffd166';
const BLUE = '#4da6ff';
const GRAY = '#4a5a7a';
const WHITE = '#f0f4ff';
const DIM = '#8896b0';

// ─── Mini sparkline (static, full data visible) ───────────────────────────────
const Sparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  if (!data || data.length < 2) return null;
  const W = 960;
  const H = 180;
  const pad = { top: 10, bottom: 10, left: 10, right: 10 };
  const iW = W - pad.left - pad.right;
  const iH = H - pad.top - pad.bottom;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const pts: [number, number][] = data.map((v, i) => [
    pad.left + (i / (data.length - 1)) * iW,
    pad.top + iH - ((v - min) / range) * iH,
  ]);

  let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i++) {
    const p0 = pts[i - 1];
    const p1 = pts[i];
    const cpx = p0[0] + (p1[0] - p0[0]) * 0.5;
    d += ` C ${cpx.toFixed(1)} ${p0[1].toFixed(1)}, ${cpx.toFixed(1)} ${p1[1].toFixed(1)}, ${p1[0].toFixed(1)} ${p1[1].toFixed(1)}`;
  }
  const area = `${d} L ${pts[pts.length - 1][0]} ${pad.top + iH} L ${pad.left} ${pad.top + iH} Z`;
  const last = pts[pts.length - 1];

  return (
    <svg width={W} height={H} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id="thumbGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.4} />
          <stop offset="100%" stopColor={color} stopOpacity={0.03} />
        </linearGradient>
        <filter id="thumbGlow">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <path d={area} fill="url(#thumbGrad)" />
      <path d={d} fill="none" stroke={color} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" filter="url(#thumbGlow)" />
      <circle cx={last[0]} cy={last[1]} r={8} fill={color} fillOpacity={0.25} />
      <circle cx={last[0]} cy={last[1]} r={4} fill={color} />
      <circle cx={last[0]} cy={last[1]} r={1.5} fill={WHITE} />
    </svg>
  );
};

// ─── Indicator chip ────────────────────────────────────────────────────────────
const Chip: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <div style={{
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
    background: `${color}12`, border: `1.5px solid ${color}45`,
    borderRadius: 18, padding: '18px 24px', flex: 1,
    boxShadow: `0 0 18px ${color}20`,
  }}>
    <div style={{ fontSize: 22, color: DIM, fontWeight: 600 }}>{label}</div>
    <div style={{ fontSize: 32, fontWeight: 900, color }}>{value}</div>
  </div>
);

// ─── Main Thumbnail component ──────────────────────────────────────────────────
export const StockThumbnail: React.FC<ThumbnailProps> = ({
  symbol,
  price,
  changePct,
  cardTitle,
  cardSubtitle,
  rsi = 50,
  macd = 0,
  macdSignal = 0,
  volumeRatio = 1,
  bbPosition = 'middle',
  emaTrend = 'mixed',
  chartData = [],
  companyNameKo = '',
}) => {
  const accent = changePct > 0 ? GREEN : changePct < 0 ? RED : YELLOW;
  const sign = changePct > 0 ? '▲' : changePct < 0 ? '▼' : '■';
  const absPct = Math.abs(changePct).toFixed(2);
  const macdBullish = macd > macdSignal;
  const emaTrendColor = emaTrend === 'bullish' ? GREEN : emaTrend === 'bearish' ? RED : YELLOW;
  const emaTrendLabel = emaTrend === 'bullish' ? '상승추세' : emaTrend === 'bearish' ? '하락추세' : '혼조';
  const rsiColor = rsi >= 70 ? RED : rsi <= 30 ? GREEN : YELLOW;
  const rsiLabel = rsi >= 70 ? '과매수' : rsi <= 30 ? '과매도' : '중립';
  const volColor = volumeRatio >= 2 ? RED : volumeRatio >= 1.5 ? YELLOW : GREEN;

  const change20d = chartData.length >= 2
    ? ((chartData[chartData.length - 1] / chartData[0] - 1) * 100).toFixed(1)
    : null;

  return (
    <AbsoluteFill style={{
      background: BG,
      fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
      overflow: 'hidden',
    }}>
      {/* Background glow blobs */}
      <div style={{
        position: 'absolute', top: -250, left: -150,
        width: 900, height: 900,
        background: `radial-gradient(circle, ${accent}14 0%, transparent 60%)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: -300, right: -200,
        width: 700, height: 700,
        background: `radial-gradient(circle, ${BLUE}0c 0%, transparent 60%)`,
        pointerEvents: 'none',
      }} />

      {/* Top brand bar */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        height: 90, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 60px',
        background: `linear-gradient(180deg, ${BG} 70%, transparent)`,
        zIndex: 10,
      }}>
        <div style={{ fontSize: 26, color: GRAY, letterSpacing: 8, fontWeight: 700 }}>STOCK·SNAP</div>
        <div style={{
          fontSize: 20, color: accent,
          background: `${accent}15`, border: `1px solid ${accent}40`,
          borderRadius: 20, padding: '6px 20px', fontWeight: 700,
        }}>
          LIVE ANALYSIS
        </div>
      </div>

      {/* Main content */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center',
        padding: '110px 60px 80px',
        gap: 0,
      }}>

        {/* Company name + symbol */}
        <div style={{ marginBottom: 4 }}>
          {companyNameKo && (
            <div style={{ fontSize: 44, fontWeight: 700, color: DIM, marginBottom: 6 }}>
              {companyNameKo}
            </div>
          )}
          <div style={{ fontSize: 120, fontWeight: 900, color: WHITE, letterSpacing: -4, lineHeight: 1 }}>
            {symbol}
          </div>
        </div>

        {/* Price */}
        <div style={{
          fontSize: 84, fontWeight: 800, color: WHITE,
          fontVariantNumeric: 'tabular-nums', marginTop: 12,
        }}>
          ${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>

        {/* Change badge — hero element */}
        <div style={{
          display: 'inline-flex', alignItems: 'center',
          marginTop: 24, width: 'fit-content',
        }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 14,
            fontSize: 72, fontWeight: 900, color: accent,
            background: `${accent}18`, border: `2.5px solid ${accent}60`,
            borderRadius: 20, padding: '16px 40px',
            boxShadow: `0 0 50px ${accent}35, 0 0 100px ${accent}15`,
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: -1,
          }}>
            {sign} {absPct}%
          </div>
        </div>

        {/* Horizontal divider */}
        <div style={{
          height: 2, marginTop: 40, marginBottom: 32,
          background: `linear-gradient(90deg, ${accent}90, ${accent}20, transparent)`,
        }} />

        {/* Sparkline chart */}
        {chartData.length >= 2 && (
          <div style={{
            background: SURFACE, border: `1px solid ${BORDER}`,
            borderRadius: 20, padding: '20px 24px', marginBottom: 28,
            boxShadow: `0 0 40px ${accent}0a`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 22, color: DIM, fontWeight: 600 }}>최근 20거래일</span>
              {change20d !== null && (
                <span style={{
                  fontSize: 26, fontWeight: 800,
                  color: parseFloat(change20d) >= 0 ? GREEN : RED,
                }}>
                  {parseFloat(change20d) >= 0 ? '+' : ''}{change20d}%
                </span>
              )}
            </div>
            <Sparkline data={chartData} color={accent} />
          </div>
        )}

        {/* Indicator chips */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 28 }}>
          <Chip label="RSI" value={`${rsi.toFixed(0)} ${rsiLabel}`} color={rsiColor} />
          <Chip label="MACD" value={macdBullish ? '골든크로스' : '데드크로스'} color={macdBullish ? GREEN : RED} />
          <Chip label="EMA" value={emaTrendLabel} color={emaTrendColor} />
          <Chip label="거래량" value={`${volumeRatio.toFixed(1)}x`} color={volColor} />
        </div>

        {/* Card title summary */}
        <div style={{
          background: `linear-gradient(135deg, ${accent}14 0%, ${SURFACE} 70%)`,
          border: `1.5px solid ${accent}45`,
          borderRadius: 20, padding: '28px 32px',
          boxShadow: `0 0 50px ${accent}18`,
        }}>
          <div style={{ fontSize: 40, fontWeight: 900, color: WHITE, lineHeight: 1.25, marginBottom: 12 }}>
            {cardTitle}
          </div>
          <div style={{ fontSize: 28, color: DIM, lineHeight: 1.5 }}>
            {cardSubtitle}
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: `linear-gradient(0deg, ${BG} 70%, transparent)`,
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 26, fontWeight: 700, color: accent,
          letterSpacing: 1,
        }}>
          @stock.snap 팔로우하고 매일 분석 받기
        </div>
      </div>
    </AbsoluteFill>
  );
};
