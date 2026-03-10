import React from 'react';
import { Composition } from 'remotion';
import { StockShort } from './StockShort';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="StockShort"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      component={StockShort as any}
      durationInFrames={900}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        symbol: 'AAPL',
        price: 150.0,
        changePct: 2.5,
        direction: '상승',
        cardTitle: '애플 급등',
        cardSubtitle: '아이폰 판매 호조',
        script: '오늘 애플 주가가 2.5% 상승했습니다.',
        audioPath: '',
        rsi: 55,
        macd: 0.5,
        macdSignal: 0.3,
        volumeRatio: 1.8,
        bbPosition: 'upper',
        emaTrend: 'bullish',
        quantSummary: 'RSI 중립, MACD 골든크로스',
        chartData: [148, 149, 147, 150, 152, 151, 153, 150, 148, 150, 152, 154, 153, 155, 154, 156, 155, 157, 156, 158],
      }}
    />
  );
};
