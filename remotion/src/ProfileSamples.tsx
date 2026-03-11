import React from 'react';
import { AbsoluteFill } from 'remotion';

// ─── Shared layout constants ─────────────────────────────────────────────────
const SIZE = 640;
const CX = SIZE / 2;
const CY = SIZE / 2;

// ─── Shared brand text block ─────────────────────────────────────────────────
const BrandText: React.FC<{ accent: string; white?: string }> = ({
  accent,
  white = '#f0f4ff',
}) => (
  <>
    {/* Separator */}
    <line
      x1={CX - 80}
      y1={SIZE - 138}
      x2={CX + 80}
      y2={SIZE - 138}
      stroke={accent}
      strokeWidth={1}
      strokeOpacity={0.45}
    />
    <text
      x={CX}
      y={SIZE - 100}
      textAnchor="middle"
      fontSize={34}
      fontWeight={700}
      fill={white}
      letterSpacing={9}
      fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
      opacity={0.95}
    >
      STOCK·SNAP
    </text>
    <text
      x={CX}
      y={SIZE - 62}
      textAnchor="middle"
      fontSize={20}
      fontWeight={400}
      fill={accent}
      letterSpacing={2.5}
      fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
      opacity={0.8}
    >
      @stock.snap
    </text>
    <text
      x={CX}
      y={SIZE - 36}
      textAnchor="middle"
      fontSize={14}
      fontWeight={400}
      fill={white}
      letterSpacing={1}
      fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
      opacity={0.35}
    >
      MARKET OPEN · MARKET CLOSE
    </text>
  </>
);

