import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

interface Props {
  symbol: string;
  price: number;
  changePct: number;
  direction: string;
  cardTitle: string;
  cardSubtitle: string;
  script: string;
  audioPath?: string;
}

export const StockShort: React.FC<Props> = ({
  symbol, price, changePct, direction, cardTitle, cardSubtitle
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const color = changePct > 0 ? '#00e676' : changePct < 0 ? '#ff5252' : '#ffd740';
  const sign = changePct > 0 ? '▲' : changePct < 0 ? '▼' : '■';

  const titleOpacity = spring({ frame, fps, from: 0, to: 1, config: { damping: 20 } });
  const priceY = interpolate(frame, [0, 20], [40, 0], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ background: '#0d1117', fontFamily: 'sans-serif', color: '#e6edf3' }}>
      {/* Brand */}
      <div style={{ position: 'absolute', top: 60, left: 60, fontSize: 20, color: '#8b949e', letterSpacing: 6 }}>
        STOCK PILOT
      </div>

      {/* Symbol + Price */}
      <div style={{
        position: 'absolute', top: 160, left: 60,
        transform: `translateY(${priceY}px)`,
      }}>
        <div style={{ fontSize: 80, fontWeight: 900 }}>{symbol}</div>
        <div style={{ fontSize: 56, fontWeight: 700, marginTop: 8 }}>
          ${price.toFixed(2)}
        </div>
        <div style={{
          display: 'inline-block', marginTop: 16,
          fontSize: 36, fontWeight: 700, color,
          padding: '8px 20px',
          border: `2px solid ${color}66`,
          borderRadius: 8,
          background: `${color}11`,
        }}>
          {sign} {Math.abs(changePct).toFixed(2)}%
        </div>
      </div>

      {/* Divider */}
      <div style={{
        position: 'absolute', top: 420, left: 60,
        width: 80, height: 4, background: color,
        opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateRight: 'clamp' }),
      }} />

      {/* Title */}
      <div style={{
        position: 'absolute', top: 460, left: 60, right: 60,
        fontSize: 60, fontWeight: 900, lineHeight: 1.2,
        opacity: titleOpacity,
      }}>
        {cardTitle}
      </div>

      {/* Subtitle */}
      <div style={{
        position: 'absolute', top: 620, left: 60, right: 60,
        fontSize: 32, color: '#8b949e',
        opacity: interpolate(frame, [30, 50], [0, 1], { extrapolateRight: 'clamp' }),
      }}>
        {cardSubtitle}
      </div>

      {/* Disclaimer */}
      <div style={{
        position: 'absolute', bottom: 60, left: 60, right: 60,
        fontSize: 18, color: '#484f58',
      }}>
        본 콘텐츠는 투자 조언이 아닙니다.
      </div>
    </AbsoluteFill>
  );
};
