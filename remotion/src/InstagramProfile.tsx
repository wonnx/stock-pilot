import React from 'react';
import { AbsoluteFill } from 'remotion';

// ─── Color palette (matches StockShort/StockThumbnail) ───────────────────────
const BG = '#080c18';
const GREEN = '#00e5a0';
const WHITE = '#f0f4ff';
const DIM = '#4a5a78';

// ─── Instagram Profile Image v2 ───────────────────────────────────────────────
// Design: solid dark navy background, clean "S" lettermark, minimal accents
// No charts — professional brand mark feel (Bloomberg/Reuters style)
export const InstagramProfile: React.FC = () => {
  const size = 640;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <AbsoluteFill
      style={{
        background: BG,
        overflow: 'hidden',
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: 'absolute', inset: 0 }}
      >
        <defs>
          {/* Subtle center radial glow — very soft */}
          <radialGradient id="centerGlow" cx="50%" cy="46%" r="42%">
            <stop offset="0%" stopColor={GREEN} stopOpacity={0.08} />
            <stop offset="100%" stopColor={GREEN} stopOpacity={0} />
          </radialGradient>

          {/* Letter gradient — white core → slight green tint */}
          <linearGradient id="letterGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} stopOpacity={1} />
            <stop offset="100%" stopColor="#c8ffe8" stopOpacity={1} />
          </linearGradient>

          {/* Soft glow for the S lettermark */}
          <filter id="sGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="14" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Green dot glow */}
          <filter id="dotGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── Background ── */}
        <rect width={size} height={size} fill={BG} />
        {/* Soft center glow */}
        <circle cx={cx} cy={cy - 20} r={260} fill="url(#centerGlow)" />

        {/* ── Outer thin ring (decorative circle) ── */}
        <circle
          cx={cx}
          cy={cy - 28}
          r={220}
          fill="none"
          stroke={DIM}
          strokeWidth={0.8}
          strokeOpacity={0.35}
        />

        {/* ── Inner ring ── */}
        <circle
          cx={cx}
          cy={cy - 28}
          r={190}
          fill="none"
          stroke={DIM}
          strokeWidth={0.6}
          strokeOpacity={0.2}
        />

        {/* ── Top arc accent — green (partial circle top) ── */}
        <path
          d={`M ${cx - 110} ${cy - 28 - Math.sqrt(220 * 220 - 110 * 110)}
              A 220 220 0 0 1 ${cx + 110} ${cy - 28 - Math.sqrt(220 * 220 - 110 * 110)}`}
          fill="none"
          stroke={GREEN}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeOpacity={0.7}
        />

        {/* ── "S" lettermark — ghost layer for depth ── */}
        <text
          x={cx + 2}
          y={cy + 52}
          textAnchor="middle"
          fontSize={300}
          fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={GREEN}
          fillOpacity={0.04}
          letterSpacing={-6}
        >
          S
        </text>

        {/* ── "S" lettermark — main ── */}
        <text
          x={cx}
          y={cy + 50}
          textAnchor="middle"
          fontSize={300}
          fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#letterGrad)"
          letterSpacing={-6}
          filter="url(#sGlow)"
          opacity={0.92}
        >
          S
        </text>

        {/* ── Bottom separator line ── */}
        <line
          x1={cx - 80}
          y1={size - 138}
          x2={cx + 80}
          y2={size - 138}
          stroke={GREEN}
          strokeWidth={1}
          strokeOpacity={0.4}
        />

        {/* ── Brand name ── */}
        <text
          x={cx}
          y={size - 100}
          textAnchor="middle"
          fontSize={34}
          fontWeight={700}
          fill={WHITE}
          letterSpacing={9}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          opacity={0.95}
        >
          STOCK·SNAP
        </text>

        {/* ── Handle ── */}
        <text
          x={cx}
          y={size - 62}
          textAnchor="middle"
          fontSize={20}
          fontWeight={400}
          fill={GREEN}
          letterSpacing={2.5}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          opacity={0.75}
        >
          @stock.snap
        </text>

        {/* ── Tagline ── */}
        <text
          x={cx}
          y={size - 36}
          textAnchor="middle"
          fontSize={14}
          fontWeight={400}
          fill={WHITE}
          letterSpacing={1}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          opacity={0.35}
        >
          MARKET OPEN · MARKET CLOSE
        </text>

        {/* ── Green accent dot (top right of ring) ── */}
        {(() => {
          const angle = -30 * (Math.PI / 180);
          const r = 220;
          const dotX = cx + r * Math.cos(angle);
          const dotY = cy - 28 + r * Math.sin(angle);
          return (
            <g filter="url(#dotGlow)">
              <circle cx={dotX} cy={dotY} r={7} fill={GREEN} opacity={0.25} />
              <circle cx={dotX} cy={dotY} r={4} fill={GREEN} opacity={0.9} />
            </g>
          );
        })()}

        {/* ── Small decorative dots flanking brand name ── */}
        <circle cx={cx - 110} cy={size - 100} r={2} fill={GREEN} opacity={0.4} />
        <circle cx={cx + 110} cy={size - 100} r={2} fill={GREEN} opacity={0.4} />
      </svg>
    </AbsoluteFill>
  );
};