// ─── Sample 01: Navy + Green (refined classic) ───────────────────────────────
export const ProfileSample01: React.FC = () => {
  const BG = '#080c18';
  const ACC = '#00e5a0';
  const WHITE = '#f0f4ff';
  const DIM = '#4a5a78';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s01glow" cx="50%" cy="46%" r="42%">
            <stop offset="0%" stopColor={ACC} stopOpacity={0.1} />
            <stop offset="100%" stopColor={ACC} stopOpacity={0} />
          </radialGradient>
          <linearGradient id="s01letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor="#c8ffe8" />
          </linearGradient>
          <filter id="s01gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="16" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill={BG} />
        <circle cx={CX} cy={CY - 20} r={270} fill="url(#s01glow)" />
        {/* Rings */}
        {[220, 190, 155].map((r, i) => (
          <circle key={i} cx={CX} cy={CY - 28} r={r} fill="none" stroke={DIM}
            strokeWidth={i === 0 ? 0.8 : 0.5} strokeOpacity={i === 0 ? 0.3 : 0.15} />
        ))}
        {/* Arc accent */}
        <path
          d={`M ${CX - 105} ${CY - 28 - Math.sqrt(220 * 220 - 105 * 105)} A 220 220 0 0 1 ${CX + 105} ${CY - 28 - Math.sqrt(220 * 220 - 105 * 105)}`}
          fill="none" stroke={ACC} strokeWidth={2.5} strokeLinecap="round" strokeOpacity={0.7}
        />
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.04} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s01letter)" letterSpacing={-6} filter="url(#s01gf)" opacity={0.92}>S</text>
        {/* Accent dot */}
        {(() => {
          const a = -30 * (Math.PI / 180);
          return (
            <circle cx={CX + 220 * Math.cos(a)} cy={CY - 28 + 220 * Math.sin(a)} r={4} fill={ACC} opacity={0.9} />
          );
        })()}
        <circle cx={CX - 110} cy={SIZE - 100} r={2} fill={ACC} opacity={0.4} />
        <circle cx={CX + 110} cy={SIZE - 100} r={2} fill={ACC} opacity={0.4} />
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 02: Obsidian + Gold (luxury lettermark) ──────────────────────────
export const ProfileSample02: React.FC = () => {
  const BG = '#080807';
  const ACC = '#f0c040';
  const WHITE = '#fff8e8';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s02bg" cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor="#1a1505" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s02gold" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fff0a0" />
            <stop offset="50%" stopColor={ACC} />
            <stop offset="100%" stopColor="#b8860b" />
          </linearGradient>
          <filter id="s02gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="18" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s02bg)" />
        {/* Diamond corners */}
        {[[CX, 40], [SIZE - 40, CY], [CX, SIZE - 40], [40, CY]].map(([x, y], i) => (
          <polygon key={i} points={`${x},${(y as number) - 8} ${(x as number) + 8},${y} ${x},${(y as number) + 8} ${(x as number) - 8},${y}`}
            fill="none" stroke={ACC} strokeWidth={0.8} strokeOpacity={0.4} />
        ))}
        {/* Corner lines */}
        {[[40, 40], [SIZE - 40, 40], [SIZE - 40, SIZE - 40], [40, SIZE - 40]].map(([x, y], i) => {
          const dx = x === 40 ? 1 : -1;
          const dy = y === 40 ? 1 : -1;
          return (
            <g key={i}>
              <line x1={x} y1={y} x2={x + dx * 30} y2={y} stroke={ACC} strokeWidth={1} strokeOpacity={0.5} />
              <line x1={x} y1={y} x2={x} y2={y + dy * 30} stroke={ACC} strokeWidth={1} strokeOpacity={0.5} />
            </g>
          );
        })}
        {/* Outer square frame */}
        <rect x={60} y={60} width={SIZE - 120} height={SIZE - 120} fill="none"
          stroke={ACC} strokeWidth={0.4} strokeOpacity={0.15} />
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="Georgia, 'Times New Roman', serif"
          fill={ACC} fillOpacity={0.04} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="Georgia, 'Times New Roman', serif"
          fill="url(#s02gold)" letterSpacing={-6} filter="url(#s02gf)" opacity={0.95}>S</text>
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 03: Deep Purple + Electric Violet (neon cyber) ───────────────────
export const ProfileSample03: React.FC = () => {
  const BG = '#0a0512';
  const ACC = '#b060ff';
  const ACC2 = '#ff40ff';
  const WHITE = '#f8f0ff';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s03bg" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#180828" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s03letter" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={ACC2} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s03gf" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="20" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s03bg)" />
        {/* Hex grid (partial) */}
        {Array.from({ length: 6 }).map((_, row) =>
          Array.from({ length: 5 }).map((_, col) => {
            const hr = 38;
            const hx = col * hr * 1.73 + (row % 2 === 0 ? 0 : hr * 0.865) + 40;
            const hy = row * hr * 1.5 + 30;
            const pts = Array.from({ length: 6 }).map((_, k) => {
              const a = (k * 60 - 30) * (Math.PI / 180);
              return `${hx + hr * Math.cos(a)},${hy + hr * Math.sin(a)}`;
            }).join(' ');
            return (
              <polygon key={`${row}-${col}`} points={pts} fill="none"
                stroke={ACC} strokeWidth={0.4} strokeOpacity={0.12} />
            );
          })
        )}
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.05} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s03letter)" letterSpacing={-6} filter="url(#s03gf)" opacity={0.95}>S</text>
        {/* Accent circle ring */}
        <circle cx={CX} cy={CY - 28} r={210} fill="none"
          stroke={ACC} strokeWidth={1} strokeOpacity={0.25} strokeDasharray="4 8" />
        {/* Top glow dot */}
        <circle cx={CX} cy={CY - 238} r={5} fill={ACC2} opacity={0.9} />
        <circle cx={CX} cy={CY - 238} r={12} fill={ACC2} opacity={0.15} />
        <BrandText accent={ACC2} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 04: Dark Teal + Aqua (geometric triangle) ────────────────────────
export const ProfileSample04: React.FC = () => {
  const BG = '#060e0e';
  const ACC = '#00d4c8';
  const WHITE = '#e8fffe';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s04bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0a1a1a" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s04letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s04gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s04bg)" />
        {/* Large upward triangle */}
        <polygon points={`${CX},${CY - 240} ${CX - 200},${CY + 80} ${CX + 200},${CY + 80}`}
          fill="none" stroke={ACC} strokeWidth={0.8} strokeOpacity={0.2} />
        {/* Inner triangle */}
        <polygon points={`${CX},${CY - 180} ${CX - 150},${CY + 60} ${CX + 150},${CY + 60}`}
          fill="none" stroke={ACC} strokeWidth={0.6} strokeOpacity={0.15} />
        {/* Horizontal lines (tech scan) */}
        {[CY - 60, CY - 20, CY + 20].map((y, i) => (
          <line key={i} x1={CX - 180} y1={y} x2={CX + 180} y2={y}
            stroke={ACC} strokeWidth={0.4} strokeOpacity={0.1} />
        ))}
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.05} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s04letter)" letterSpacing={-6} filter="url(#s04gf)" opacity={0.93}>S</text>
        {/* Triangle vertex dots */}
        {[[CX, CY - 240], [CX - 200, CY + 80], [CX + 200, CY + 80]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={4} fill={ACC} opacity={0.7} />
        ))}
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 05: Carbon + Orange (angular brackets) ───────────────────────────
export const ProfileSample05: React.FC = () => {
  const BG = '#0c0c0c';
  const ACC = '#ff7020';
  const WHITE = '#fff4ee';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <linearGradient id="s05letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s05gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill={BG} />
        {/* Subtle diagonal texture lines */}
        {Array.from({ length: 20 }).map((_, i) => {
          const offset = i * 40 - 200;
          return (
            <line key={i} x1={offset} y1={0} x2={offset + SIZE} y2={SIZE}
              stroke="#ffffff" strokeWidth={0.3} strokeOpacity={0.025} />
          );
        })}
        {/* Angular bracket left */}
        <polyline points={`${CX - 180},${CY - 150} ${CX - 230},${CY - 150} ${CX - 230},${CY + 100} ${CX - 180},${CY + 100}`}
          fill="none" stroke={ACC} strokeWidth={2} strokeOpacity={0.5} strokeLinejoin="miter" />
        {/* Angular bracket right */}
        <polyline points={`${CX + 180},${CY - 150} ${CX + 230},${CY - 150} ${CX + 230},${CY + 100} ${CX + 180},${CY + 100}`}
          fill="none" stroke={ACC} strokeWidth={2} strokeOpacity={0.5} strokeLinejoin="miter" />
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={280} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.04} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={280} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s05letter)" letterSpacing={-6} filter="url(#s05gf)" opacity={0.93}>S</text>
        {/* Bracket corner markers */}
        {[[CX - 230, CY - 150], [CX + 230, CY - 150], [CX - 230, CY + 100], [CX + 230, CY + 100]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={3} fill={ACC} opacity={0.8} />
        ))}
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 06: Midnight Blue + Coral (overlapping circles) ──────────────────
export const ProfileSample06: React.FC = () => {
  const BG = '#090b18';
  const ACC = '#ff6b6b';
  const ACC2 = '#ff9f80';
  const WHITE = '#fff0ee';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s06bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#121028" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s06letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC2} />
          </linearGradient>
          <filter id="s06gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="16" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s06bg)" />
        {/* Overlapping circles */}
        <circle cx={CX - 60} cy={CY - 40} r={180} fill="none"
          stroke={ACC} strokeWidth={0.8} strokeOpacity={0.2} />
        <circle cx={CX + 60} cy={CY - 40} r={180} fill="none"
          stroke={ACC2} strokeWidth={0.8} strokeOpacity={0.2} />
        <circle cx={CX} cy={CY + 60} r={150} fill="none"
          stroke={ACC} strokeWidth={0.6} strokeOpacity={0.12} />
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.04} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s06letter)" letterSpacing={-6} filter="url(#s06gf)" opacity={0.93}>S</text>
        {/* Circle intersection markers */}
        <circle cx={CX} cy={CY - 200} r={4} fill={ACC} opacity={0.8} />
        <circle cx={CX - 215} cy={CY - 40} r={4} fill={ACC2} opacity={0.6} />
        <circle cx={CX + 215} cy={CY - 40} r={4} fill={ACC2} opacity={0.6} />
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 07: Dark Forest + Lime (organic arcs) ────────────────────────────
export const ProfileSample07: React.FC = () => {
  const BG = '#060d08';
  const ACC = '#80ff40';
  const WHITE = '#f0fff0';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s07bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0c1a0e" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s07letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s07gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s07bg)" />
        {/* Concentric arcs (organic curves) */}
        {[120, 160, 200, 240].map((r, i) => (
          <path key={i}
            d={`M ${CX - r} ${CY} Q ${CX} ${CY - r * 1.3} ${CX + r} ${CY}`}
            fill="none" stroke={ACC} strokeWidth={0.6}
            strokeOpacity={0.15 - i * 0.02} />
        ))}
        {/* Bottom arcs */}
        {[100, 140, 180].map((r, i) => (
          <path key={i}
            d={`M ${CX - r} ${CY + 20} Q ${CX} ${CY + r} ${CX + r} ${CY + 20}`}
            fill="none" stroke={ACC} strokeWidth={0.5}
            strokeOpacity={0.1 - i * 0.02} />
        ))}
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.05} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s07letter)" letterSpacing={-6} filter="url(#s07gf)" opacity={0.93}>S</text>
        {/* Arc endpoints */}
        <circle cx={CX} cy={CY - 156} r={4} fill={ACC} opacity={0.8} />
        <circle cx={CX - 240} cy={CY} r={3} fill={ACC} opacity={0.5} />
        <circle cx={CX + 240} cy={CY} r={3} fill={ACC} opacity={0.5} />
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 08: Slate + Royal Blue (dot grid) ────────────────────────────────
export const ProfileSample08: React.FC = () => {
  const BG = '#090b10';
  const ACC = '#4488ff';
  const WHITE = '#eef2ff';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s08mask" cx="50%" cy="50%" r="48%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity={1} />
            <stop offset="100%" stopColor="#ffffff" stopOpacity={0} />
          </radialGradient>
          <mask id="s08dm">
            <rect width={SIZE} height={SIZE} fill="url(#s08mask)" />
          </mask>
          <linearGradient id="s08letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s08gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill={BG} />
        {/* Dot grid */}
        <g mask="url(#s08dm)">
          {Array.from({ length: 20 }).map((_, row) =>
            Array.from({ length: 20 }).map((_, col) => (
              <circle key={`${row}-${col}`}
                cx={col * 34 + 12} cy={row * 34 + 12}
                r={1.2} fill={ACC} opacity={0.25} />
            ))
          )}
        </g>
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.05} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s08letter)" letterSpacing={-6} filter="url(#s08gf)" opacity={0.93}>S</text>
        {/* Outer ring */}
        <circle cx={CX} cy={CY - 28} r={215} fill="none"
          stroke={ACC} strokeWidth={0.7} strokeOpacity={0.25} />
        {/* Cardinal dots */}
        {[[-215, 0], [215, 0], [0, -215], [0, 215]].map(([dx, dy], i) => (
          <circle key={i} cx={CX + dx} cy={CY - 28 + dy} r={3.5} fill={ACC} opacity={0.7} />
        ))}
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 09: Charcoal + Silver (crosshair / precision) ────────────────────
export const ProfileSample09: React.FC = () => {
  const BG = '#0d0d0d';
  const ACC = '#c0c8d8';
  const ACC2 = '#8898aa';
  const WHITE = '#f4f6f8';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <linearGradient id="s09letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="100%" stopColor={ACC} />
          </linearGradient>
          <filter id="s09gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="12" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill={BG} />
        {/* Crosshair lines */}
        <line x1={CX} y1={50} x2={CX} y2={CY - 130}
          stroke={ACC2} strokeWidth={0.5} strokeOpacity={0.4} />
        <line x1={CX} y1={CY + 80} x2={CX} y2={SIZE - 160}
          stroke={ACC2} strokeWidth={0.5} strokeOpacity={0.4} />
        <line x1={50} y1={CY - 28} x2={CX - 130} y2={CY - 28}
          stroke={ACC2} strokeWidth={0.5} strokeOpacity={0.4} />
        <line x1={CX + 130} y1={CY - 28} x2={SIZE - 50} y2={CY - 28}
          stroke={ACC2} strokeWidth={0.5} strokeOpacity={0.4} />
        {/* Concentric rings */}
        {[220, 180, 140, 100].map((r, i) => (
          <circle key={i} cx={CX} cy={CY - 28} r={r} fill="none"
            stroke={ACC2} strokeWidth={0.5}
            strokeOpacity={0.07 + i * 0.03} />
        ))}
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill={ACC} fillOpacity={0.04} letterSpacing={-6}>S</text>
        {/* Main S */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
          fill="url(#s09letter)" letterSpacing={-6} filter="url(#s09gf)" opacity={0.93}>S</text>
        {/* Center crosshair marker */}
        <circle cx={CX} cy={CY - 28} r={8} fill="none" stroke={ACC} strokeWidth={1} strokeOpacity={0.5} />
        <circle cx={CX} cy={CY - 28} r={2} fill={ACC} opacity={0.8} />
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};

// ─── Sample 10: Dark Wine + Rose Gold (flowing curve / elegant) ───────────────
export const ProfileSample10: React.FC = () => {
  const BG = '#100810';
  const ACC = '#ffb0c0';
  const ACC2 = '#e8889a';
  const WHITE = '#fff0f4';
  return (
    <AbsoluteFill style={{ background: BG, overflow: 'hidden' }}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="s10bg" cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor="#1e0e18" />
            <stop offset="100%" stopColor={BG} />
          </radialGradient>
          <linearGradient id="s10letter" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={WHITE} />
            <stop offset="50%" stopColor={ACC} />
            <stop offset="100%" stopColor={ACC2} />
          </linearGradient>
          <filter id="s10gf" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="16" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width={SIZE} height={SIZE} fill="url(#s10bg)" />
        {/* Flowing S-curve accents */}
        <path
          d={`M 80 ${CY - 100} C 200 ${CY - 240} ${CX + 100} ${CY - 180} ${CX} ${CY - 28}`}
          fill="none" stroke={ACC} strokeWidth={1} strokeOpacity={0.25} />
        <path
          d={`M ${SIZE - 80} ${CY + 60} C ${SIZE - 200} ${CY + 200} ${CX - 100} ${CY + 140} ${CX} ${CY - 28}`}
          fill="none" stroke={ACC} strokeWidth={1} strokeOpacity={0.25} />
        {/* Decorative oval */}
        <ellipse cx={CX} cy={CY - 28} rx={210} ry={190} fill="none"
          stroke={ACC2} strokeWidth={0.7} strokeOpacity={0.18} />
        <ellipse cx={CX} cy={CY - 28} rx={170} ry={150} fill="none"
          stroke={ACC2} strokeWidth={0.5} strokeOpacity={0.12} />
        {/* Ghost S */}
        <text x={CX + 2} y={CY + 52} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="Georgia, 'Times New Roman', serif"
          fill={ACC} fillOpacity={0.05} letterSpacing={-6}>S</text>
        {/* Main S — serif for elegant feel */}
        <text x={CX} y={CY + 50} textAnchor="middle" fontSize={300} fontWeight={900}
          fontFamily="Georgia, 'Times New Roman', serif"
          fill="url(#s10letter)" letterSpacing={-6} filter="url(#s10gf)" opacity={0.93}>S</text>
        {/* Top oval accent dot */}
        <ellipse cx={CX} cy={CY - 218} rx={5} ry={5} fill={ACC} opacity={0.8} />
        <ellipse cx={CX} cy={CY - 218} rx={12} ry={12} fill={ACC} opacity={0.12} />
        <BrandText accent={ACC} white={WHITE} />
      </svg>
    </AbsoluteFill>
  );
};
